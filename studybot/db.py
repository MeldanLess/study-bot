"""Движок, сессии и создание таблиц.

Движок создаётся один раз на процесс: внутри движка держится пул соединений,
а для SQLite это один файл, который нельзя открыть на запись дважды.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from studybot.models import Base


def build_engine(database_url: str) -> AsyncEngine:
    """Создаёт асинхронный движок.

    Для SQLite каталог с базой создаётся заранее: иначе первое же сохранение
    падает с «unable to open database file», и ошибка выглядит как проблема
    прав доступа, а не как отсутствующая папка.
    """
    if database_url.startswith("sqlite"):
        path = database_url.split("///", 1)[-1]
        if path and path != ":memory:":
            Path(path).expanduser().parent.mkdir(parents=True, exist_ok=True)
    return create_async_engine(database_url, future=True)


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Фабрика сессий для хранилища."""
    return async_sessionmaker(engine, expire_on_commit=False)


async def create_tables(engine: AsyncEngine) -> None:
    """Создаёт таблицы, если их ещё нет."""
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
