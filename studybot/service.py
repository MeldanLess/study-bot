"""Правила бота — без Telegram и без aiogram.

Ручки Telegram тонкие: они разбирают команду и зовут сюда. Всё, что с
задачами, живёт здесь, и поэтому проверяется обычными тестами — без сети,
без Telegram и без фейкового клиента.

Сервис возвращает готовый текст ответа и не знает, как он будет отправлен.
"""

from __future__ import annotations

from datetime import UTC, datetime, tzinfo

from studybot import texts
from studybot.ai import Summarizer, SummarizerUnavailable
from studybot.dates import DateParseError, parse_due
from studybot.models import Task
from studybot.repository import TaskRepository


class StudyService:
    """Что бот умеет делать с учебными задачами."""

    def __init__(self, repository: TaskRepository, summarizer: Summarizer, tz: tzinfo) -> None:
        self._repository = repository
        self._summarizer = summarizer
        self._tz = tz

    @property
    def tz(self) -> tzinfo:
        """Часовой пояс, в котором бот показывает время."""
        return self._tz

    async def add_task(self, user_id: int, title: str, due_raw: str | None, now: datetime) -> str:
        """Добавляет задачу. Срок разбирается из человеческого текста."""
        cleaned = title.strip()
        if not cleaned:
            return texts.EMPTY_TITLE

        due_at = None
        if due_raw and due_raw.strip():
            try:
                due_at = parse_due(due_raw, now=now, tz=self._tz)
            except DateParseError:
                return texts.BAD_DATE.format(raw=due_raw.strip())

        task = Task(user_id=user_id, title=cleaned, due_at=due_at)
        saved = await self._repository.add(task)
        return f"Записал: №{saved.id} {saved.title} — {texts.format_due(saved.due_at, self._tz)}"

    async def list_tasks(self, user_id: int) -> str:
        """Список незавершённых задач."""
        tasks = await self._repository.list_active(user_id)
        return texts.format_tasks(tasks, self._tz)

    async def complete_task(self, user_id: int, raw_id: str) -> str:
        """Отмечает задачу выполненной."""
        task_id = _parse_id(raw_id)
        if task_id is None:
            return texts.NOT_A_NUMBER.format(example=texts.EXAMPLE_DONE)
        if not await self._repository.complete(task_id, user_id):
            return texts.UNKNOWN_TASK.format(task_id=task_id)
        return texts.DONE.format(task_id=task_id)

    async def set_note(self, user_id: int, raw_id: str, note: str) -> str:
        """Прикрепляет заметку к задаче."""
        task_id = _parse_id(raw_id)
        if task_id is None:
            return texts.NOT_A_NUMBER.format(example=texts.EXAMPLE_NOTE)
        if not await self._repository.set_note(task_id, user_id, note.strip()):
            return texts.UNKNOWN_TASK.format(task_id=task_id)
        return texts.NOTE_SAVED.format(task_id=task_id)

    async def summarize_task(self, user_id: int, raw_id: str) -> str:
        """Сжимает заметку задачи до короткого пересказа."""
        task_id = _parse_id(raw_id)
        if task_id is None:
            return texts.NOT_A_NUMBER.format(example=texts.EXAMPLE_SUMMARIZE)
        task = await self._repository.get(task_id, user_id)
        if task is None:
            return texts.UNKNOWN_TASK.format(task_id=task_id)
        if not task.note:
            return texts.NO_NOTE.format(task_id=task_id)
        try:
            summary = await self._summarizer.summarize(task.note)
        except SummarizerUnavailable:
            return texts.SUMMARIZER_OFF
        except Exception as error:  # noqa: BLE001 — причина важнее текста исключения
            return texts.SUMMARY_FAILED.format(reason=type(error).__name__)
        return texts.SUMMARY.format(task_id=task_id, summary=summary)

    async def collect_due(self, now: datetime | None = None) -> list[Task]:
        """Задачи, которым пора напомнить, и пометка «напомнили»."""
        moment = now or datetime.now(UTC)
        tasks = await self._repository.due(moment)
        await self._repository.mark_reminded([task.id for task in tasks], moment)
        return tasks


def _parse_id(raw: str) -> int | None:
    """Номер задачи из строки. Не число — `None`, а не исключение."""
    cleaned = raw.strip()
    if not cleaned.isdigit():
        return None
    return int(cleaned)
