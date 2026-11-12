"""Тест точки входа.

Бот без токена должен сказать об этом понятно и сразу, а не упасть с
трассировкой pydantic: первое, что видит человек, запустивший проект, — это
сообщение.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from studybot.__main__ import main


def test_без_токена_понятное_сообщение(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    # Уходим из каталога проекта: иначе подхватится случайный .env.
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit) as error:
        main()

    assert "TELEGRAM_BOT_TOKEN" in str(error.value)
