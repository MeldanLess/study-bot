"""Модель задачи и тип для дат.

SQLite не хранит часовой пояс: значение, сохранённое с `tzinfo`, возвращается
наивным, и сравнение с осознанным `datetime` падает с `TypeError` — причём
не сразу, а в самый неподходящий момент: в проверке «пора ли напомнить».
Поэтому даты ходят через `UtcDateTime`: на записи всё приводится к UTC, на
чтении возвращается осознанный UTC, и сравнения в коде остаются честными.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


class UtcDateTime(TypeDecorator):
    """Дата и время, которые всегда в UTC."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, _dialect: object) -> datetime | None:
        """На записи: приводим к UTC и отказываемся работать с наивным временем."""
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError(
                "Наивное datetime — это ошибка: время задаётся с часовым поясом и хранится в UTC."
            )
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, _dialect: object) -> datetime | None:
        """На чтении: возвращаем осознанный UTC."""
        if value is None:
            return None
        return value.replace(tzinfo=UTC)


class Base(DeclarativeBase):
    """Базовый класс для моделей."""


class Task(Base):
    """Учебная задача одного пользователя."""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    title: Mapped[str] = mapped_column(String(500))
    note: Mapped[str | None] = mapped_column(String(4000), default=None)
    due_at: Mapped[datetime | None] = mapped_column(UtcDateTime, default=None, index=True)
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    reminded_at: Mapped[datetime | None] = mapped_column(UtcDateTime, default=None)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=lambda: datetime.now(UTC))
