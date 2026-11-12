"""Сборка бота: aiogram, маршруты и напоминания.

Здесь три вещи: маршруты команд (тонкие — только разбор и ответ), запуск
polling и фоновый цикл напоминаний.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from datetime import UTC, datetime

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from studybot import texts
from studybot.ai import AnthropicSummarizer, DisabledSummarizer, Summarizer
from studybot.config import Settings
from studybot.db import build_engine, build_session_factory, create_tables
from studybot.repository import TaskRepository
from studybot.service import StudyService

logger = logging.getLogger(__name__)

# Разделитель между текстом задачи и сроком в команде `/add`.
DUE_MARKER = " до "


def split_add_args(args: str) -> tuple[str, str | None]:
    """Делит аргументы `/add` на текст задачи и срок.

    Срок идёт после «до»: «прочитать главу до 20.11». Разделитель ищется с
    конца: «прочитать до обеда до 20.11» — это задача «прочитать до обеда» со
    сроком «20.11», а не задача «прочитать» со сроком «обеда до 20.11».
    """
    lowered = args.lower()
    index = lowered.rfind(DUE_MARKER)
    if index == -1:
        return args.strip(), None
    return args[:index].strip(), args[index + len(DUE_MARKER) :].strip() or None


def build_router(service: StudyService) -> Router:
    """Собирает маршруты команд."""
    router = Router(name="study")

    @router.message(Command("start", "help"))
    async def start(message: Message) -> None:
        await message.answer(texts.START)

    @router.message(Command("add"))
    async def add(message: Message, command: CommandObject) -> None:
        title, due_raw = split_add_args(command.args or "")
        now = datetime.now(UTC)
        answer = await service.add_task(message.from_user.id, title, due_raw, now)
        await message.answer(answer)

    @router.message(Command("list"))
    async def list_tasks(message: Message) -> None:
        await message.answer(await service.list_tasks(message.from_user.id))

    @router.message(Command("done"))
    async def done(message: Message, command: CommandObject) -> None:
        answer = await service.complete_task(message.from_user.id, command.args or "")
        await message.answer(answer)

    @router.message(Command("note"))
    async def note(message: Message, command: CommandObject) -> None:
        raw_id, text = split_id_and_text(command.args or "")
        answer = await service.set_note(message.from_user.id, raw_id, text)
        await message.answer(answer)

    @router.message(Command("summarize"))
    async def summarize(message: Message, command: CommandObject) -> None:
        answer = await service.summarize_task(message.from_user.id, command.args or "")
        await message.answer(answer)

    return router


def build_summarizer(settings: Settings) -> Summarizer:
    """Суммаризатор: настоящий, если есть ключ, иначе — честная заглушка."""
    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY не задан — суммаризация выключена.")
        return DisabledSummarizer()
    from anthropic import AsyncAnthropic  # импорт локальный: без ключа SDK не нужен

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return AnthropicSummarizer(client, settings.anthropic_model)


async def run(settings: Settings) -> None:
    """Запускает бота до отмены."""
    engine = build_engine(settings.database_url)
    await create_tables(engine)
    sessions = build_session_factory(engine)
    repository = TaskRepository(sessions)
    service = StudyService(repository, build_summarizer(settings), settings.tz)

    bot = Bot(token=settings.telegram_bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(build_router(service))

    reminders = asyncio.create_task(reminder_loop(bot, service, settings.reminder_interval_seconds))
    logger.info(
        "Бот запущен, напоминания проверяются каждые %s с",
        settings.reminder_interval_seconds,
    )
    try:
        await dispatcher.start_polling(bot)
    finally:
        reminders.cancel()
        with suppress(asyncio.CancelledError):
            await reminders
        await bot.session.close()
        await engine.dispose()


async def reminder_loop(bot: Bot, service: StudyService, interval_seconds: int) -> None:
    """Проверяет базу и напоминает о задачах, которым подошёл срок.

    Один цикл на весь бот, а не таймер на каждую задачу: таймер живёт в памяти
    процесса и после перезапуска пропадает вместе с напоминанием. Здесь срок
    сравнивается с тем, что лежит в базе, — база переживает перезапуск.
    """
    while True:
        try:
            await send_due(bot, service)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Не удалось разослать напоминания")
        await asyncio.sleep(interval_seconds)


async def send_due(bot: Bot, service: StudyService, now: datetime | None = None) -> int:
    """Отправляет напоминания и возвращает их количество."""
    tasks = await service.collect_due(now)
    for task in tasks:
        try:
            await bot.send_message(
                task.user_id,
                texts.DUE_REMINDER.format(
                    title=task.title,
                    due=texts.format_due(task.due_at, service.tz),
                ),
            )
        except Exception:
            logger.exception("Не удалось отправить напоминание о задаче %s", task.id)
    return len(tasks)


def split_id_and_text(args: str) -> tuple[str, str]:
    """Делит «3 прикрепи заметку» на номер и текст."""
    parts = args.strip().split(maxsplit=1)
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]
