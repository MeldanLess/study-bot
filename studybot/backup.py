"""Резервная копия базы бота.

Копия снимается через backup API SQLite, а не копированием файла: база может
писаться в этот момент, и обычная копия получится недописанной. Backup API
работает с открытой базой и делает снимок согласованным.

Запуск:

    study-bot-backup --source data/studybot.db --target data/backups
"""

from __future__ import annotations

import argparse
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_KEEP = 14
PREFIX = "studybot-"
SUFFIX = ".db"


def backup(source: Path, target_dir: Path, now: datetime | None = None) -> Path:
    """Снимает копию базы и возвращает путь к ней."""
    if not source.exists():
        raise FileNotFoundError(f"Нет базы: {source}")
    target_dir.mkdir(parents=True, exist_ok=True)
    moment = now or datetime.now(UTC)
    target = target_dir / f"{PREFIX}{moment:%Y-%m-%d}{SUFFIX}"
    with sqlite3.connect(source) as origin, sqlite3.connect(target) as copy:
        origin.backup(copy)
    return target


def prune(target_dir: Path, keep: int = DEFAULT_KEEP) -> list[Path]:
    """Удаляет старые копии, оставляя последние `keep`."""
    copies = sorted(target_dir.glob(f"{PREFIX}*{SUFFIX}"))
    old = copies if keep <= 0 else copies[:-keep]
    for path in old:
        path.unlink()
    return old


def main(argv: list[str] | None = None) -> int:
    """Точка входа: `study-bot-backup …`."""
    parser = argparse.ArgumentParser(description="Снять резервную копию базы бота.")
    parser.add_argument("--source", default="data/studybot.db", help="Файл базы.")
    parser.add_argument("--target", default="data/backups", help="Каталог для копий.")
    parser.add_argument("--keep", type=int, default=DEFAULT_KEEP, help="Сколько копий хранить.")
    args = parser.parse_args(argv)

    try:
        target = backup(Path(args.source), Path(args.target))
    except (FileNotFoundError, sqlite3.Error) as error:
        print(f"Копия не снята: {error}")
        return 1

    removed = prune(Path(args.target), args.keep)
    print(f"Копия снята: {target}")
    if removed:
        print(f"Удалено старых копий: {len(removed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
