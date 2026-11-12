"""Суммаризация заметки через Anthropic API.

Фича необязательная, и в этом её главное свойство: без ключа бот честно
говорит, что суммарировать нечем, а не делает вид, что всё работает. Тихий
отказ хуже явного — человек ждёт ответа и не понимает, что что-то сломалось.

Сам вызов намеренно узкий: одна модель, один системный промпт, короткий
ответ. Всё, что можно вынести в настройки, вынесено.
"""

from __future__ import annotations

from typing import Any, Protocol

SYSTEM_PROMPT = (
    "Ты — помощник студента. Сожми заметку до трёх пунктов: что нужно сделать, "
    "что уже сделано и что осталось непонятным. Отвечай по-русски, коротко, "
    "без вступлений. Если в заметке нет дел, скажи об этом одной фразой."
)

DEFAULT_MAX_TOKENS = 600


class SummarizerUnavailable(RuntimeError):
    """Суммарировать нечем: ключ API не задан."""


class Summarizer(Protocol):
    """Умеет сжимать текст до короткого пересказа."""

    async def summarize(self, note: str) -> str:
        """Возвращает короткий пересказ заметки."""
        ...


class AnthropicSummarizer:
    """Суммаризатор на Anthropic API."""

    def __init__(self, client: Any, model: str, max_tokens: int = DEFAULT_MAX_TOKENS) -> None:
        self._client = client
        self._model = model
        self._max_tokens = max_tokens

    async def summarize(self, note: str) -> str:
        """Просит модель сжать заметку."""
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": note}],
        )
        parts = [
            block.text
            for block in response.content
            if getattr(block, "type", "") == "text" and getattr(block, "text", "")
        ]
        summary = "".join(parts).strip()
        return summary or "Модель вернула пустой ответ."


class DisabledSummarizer:
    """Заглушка на случай, когда ключа нет."""

    async def summarize(self, _note: str) -> str:
        """Всегда отказывается — и это видно вызывающему коду."""
        raise SummarizerUnavailable("Не задан ANTHROPIC_API_KEY — суммарирование выключено.")
