"""Тесты маршрутов Telegram.

Сеть не используется: подменяется бот, который только запоминает отправленные
сообщения. Так проверяется весь путь команды — разбор текста, фильтр,
обработчик и ответ.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

import pytest
from aiogram import Dispatcher
from aiogram.methods import SendMessage
from aiogram.types import Chat, Message, Update, User

from studybot.ai import AnthropicSummarizer, DisabledSummarizer
from studybot.bot import build_router, build_summarizer, reminder_loop, send_due
from studybot.config import Settings
from studybot.service import StudyService

USER_ID = 42
NOW = datetime(2026, 11, 12, 7, 0, tzinfo=UTC)


class FakeBot:
    """Бот, который только запоминает отправленные сообщения."""

    id = 1

    def __init__(self) -> None:
        self.sent: list[str] = []

    async def __call__(self, method: SendMessage, **_kwargs: Any) -> SendMessage:
        self.sent.append(method.text)
        return method

    async def send_message(self, chat_id: int, text: str, **_kwargs: Any) -> SendMessage:
        """Так бот отправляет напоминания — напрямую методом."""
        self.sent.append(text)
        return SendMessage(chat_id=chat_id, text=text)


def make_update(text: str, user_id: int = USER_ID) -> Update:
    """Собирает обновление с текстовым сообщением."""
    user = User(id=user_id, is_bot=False, first_name="Тест")
    chat = Chat(id=user_id, type="private")
    message = Message(
        message_id=1,
        date=datetime(2026, 11, 12, 7, 0, tzinfo=UTC),
        chat=chat,
        from_user=user,
        text=text,
    )
    return Update(update_id=1, message=message)


async def send(service: StudyService, text: str) -> list[str]:
    """Отправляет команду боту и возвращает ответы."""
    bot = FakeBot()
    dispatcher = Dispatcher()
    dispatcher.include_router(build_router(service))
    await dispatcher.feed_update(bot, make_update(text))
    return bot.sent


class TestCommands:
    """Команды бота."""

    async def test_справка(self, service: StudyService) -> None:
        answers = await send(service, "/start")
        assert answers
        assert "/add" in answers[0]

    async def test_добавление_задачи(self, service: StudyService) -> None:
        answers = await send(service, "/add Прочитать главу до завтра")
        assert "Прочитать главу" in answers[0]
        assert "13 ноября, 09:00" in answers[0]

    async def test_добавление_без_срока(self, service: StudyService) -> None:
        answers = await send(service, "/add Прочитать главу")
        assert "без срока" in answers[0]

    async def test_непонятный_срок(self, service: StudyService) -> None:
        answers = await send(service, "/add Прочитать главу до когда-нибудь")
        assert "Не понял срок" in answers[0]

    async def test_список(self, service: StudyService) -> None:
        await send(service, "/add Прочитать главу до завтра")
        answers = await send(service, "/list")
        assert "Прочитать главу" in answers[0]

    async def test_пустой_список(self, service: StudyService) -> None:
        answers = await send(service, "/list")
        assert "ничего нет" in answers[0]

    async def test_отметка_выполнения(self, service: StudyService) -> None:
        await send(service, "/add Прочитать главу до завтра")
        answers = await send(service, "/done 1")
        assert "выполненной" in answers[0]

    async def test_заметка(self, service: StudyService) -> None:
        await send(service, "/add Прочитать главу до завтра")
        answers = await send(service, "/note 1 прочитать первые две главы")
        assert "Заметку" in answers[0]

    async def test_суммаризация(self, service: StudyService, summarizer) -> None:
        await send(service, "/add Прочитать главу до завтра")
        await send(service, "/note 1 длинный текст")
        answers = await send(service, "/summarize 1")
        assert summarizer.summary in answers[0]


class TestReminders:
    """Напоминания о задачах, которым подошёл срок."""

    async def test_напоминание_уходит(self, service: StudyService) -> None:
        await service.add_task(USER_ID, "Прочитать главу", "2026-11-10 09:00", NOW)
        bot = FakeBot()
        count = await send_due(bot, service, NOW)
        assert count == 1
        assert "Прочитать главу" in bot.sent[0]
        assert "Дедлайн был" in bot.sent[0]

    async def test_повторно_не_напоминает(self, service: StudyService) -> None:
        await service.add_task(USER_ID, "Прочитать главу", "2026-11-10 09:00", NOW)
        bot = FakeBot()
        await send_due(bot, service, NOW)
        assert await send_due(bot, service, NOW) == 0
        assert len(bot.sent) == 1

    async def test_цикл_останавливается(self, service: StudyService) -> None:
        task = asyncio.create_task(reminder_loop(FakeBot(), service, 1))
        await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


class TestSummarizerFactory:
    """Суммаризатор собирается по настройкам."""

    def test_без_ключа_заглушка(self) -> None:
        settings = Settings(telegram_bot_token="123:ABC")
        assert isinstance(build_summarizer(settings), DisabledSummarizer)

    def test_с_ключом_настоящий(self) -> None:
        settings = Settings(telegram_bot_token="123:ABC", anthropic_api_key="sk-ant-test")
        assert isinstance(build_summarizer(settings), AnthropicSummarizer)
