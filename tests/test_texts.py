"""Тесты текстов и разбора аргументов команд."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from studybot import texts
from studybot.bot import split_add_args, split_id_and_text
from studybot.models import Task

TZ = ZoneInfo("Europe/Moscow")


class TestFormatDue:
    """Как бот показывает время."""

    def test_без_срока(self) -> None:
        assert texts.format_due(None, TZ) == "без срока"

    def test_время_переводится_в_часовой_пояс(self) -> None:
        moment = datetime(2026, 11, 12, 7, 0, tzinfo=UTC)
        assert texts.format_due(moment, TZ) == "12 ноября, 10:00"


class TestFormatTask:
    """Одна задача одной строкой."""

    def test_задача_в_строке(self) -> None:
        task = Task(id=7, user_id=1, title="Прочитать главу", due_at=None)
        line = texts.format_task(task, TZ)
        assert "№7" in line
        assert "Прочитать главу" in line
        assert "без срока" in line

    def test_заметка_отмечается(self) -> None:
        task = Task(id=7, user_id=1, title="Задача", note="текст")
        assert "есть заметка" in texts.format_task(task, TZ)

    def test_пустой_список(self) -> None:
        assert texts.format_tasks([], TZ) == texts.NO_TASKS


class TestSplitAddArgs:
    """Команда `/add Задача до срок`."""

    def test_без_срока(self) -> None:
        assert split_add_args("Прочитать главу") == ("Прочитать главу", None)

    def test_со_сроком(self) -> None:
        assert split_add_args("Прочитать главу до 20.11") == (
            "Прочитать главу",
            "20.11",
        )

    def test_разделитель_ищется_с_конца(self) -> None:
        assert split_add_args("прочитать до обеда до 20.11") == (
            "прочитать до обеда",
            "20.11",
        )

    def test_пустой_срок_считается_отсутствующим(self) -> None:
        assert split_add_args("Прочитать главу до ") == ("Прочитать главу", None)

    def test_пустая_команда(self) -> None:
        assert split_add_args("") == ("", None)


class TestSplitIdAndText:
    """Команда `/note 3 текст заметки`."""

    def test_номер_и_текст(self) -> None:
        assert split_id_and_text("3 прочитать первые две главы") == (
            "3",
            "прочитать первые две главы",
        )

    def test_только_номер(self) -> None:
        assert split_id_and_text("3") == ("3", "")

    def test_пусто(self) -> None:
        assert split_id_and_text("") == ("", "")
