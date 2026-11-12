# Команды проекта. Короткие имена для рутины, полные команды — в README.
#
#     make install   — поставить зависимости
#     make test      — прогнать тесты
#     make lint      — проверить стиль
#     make coverage  — прогнать тесты и посчитать покрытие
#     make run       — запустить бота
#     make backup    — снять резервную копию базы
#     make docker    — собрать и запустить контейнер

PYTHON ?= python
PIP ?= $(PYTHON) -m pip

.PHONY: help install test coverage lint format run backup docker clean

help:
	@echo "install  — поставить зависимости"
	@echo "test     — прогнать тесты"
	@echo "coverage — прогнать тесты и посчитать покрытие"
	@echo "lint     — проверить стиль (Ruff)"
	@echo "format   — переформатировать код (Ruff)"
	@echo "run      — запустить бота"
	@echo "backup   — снять резервную копию базы"
	@echo "docker   — собрать и запустить контейнер"

install:
	$(PIP) install -r requirements.txt -r requirements-dev.txt

test:
	$(PYTHON) -m pytest -q

coverage:
	$(PYTHON) -m pytest --cov=studybot --cov-report=term-missing

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

format:
	$(PYTHON) -m ruff format .

run:
	$(PYTHON) -m studybot

backup:
	$(PYTHON) -m studybot.backup --source data/studybot.db --target data/backups

docker:
	docker compose up -d

clean:
	rm -rf .pytest_cache .ruff_cache .coverage coverage.xml
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
