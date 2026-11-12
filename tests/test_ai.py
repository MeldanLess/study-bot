"""Тесты суммаризатора.

API не вызывается: клиент подменяется, и проверяется, что именно уходит в
запрос. Это важно: сломанный промпт или неверная модель выглядят как
«модель отвечает ерундой», и найти это можно только здесь.
"""

from __future__ import annotations

from typing import Any

import pytest

from studybot.ai import (
    SYSTEM_PROMPT,
    AnthropicSummarizer,
    DisabledSummarizer,
    SummarizerUnavailable,
)


class FakeBlock:
    """Блок ответа модели."""

    def __init__(self, text: str, block_type: str = "text") -> None:
        self.text = text
        self.type = block_type


class FakeResponse:
    """Ответ модели."""

    def __init__(self, blocks: list[FakeBlock]) -> None:
        self.content = blocks


class FakeMessages:
    """Запоминает запрос и отдаёт заготовленный ответ."""

    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> FakeResponse:
        self.calls.append(kwargs)
        return self.response


class FakeClient:
    """Клиент Anthropic API, который никуда не ходит."""

    def __init__(self, response: FakeResponse) -> None:
        self.messages = FakeMessages(response)


class TestAnthropicSummarizer:
    """Запрос к модели."""

    async def test_запрос_собирается_верно(self) -> None:
        client = FakeClient(FakeResponse([FakeBlock("Коротко.")]))
        summarizer = AnthropicSummarizer(client, model="claude-test")

        result = await summarizer.summarize("длинная заметка")

        assert result == "Коротко."
        call = client.messages.calls[0]
        assert call["model"] == "claude-test"
        assert call["system"] == SYSTEM_PROMPT
        assert call["messages"] == [{"role": "user", "content": "длинная заметка"}]
        assert call["max_tokens"] > 0

    async def test_несколько_блоков_склеиваются(self) -> None:
        client = FakeClient(FakeResponse([FakeBlock("Первое. "), FakeBlock("Второе.")]))
        summarizer = AnthropicSummarizer(client, model="claude-test")
        assert await summarizer.summarize("заметка") == "Первое. Второе."

    async def test_нетекстовые_блоки_пропускаются(self) -> None:
        client = FakeClient(
            FakeResponse([FakeBlock("ignored", block_type="thinking"), FakeBlock("Итог.")])
        )
        summarizer = AnthropicSummarizer(client, model="claude-test")
        assert await summarizer.summarize("заметка") == "Итог."

    async def test_пустой_ответ_не_молчит(self) -> None:
        client = FakeClient(FakeResponse([]))
        summarizer = AnthropicSummarizer(client, model="claude-test")
        assert "пустой" in await summarizer.summarize("заметка")


class TestDisabledSummarizer:
    """Без ключа суммарировать нечем — и это видно."""

    async def test_отказ_явный(self) -> None:
        with pytest.raises(SummarizerUnavailable, match="ANTHROPIC_API_KEY"):
            await DisabledSummarizer().summarize("заметка")
