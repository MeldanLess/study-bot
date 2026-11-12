# syntax=docker/dockerfile:1

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Сначала зависимости: этот слой кэшируется и пересобирается только при
# изменении requirements.txt, а не при каждой правке исходников.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY studybot ./studybot

# Каталог с базой создаём заранее: он подключается снаружи, и без него
# контейнер стартует не с той точки монтирования.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app

# Бот не от root: ошибка в коде не должна давать root внутри контейнера.
USER appuser

# Бот ходит наружу сам (long polling к Telegram), входящих портов у него нет:
# публиковать нечего, и поэтому нечего закрывать.
CMD ["python", "-m", "studybot"]
