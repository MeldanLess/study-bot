"""Точка входа: `python -m studybot`.

После `pip install -e .` бот запускается и как команда `study-bot`.
"""

from __future__ import annotations

import asyncio
import logging

from pydantic import ValidationError

from studybot.bot import run
from studybot.config import Settings


def main() -> None:
    """Читает настройки и запускает бота."""
    try:
        settings = Settings()
    except ValidationError as error:
        raise SystemExit(
            "Не задан TELEGRAM_BOT_TOKEN.\n"
            "Скопируйте .env.example в .env и впишите токен от @BotFather.\n"
            f"Подробности: {error}"
        ) from error

    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    asyncio.run(run(settings))


if __name__ == "__main__":
    main()
