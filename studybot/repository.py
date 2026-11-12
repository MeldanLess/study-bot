"""Хранилище задач — единственное место, где живёт SQL.

Всё, что выше, работает с объектами `Task` и не знает про запросы. Так
логику можно проверять, не подменяя базу, а базу — подменять одним
драйвером, если завтра понадобится PostgreSQL.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from studybot.models import Task


class TaskRepository:
    """Хранилище задач одного пользователя."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def add(self, task: Task) -> Task:
        """Сохраняет задачу и возвращает её с присвоенным id."""
        async with self._sessions() as session:
            session.add(task)
            await session.commit()
            await session.refresh(task)
            return task

    async def get(self, task_id: int, user_id: int) -> Task | None:
        """Возвращает задачу пользователя или `None`.

        Чужую задачу не найти: `user_id` — часть условия. Это не «скрытие»,
        а отсутствие доступа: чужих данных у бота просто нет.
        """
        async with self._sessions() as session:
            result = await session.execute(
                select(Task).where(Task.id == task_id, Task.user_id == user_id)
            )
            return result.scalar_one_or_none()

    async def list_active(self, user_id: int) -> list[Task]:
        """Незавершённые задачи пользователя, ближайшие дедлайны сверху."""
        async with self._sessions() as session:
            result = await session.execute(
                select(Task)
                .where(Task.user_id == user_id, Task.done.is_(False))
                .order_by(Task.due_at.is_(None), Task.due_at, Task.id)
            )
            return list(result.scalars().all())

    async def set_note(self, task_id: int, user_id: int, note: str) -> bool:
        """Прикрепляет заметку к задаче."""
        async with self._sessions() as session:
            result = await session.execute(
                update(Task).where(Task.id == task_id, Task.user_id == user_id).values(note=note)
            )
            await session.commit()
            return bool(result.rowcount)

    async def complete(self, task_id: int, user_id: int) -> bool:
        """Отмечает задачу выполненной."""
        async with self._sessions() as session:
            result = await session.execute(
                update(Task).where(Task.id == task_id, Task.user_id == user_id).values(done=True)
            )
            await session.commit()
            return bool(result.rowcount)

    async def due(self, now: datetime) -> list[Task]:
        """Задачи, которым пора напомнить.

        Условие — срок наступил, задача не выполнена и напоминание ещё не
        отправлялось. Последнее условие важно: иначе бот присылал бы одно и то
        же каждую минуту.
        """
        async with self._sessions() as session:
            result = await session.execute(
                select(Task).where(
                    Task.due_at.is_not(None),
                    Task.due_at <= now,
                    Task.done.is_(False),
                    Task.reminded_at.is_(None),
                )
            )
            return list(result.scalars().all())

    async def mark_reminded(self, task_ids: list[int], when: datetime) -> None:
        """Запоминает, что напоминание отправлено."""
        if not task_ids:
            return
        async with self._sessions() as session:
            await session.execute(
                update(Task).where(Task.id.in_(task_ids)).values(reminded_at=when)
            )
            await session.commit()
