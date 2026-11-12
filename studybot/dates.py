"""Разбор срока из человеческого текста.

Человек в Telegram пишет «завтра», «через 2 часа», «20.11», «20.11 18:00» — и
редко пишет ISO-формат. Бот понимает то, что реально пишут, и говорит прямо,
когда не понял: «не понял срок» честнее, чем молчаливый дедлайн не туда.

Правила:

* дата без времени — это 09:00 по часовому поясу пользователя;
* «сегодня» — конец сегодняшнего дня (23:59), а не «сейчас»;
* «завтра» и «послезавтра» — 09:00 соответствующего дня;
* «через N минут / часов / дней» — от текущего момента;
* год без указания — ближайший будущий: если дата в этом году уже прошла,
  берётся следующий год;
* всё, что бот хранит, — в UTC. Часовой пояс нужен для разбора и для показа
  времени человеку, но не для хранения.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta, tzinfo

# Время по умолчанию, когда указана только дата.
DEFAULT_HOUR = 9
DEFAULT_MINUTE = 0

# Конец дня — для «сегодня».
END_OF_DAY = (23, 59)

# Единицы измерения, которые понимает бот.
UNITS = {
    "минуту": "minutes",
    "минуты": "minutes",
    "минут": "minutes",
    "минута": "minutes",
    "час": "hours",
    "часа": "hours",
    "часов": "hours",
    "день": "days",
    "дня": "days",
    "дней": "days",
}

RELATIVE = re.compile(r"^через\s+(\d+)\s+([а-яё]+)$")
DAY_MONTH = re.compile(r"^(\d{1,2})\.(\d{1,2})(?:\s+(\d{1,2}):(\d{2}))?$")
YEAR_MONTH_DAY = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})(?:\s+(\d{1,2}):(\d{2}))?$")

# Слова, из которых понятен день без даты.
KEYWORD_DAYS = {
    "сегодня": 0,
    "завтра": 1,
    "послезавтра": 2,
}


class DateParseError(ValueError):
    """Срок не удалось понять."""


def normalize(text: str) -> str:
    """Приводит текст к виду, с которым удобно работать."""
    cleaned = text.strip().lower().replace("ё", "е")
    return re.sub(r"\s+", " ", cleaned)


def parse_due(text: str, *, now: datetime, tz: tzinfo) -> datetime:
    """Разбирает срок и возвращает момент в UTC.

    `now` передаётся снаружи, а не берётся из `datetime.now()`: так разбор
    можно проверить на конкретной секунде, и он не зависит от того, когда
    запустился тест.
    """
    if now.tzinfo is None:
        raise ValueError("Текущее время должно быть с часовым поясом.")

    cleaned = normalize(text)
    if not cleaned:
        raise DateParseError("Срок пустой.")

    local_now = now.astimezone(tz)

    if cleaned in KEYWORD_DAYS:
        day = local_now + timedelta(days=KEYWORD_DAYS[cleaned])
        if cleaned == "сегодня":
            # «Сегодня» — это конец сегодняшнего дня, а не «сейчас»: человек
            # пишет «сегодня» про задачу на сегодня, а не про следующий час.
            return _local(day.replace(hour=END_OF_DAY[0], minute=END_OF_DAY[1]), tz)
        return _local(day.replace(hour=DEFAULT_HOUR, minute=DEFAULT_MINUTE), tz)

    relative = RELATIVE.match(cleaned)
    if relative:
        amount = int(relative.group(1))
        unit = UNITS.get(relative.group(2))
        if unit is None:
            raise DateParseError(f"Не понимаю единицу «{relative.group(2)}».")
        if amount <= 0:
            raise DateParseError("Сколько именно? Нужно положительное число.")
        return (now + timedelta(**{unit: amount})).astimezone(UTC)

    day_month = DAY_MONTH.match(cleaned)
    if day_month:
        day, month = int(day_month.group(1)), int(day_month.group(2))
        hour = int(day_month.group(3)) if day_month.group(3) else DEFAULT_HOUR
        minute = int(day_month.group(4)) if day_month.group(4) else DEFAULT_MINUTE
        year = _nearest_year(local_now, month, day)
        return _local(datetime(year, month, day, hour, minute), tz)

    full = YEAR_MONTH_DAY.match(cleaned)
    if full:
        year, month, day = int(full.group(1)), int(full.group(2)), int(full.group(3))
        hour = int(full.group(4)) if full.group(4) else DEFAULT_HOUR
        minute = int(full.group(5)) if full.group(5) else DEFAULT_MINUTE
        return _local(datetime(year, month, day, hour, minute), tz)

    raise DateParseError(f"Не понял срок «{text.strip()}».")


def _nearest_year(now: datetime, month: int, day: int) -> int:
    """Год для даты без года: ближайший, в который дата ещё не прошла."""
    try:
        candidate = now.replace(month=month, day=day, hour=0, minute=0)
    except ValueError as error:
        raise DateParseError("Такой даты не бывает.") from error
    if candidate < now:
        return now.year + 1
    return now.year


def _local(moment: datetime, tz: tzinfo) -> datetime:
    """Осознанное местное время → UTC."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=tz)
    return moment.astimezone(UTC)
