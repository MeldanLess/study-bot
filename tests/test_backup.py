"""Тесты резервного копирования.

Копия должна быть рабочей базой, а не файлом с тем же именем: проверяем
именно это — открываем копию и читаем из неё задачу.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from studybot.backup import backup, main as backup_main, prune


def _make_db(path: Path) -> None:
    """Создаёт базу с одной таблицей."""
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT)")
        connection.execute("INSERT INTO tasks (title) VALUES ('Прочитать главу')")


class TestBackup:
    """Копия снимается."""

    def test_копия_создаётся(self, tmp_path: Path) -> None:
        source = tmp_path / "studybot.db"
        _make_db(source)
        target = backup(source, tmp_path / "backups", datetime(2026, 11, 12, tzinfo=UTC))
        assert target.exists()
        assert target.name == "studybot-2026-11-12.db"

    def test_копия_читается(self, tmp_path: Path) -> None:
        source = tmp_path / "studybot.db"
        _make_db(source)
        target = backup(source, tmp_path / "backups", datetime(2026, 11, 12, tzinfo=UTC))
        with sqlite3.connect(target) as connection:
            rows = connection.execute("SELECT title FROM tasks").fetchall()
        assert rows == [("Прочитать главу",)]

    def test_нет_базы_и_ничего_не_ломается(self, tmp_path: Path) -> None:
        try:
            backup(tmp_path / "нет-такой.db", tmp_path / "backups")
        except FileNotFoundError as error:
            assert "Нет базы" in str(error)
        else:
            raise AssertionError("Ожидалась ошибка FileNotFoundError")


class TestPrune:
    """Старые копии удаляются."""

    def test_остаётся_последние_копии(self, tmp_path: Path) -> None:
        for day in range(1, 6):
            (tmp_path / f"studybot-2026-11-0{day}.db").write_bytes(b"")
        removed = prune(tmp_path, keep=2)
        assert len(removed) == 3
        assert sorted(path.name for path in tmp_path.glob("*.db")) == [
            "studybot-2026-11-04.db",
            "studybot-2026-11-05.db",
        ]

    def test_при_нуле_удаляются_все(self, tmp_path: Path) -> None:
        (tmp_path / "studybot-2026-11-01.db").write_bytes(b"")
        assert len(prune(tmp_path, keep=0)) == 1
        assert list(tmp_path.glob("*.db")) == []


class TestMain:
    """Команда копирования."""

    def test_копия_снимается(self, tmp_path: Path, capsys) -> None:
        source = tmp_path / "studybot.db"
        _make_db(source)
        code = backup_main(
            ["--source", str(source), "--target", str(tmp_path / "backups"), "--keep", "3"]
        )
        assert code == 0
        assert list((tmp_path / "backups").glob("studybot-*.db"))
        assert "Копия снята" in capsys.readouterr().out

    def test_нет_базы_и_понятное_сообщение(self, tmp_path: Path, capsys) -> None:
        code = backup_main(
            ["--source", str(tmp_path / "нет-такой.db"), "--target", str(tmp_path / "backups")]
        )
        assert code == 1
        assert "Копия не снята" in capsys.readouterr().out
