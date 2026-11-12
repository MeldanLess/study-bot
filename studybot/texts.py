"""Все тексты бота — в одном месте.

Так их видно целиком, их легко тестировать и легко менять голос, не трогая
логику. Проверки текста живут здесь же: `format_due` отвечает на вопрос
«как бот показывает время», и ответ на него должен быть один.
"""

from __future__ import annotations

from datetime import datetime, tzinfo

from studybot.models import Task

MONTHS = (
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)

START = (
    "Привет! Я помогаю с учебными задачами.\n"
    "\n"
    "Что я умею:\n"
    "• /add Задача до завтра — добавить задачу с дедлайном;\n"
    "• /list — что осталось;\n"
    "• /done 3 — отметить задачу выполненной;\n"
    "• /note 3 текст — прикрепить заметку;\n"
    "• /summarize 3 — сжать заметку до трёх пунктов;\n"
    "• /help — эта справка.\n"
    "\n"
    "Срок можно написать словами: «сегодня», «завтра», «через 2 часа», "
    "«20.11», «20.11 18:00»."
)

HELP = START

NO_TASKS = "Пока ничего нет. Добавь первую задачу: /add Задача до завтра"

UNKNOWN_TASK = "Не нашёл задачу с номером {task_id}. Посмотри список: /list"

# Пример в ответе — тот же, что и команда, которую человек только что ввёл:
# подсказка «/done 3» в ответ на /note сбивает с толку.
EXAMPLE_DONE = "/done 3"
EXAMPLE_NOTE = "/note 3 текст"
EXAMPLE_SUMMARIZE = "/summarize 3"

NOT_A_NUMBER = "Номер задачи — это число. Например: {example}"

BAD_DATE = "Не понял срок «{raw}». Напиши так: «завтра», «через 2 часа», «20.11 18:00»"

EMPTY_TITLE = "А что именно сделать? Напиши: /add Задача до завтра"

NOTE_SAVED = "Заметку к задаче №{task_id} сохранил."

NO_NOTE = "У задачи №{task_id} нет заметки. Прикрепи: /note {task_id} текст"

SUMMARY = "Заметка к задаче №{task_id} — коротко:\n\n{summary}"

SUMMARY_FAILED = "Не получилось сжать заметку: {reason}"

SUMMARIZER_OFF = (
    "Суммаризация выключена: не задан ANTHROPIC_API_KEY. "
    "Задачи работают и без неё — заметку можно просто прочитать."
)

DUE_REMINDER = "⏰ {title}\n\nДедлайн был {due}."

DONE = "Отметил задачу №{task_id} выполненной."


def format_due(moment: datetime | None, tz: tzinfo) -> str:
    """Человеческое представление срока в часовом поясе пользователя."""
    if moment is None:
        return "без срока"
    local = moment.astimezone(tz)
    return f"{local.day} {MONTHS[local.month - 1]}, {local:%H:%M}"


def format_task(task: Task, tz: tzinfo) -> str:
    """Одна задача одной строкой."""
    mark = "✓" if task.done else "•"
    note = " · есть заметка" if task.note else ""
    return f"{mark} №{task.id} {task.title} — {format_due(task.due_at, tz)}{note}"


def format_tasks(tasks: list[Task], tz: tzinfo) -> str:
    """Список задач или сообщение о пустом списке."""
    if not tasks:
        return NO_TASKS
    return "\n".join(format_task(task, tz) for task in tasks)
