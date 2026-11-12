"""Тесты правил бота.

Сервис не знает про Telegram: он получает команду и возвращает текст
ответа. Поэтому здесь нет ни сети, ни фейкового клиента — только правила.
"""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from studybot import texts
from studybot.ai import DisabledSummarizer
from studybot.service import StudyService

NOW = datetime(2026, 11, 12, 7, 0, tzinfo=UTC)
TZ = ZoneInfo("Europe/Moscow")


class TestAddTask:
    """Добавление задачи."""

    async def test_задача_сохраняется_и_отвечает(self, service: StudyService) -> None:
        answer = await service.add_task(1, "Прочитать главу", "завтра", NOW)
        assert "Прочитать главу" in answer
        assert "13 ноября, 09:00" in answer

    async def test_без_срока(self, service: StudyService) -> None:
        answer = await service.add_task(1, "Прочитать главу", None, NOW)
        assert "без срока" in answer

    async def test_пустая_задача(self, service: StudyService) -> None:
        answer = await service.add_task(1, "   ", "завтра", NOW)
        assert answer == texts.EMPTY_TITLE

    async def test_непонятный_срок(self, service: StudyService) -> None:
        answer = await service.add_task(1, "Прочитать главу", "когда-нибудь", NOW)
        assert answer == texts.BAD_DATE.format(raw="когда-нибудь")

    async def test_срок_доходит_до_базы(self, service: StudyService) -> None:
        await service.add_task(1, "Прочитать главу", "завтра", NOW)
        tasks = await service.list_tasks(1)
        assert "13 ноября, 09:00" in tasks


class TestListTasks:
    """Список задач."""

    async def test_пусто(self, service: StudyService) -> None:
        assert await service.list_tasks(1) == texts.NO_TASKS

    async def test_задача_в_списке(self, service: StudyService) -> None:
        await service.add_task(1, "Прочитать главу", "завтра", NOW)
        answer = await service.list_tasks(1)
        assert "Прочитать главу" in answer
        assert "№1" in answer

    async def test_чужие_задачи_не_показываются(self, service: StudyService) -> None:
        await service.add_task(2, "Чужая задача", "завтра", NOW)
        assert await service.list_tasks(1) == texts.NO_TASKS


class TestCompleteTask:
    """Отметка выполнения."""

    async def test_задача_закрывается(self, service: StudyService) -> None:
        await service.add_task(1, "Прочитать главу", None, NOW)
        answer = await service.complete_task(1, "1")
        assert answer == texts.DONE.format(task_id=1)
        assert await service.list_tasks(1) == texts.NO_TASKS

    async def test_не_число(self, service: StudyService) -> None:
        assert await service.complete_task(1, "abc") == texts.NOT_A_NUMBER.format(
            example=texts.EXAMPLE_DONE
        )

    async def test_неизвестная_задача(self, service: StudyService) -> None:
        assert await service.complete_task(1, "42") == texts.UNKNOWN_TASK.format(task_id=42)


class TestNote:
    """Заметки."""

    async def test_заметка_сохраняется(self, service: StudyService) -> None:
        await service.add_task(1, "Прочитать главу", None, NOW)
        answer = await service.set_note(1, "1", "прочитать первые две главы")
        assert answer == texts.NOTE_SAVED.format(task_id=1)

    async def test_не_число(self, service: StudyService) -> None:
        assert await service.set_note(1, "abc", "текст") == texts.NOT_A_NUMBER.format(
            example=texts.EXAMPLE_NOTE
        )

    async def test_неизвестная_задача(self, service: StudyService) -> None:
        assert await service.set_note(1, "42", "текст") == texts.UNKNOWN_TASK.format(task_id=42)


class TestSummarize:
    """Суммаризация заметки."""

    async def test_заметка_сжимается(self, service: StudyService, summarizer) -> None:
        await service.add_task(1, "Прочитать главу", None, NOW)
        await service.set_note(1, "1", "длинный текст")
        answer = await service.summarize_task(1, "1")
        assert summarizer.summary in answer
        assert summarizer.calls == ["длинный текст"]

    async def test_без_заметки(self, service: StudyService) -> None:
        await service.add_task(1, "Прочитать главу", None, NOW)
        assert await service.summarize_task(1, "1") == texts.NO_NOTE.format(task_id=1)

    async def test_неизвестная_задача(self, service: StudyService) -> None:
        assert await service.summarize_task(1, "42") == texts.UNKNOWN_TASK.format(task_id=42)

    async def test_не_число(self, service: StudyService) -> None:
        assert await service.summarize_task(1, "abc") == texts.NOT_A_NUMBER.format(
            example=texts.EXAMPLE_SUMMARIZE
        )

    async def test_выключенная_суммаризация(self, repository) -> None:
        service = StudyService(repository, DisabledSummarizer(), TZ)
        await service.add_task(1, "Прочитать главу", None, NOW)
        await service.set_note(1, "1", "текст")
        assert await service.summarize_task(1, "1") == texts.SUMMARIZER_OFF

    async def test_ошибка_апи_не_ломает_бота(self, repository) -> None:
        class СломанныйСуммаризатор:
            async def summarize(self, _note: str) -> str:
                raise RuntimeError("503")

        service = StudyService(repository, СломанныйСуммаризатор(), TZ)
        await service.add_task(1, "Прочитать главу", None, NOW)
        await service.set_note(1, "1", "текст")
        answer = await service.summarize_task(1, "1")
        assert "RuntimeError" in answer


class TestCollectDue:
    """Напоминания."""

    async def test_пора_напомнить(self, service: StudyService) -> None:
        # Дата с годом и в прошлом: без года срок всегда в будущем — так
        # устроено правило «ближайший будущий год».
        await service.add_task(1, "Прочитать главу", "2026-11-10 09:00", NOW)
        due = await service.collect_due(NOW)
        assert len(due) == 1
        assert due[0].title == "Прочитать главу"

    async def test_повторно_не_напоминает(self, service: StudyService) -> None:
        await service.add_task(1, "Прочитать главу", "2026-11-10 09:00", NOW)
        await service.collect_due(NOW)
        assert await service.collect_due(NOW) == []
