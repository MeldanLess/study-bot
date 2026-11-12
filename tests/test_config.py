"""Тесты настроек.

Настройки — это то, что чаще всего ломается не в коде, а в окружении:
нет токена, неизвестный часовой пояс, ключ API прописан с пробелом.
"""

from __future__ import annotations

from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from studybot.config import Settings


class TestSettings:
    """Загрузка настроек."""

    def test_токен_обязателен(self) -> None:
        # `_env_file=None` — файл `.env` не читается: тест не должен зависеть
        # от того, есть ли у разработчика свой токен на диске.
        with pytest.raises(ValidationError):
            Settings(_env_file=None)

    def test_минимальный_набор(self) -> None:
        settings = Settings(telegram_bot_token="123:ABC")
        assert settings.telegram_bot_token == "123:ABC"
        assert settings.database_url.startswith("sqlite+aiosqlite")
        assert settings.reminder_interval_seconds == 60

    def test_часовой_пояс_из_настроек(self) -> None:
        settings = Settings(telegram_bot_token="123:ABC", timezone="Europe/Moscow")
        assert settings.tz == ZoneInfo("Europe/Moscow")

    def test_неизвестный_часовой_пояс(self) -> None:
        settings = Settings(telegram_bot_token="123:ABC", timezone="Марсианский")
        with pytest.raises(ValueError, match="часовой пояс"):
            _ = settings.tz

    def test_суммаризация_выключена_без_ключа(self) -> None:
        assert Settings(telegram_bot_token="123:ABC").summarization_enabled is False

    def test_суммаризация_включена_с_ключом(self) -> None:
        settings = Settings(telegram_bot_token="123:ABC", anthropic_api_key="sk-ant-test")
        assert settings.summarization_enabled is True

    def test_интервал_напоминаний_не_слишком_часто(self) -> None:
        with pytest.raises(ValidationError):
            Settings(telegram_bot_token="123:ABC", reminder_interval_seconds=1)
