"""Настройки бота — всё приходит из переменных окружения.

Один источник правды: и бот, и тесты читают настройки отсюда. Файл `.env`
читается, но переменные окружения имеют приоритет: на сервере секреты кладутся
в окружение, а не в файл, который случайно уедет в репозиторий.
"""

from __future__ import annotations

from datetime import tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    telegram_bot_token: str = Field(..., description="Токен бота от @BotFather.")
    anthropic_api_key: str | None = Field(
        default=None,
        description="Ключ Anthropic API. Без него суммаризация выключена.",
    )
    anthropic_model: str = Field(
        default="claude-sonnet-5-5",
        description="Модель для суммаризации заметок.",
    )
    database_url: str = Field(
        default="sqlite+aiosqlite:///data/studybot.db",
        description="Адрес базы. SQLite — этого хватает для бота на одного человека.",
    )
    timezone: str = Field(
        default="Europe/Moscow",
        description="Часовой пояс: в нём бот понимает и показывает время.",
    )
    reminder_interval_seconds: int = Field(
        default=60,
        ge=10,
        le=3600,
        description="Как часто бот проверяет, кому пора напомнить.",
    )
    log_level: str = Field(default="INFO", description="Уровень логирования.")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def tz(self) -> tzinfo:
        """Часовой пояс, в котором бот понимает и показывает время."""
        try:
            return ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as error:
            raise ValueError(f"Неизвестный часовой пояс: {self.timezone}") from error

    @computed_field  # type: ignore[prop-decorator]
    @property
    def summarization_enabled(self) -> bool:
        """Включена ли суммаризация."""
        return bool(self.anthropic_api_key)
