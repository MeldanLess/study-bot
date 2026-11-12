"""Тесты разбора срока.

Разбор — место, где чаще всего живут тихие ошибки: «завтра» в 23:59, год
не тот, минуты вместо часов. Поэтому здесь проверяется каждое правило
отдельно, на фиксированном моменте времени.
"""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from studybot.dates import DateParseError, parse_due

TZ = ZoneInfo("Europe/Moscow")
NOW = datetime(2026, 11, 12, 10, 0, tzinfo=TZ).astimezone(UTC)


class TestKeywords:
    """Слова вместо дат."""

    def test_сегодня_это_конец_дня(self) -> None:
        result = parse_due("сегодня", now=NOW, tz=TZ)
        assert result == datetime(2026, 11, 12, 20, 59, tzinfo=UTC)

    def test_завтра_это_девять_утра(self) -> None:
        result = parse_due("завтра", now=NOW, tz=TZ)
        assert result == datetime(2026, 11, 13, 6, 0, tzinfo=UTC)

    def test_послезавтра(self) -> None:
        result = parse_due("послезавтра", now=NOW, tz=TZ)
        assert result == datetime(2026, 11, 14, 6, 0, tzinfo=UTC)

    def test_регистр_и_пробелы_не_важны(self) -> None:
        assert parse_due("  ЗАВТРА ", now=NOW, tz=TZ) == parse_due("завтра", now=NOW, tz=TZ)


class TestRelative:
    """«Через N …» — от текущего момента."""

    def test_через_часы(self) -> None:
        assert parse_due("через 2 часа", now=NOW, tz=TZ) == datetime(2026, 11, 12, 9, 0, tzinfo=UTC)

    def test_через_минуты(self) -> None:
        assert parse_due("через 90 минут", now=NOW, tz=TZ) == datetime(
            2026, 11, 12, 8, 30, tzinfo=UTC
        )

    def test_через_дни(self) -> None:
        assert parse_due("через 3 дня", now=NOW, tz=TZ) == datetime(2026, 11, 15, 7, 0, tzinfo=UTC)

    def test_неизвестная_единица(self) -> None:
        with pytest.raises(DateParseError, match="единицу"):
            parse_due("через 5 недель", now=NOW, tz=TZ)

    def test_ноль_не_проходит(self) -> None:
        with pytest.raises(DateParseError, match="положительное"):
            parse_due("через 0 часов", now=NOW, tz=TZ)


class TestDates:
    """Даты цифрами."""

    def test_дата_без_года(self) -> None:
        assert parse_due("20.11", now=NOW, tz=TZ) == datetime(2026, 11, 20, 6, 0, tzinfo=UTC)

    def test_прошедшая_дата_берёт_следующий_год(self) -> None:
        assert parse_due("01.11", now=NOW, tz=TZ) == datetime(2027, 11, 1, 6, 0, tzinfo=UTC)

    def test_дата_со_временем(self) -> None:
        assert parse_due("20.11 18:30", now=NOW, tz=TZ) == datetime(
            2026, 11, 20, 15, 30, tzinfo=UTC
        )

    def test_полный_формат(self) -> None:
        assert parse_due("2026-12-01 08:00", now=NOW, tz=TZ) == datetime(
            2026, 12, 1, 5, 0, tzinfo=UTC
        )

    def test_несуществующая_дата(self) -> None:
        with pytest.raises(DateParseError, match="не бывает"):
            parse_due("32.13", now=NOW, tz=TZ)


class TestErrors:
    """Непонятный срок — это ошибка, а не молчание."""

    def test_пустой_срок(self) -> None:
        with pytest.raises(DateParseError, match="пустой"):
            parse_due("   ", now=NOW, tz=TZ)

    def test_непонятный_срок(self) -> None:
        with pytest.raises(DateParseError, match="Не понял срок"):
            parse_due("когда-нибудь", now=NOW, tz=TZ)

    def test_наивное_текущее_время_отвергается(self) -> None:
        naive = datetime(2026, 11, 12, 10, 0)
        with pytest.raises(ValueError, match="часовым поясом"):
            parse_due("завтра", now=naive, tz=TZ)
