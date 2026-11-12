"""Общие приспособления для тестов.

Тесты не ходят в сеть: ни Telegram, ни Anthropic API. Суммаризатор подменяется
заглушкой, а база — временным файлом SQLite.
"""

from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from studybot.db import build_engine, build_session_factory, create_tables  # noqa: E402
from studybot.repository import TaskRepository  # noqa: E402
from studybot.service import StudyService  # noqa: E402

TZ = ZoneInfo("Europe/Moscow")


@pytest.fixture()
def now() -> datetime:
    """Фиксированный момент: 12 ноября 2026, 10:00 по Москве."""
    return datetime(2026, 11, 12, 10, 0, tzinfo=TZ).astimezone(UTC)


@pytest.fixture()
async def repository(tmp_path: Path) -> AsyncIterator[TaskRepository]:
    """Хранилище на временной базе."""
    engine = build_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    await create_tables(engine)
    sessions = build_session_factory(engine)
    yield TaskRepository(sessions)
    await engine.dispose()


class FakeSummarizer:
    """Суммаризатор, который не ходит в сеть и запоминает вызовы."""

    def __init__(self, summary: str = "Коротко: сделать и закрыть.") -> None:
        self.summary = summary
        self.calls: list[str] = []

    async def summarize(self, note: str) -> str:
        self.calls.append(note)
        return self.summary


@pytest.fixture()
def summarizer() -> FakeSummarizer:
    """Заглушка суммаризатора."""
    return FakeSummarizer()


@pytest.fixture()
async def service(repository: TaskRepository, summarizer: FakeSummarizer) -> StudyService:
    """Сервис бота на временной базе."""
    return StudyService(repository, summarizer, TZ)
