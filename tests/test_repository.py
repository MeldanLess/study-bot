"""Тесты хранилища.

Проверяется не «работает ли SQL», а границы: чужая задача не видна, готовая
не попадает в список, а напоминание не повторяется.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from studybot.models import Task
from studybot.repository import TaskRepository

NOW = datetime(2026, 11, 12, 7, 0, tzinfo=UTC)


async def _add(repository: TaskRepository, **kwargs: object) -> Task:
    task = Task(user_id=kwargs.pop("user_id", 1), title=kwargs.pop("title", "Задача"), **kwargs)
    return await repository.add(task)


class TestAdd:
    """Добавление задачи."""

    async def test_задаче_даётся_номер(self, repository: TaskRepository) -> None:
        task = await _add(repository)
        assert task.id is not None
        assert task.title == "Задача"

    async def test_время_возвращается_осознанным_в_utc(self, repository: TaskRepository) -> None:
        task = await _add(repository, due_at=NOW)
        assert task.due_at is not None
        assert task.due_at.tzinfo is not None
        assert task.due_at.utcoffset() == timedelta(0)
        assert task.due_at == NOW

    async def test_наивное_время_не_принимается(self, repository: TaskRepository) -> None:
        naive = datetime(2026, 11, 12, 7, 0)
        with pytest.raises(Exception, match="Наивное"):
            await _add(repository, due_at=naive)


class TestAccess:
    """Чужие данные недоступны."""

    async def test_чужая_задача_не_находится(self, repository: TaskRepository) -> None:
        task = await _add(repository, user_id=1)
        assert await repository.get(task.id, user_id=2) is None

    async def test_своя_задача_находится(self, repository: TaskRepository) -> None:
        task = await _add(repository, user_id=1)
        found = await repository.get(task.id, user_id=1)
        assert found is not None
        assert found.title == task.title


class TestList:
    """Список незавершённых задач."""

    async def test_пустой_список(self, repository: TaskRepository) -> None:
        assert await repository.list_active(user_id=1) == []

    async def test_выполненные_не_показываются(self, repository: TaskRepository) -> None:
        task = await _add(repository)
        await repository.complete(task.id, user_id=1)
        assert await repository.list_active(user_id=1) == []

    async def test_чужие_не_показываются(self, repository: TaskRepository) -> None:
        await _add(repository, user_id=2)
        assert await repository.list_active(user_id=1) == []

    async def test_порядок_по_сроку(self, repository: TaskRepository) -> None:
        later = await _add(
            repository, title="Позже", due_at=datetime(2026, 11, 20, 7, 0, tzinfo=UTC)
        )
        soon = await _add(
            repository, title="Скоро", due_at=datetime(2026, 11, 13, 7, 0, tzinfo=UTC)
        )
        without = await _add(repository, title="Без срока")
        assert [task.id for task in await repository.list_active(user_id=1)] == [
            soon.id,
            later.id,
            without.id,
        ]


class TestChanges:
    """Заметка и отметка выполнения."""

    async def test_заметка_сохраняется(self, repository: TaskRepository) -> None:
        task = await _add(repository)
        assert await repository.set_note(task.id, user_id=1, note="текст") is True
        found = await repository.get(task.id, user_id=1)
        assert found is not None
        assert found.note == "текст"

    async def test_чужую_заметку_не_меняем(self, repository: TaskRepository) -> None:
        task = await _add(repository, user_id=1)
        assert await repository.set_note(task.id, user_id=2, note="текст") is False

    async def test_отметка_выполнения(self, repository: TaskRepository) -> None:
        task = await _add(repository)
        assert await repository.complete(task.id, user_id=1) is True
        found = await repository.get(task.id, user_id=1)
        assert found is not None
        assert found.done is True

    async def test_чужую_задачу_не_закрыть(self, repository: TaskRepository) -> None:
        task = await _add(repository, user_id=1)
        assert await repository.complete(task.id, user_id=2) is False


class TestDue:
    """Кому пора напомнить."""

    async def test_пусто(self, repository: TaskRepository) -> None:
        assert await repository.due(NOW) == []

    async def test_срок_наступил(self, repository: TaskRepository) -> None:
        task = await _add(repository, due_at=datetime(2026, 11, 12, 6, 0, tzinfo=UTC))
        due = await repository.due(NOW)
        assert [item.id for item in due] == [task.id]

    async def test_срок_ещё_не_наступил(self, repository: TaskRepository) -> None:
        await _add(repository, due_at=datetime(2026, 11, 13, 6, 0, tzinfo=UTC))
        assert await repository.due(NOW) == []

    async def test_выполненная_не_напоминается(self, repository: TaskRepository) -> None:
        task = await _add(repository, due_at=datetime(2026, 11, 12, 6, 0, tzinfo=UTC))
        await repository.complete(task.id, user_id=1)
        assert await repository.due(NOW) == []

    async def test_повторно_не_напоминает(self, repository: TaskRepository) -> None:
        task = await _add(repository, due_at=datetime(2026, 11, 12, 6, 0, tzinfo=UTC))
        await repository.mark_reminded([task.id], NOW)
        assert await repository.due(NOW) == []
