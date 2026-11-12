# Развёртывание бота

У бота нет публичного адреса: он сам ходит в Telegram по long polling. Поэтому
выкладка устроена иначе, чем у веб-приложений из этого портфолио — здесь
нужны сервис, который поднимается после перезагрузки, и резервные копии
базы.

## Что должно быть на сервере

- Ubuntu 22.04 или новее;
- Docker Engine с плагином Compose (`docker compose`, не `docker-compose`).

## 1. Код и настройки

```bash
sudo git clone https://github.com/MeldanLess/study-bot.git /opt/study-bot
cd /opt/study-bot
cp .env.example .env
```

В `.env` — токен от [@BotFather](https://t.me/BotFather) и, по желанию, ключ
Anthropic API:

```
TELEGRAM_BOT_TOKEN=123456:ABC...
ANTHROPIC_API_KEY=sk-ant-...
```

Файл `.env` в `.gitignore`, а права на него стоит ограничить:

```bash
chmod 600 .env
```

## 2. Запуск

```bash
docker compose up -d
docker compose logs -f bot
```

В логах должно быть «Бот запущен, напоминания проверяются каждые 60 с».
Проверить, что бот отвечает, проще всего написать ему в Telegram: `/start`.

## 3. systemd

```bash
sudo cp deploy/study-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now study-bot
systemctl status study-bot
```

Юнит поднимает compose-стек и поднимает его после перезагрузки сервера.
`systemctl reload study-bot` подтянет новый образ и перезапустит контейнер.

## 4. Резервные копии

У бота всё данные — это один файл SQLite. Копия снимается через backup API
SQLite (она работает, пока база открыта, и делает снимок согласованным), а
старые копии удаляются.

```bash
sudo cp deploy/study-bot-backup.service /etc/systemd/system/
sudo cp deploy/study-bot-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now study-bot-backup.timer
systemctl list-timers study-bot-backup.timer
```

Проверить вручную:

```bash
sudo systemctl start study-bot-backup.service
journalctl -u study-bot-backup.service -n 20
ls -l data/backups
```

Копии лежат в `data/backups` рядом с базой. Копия на том же сервере — это
страховка от опечатки в боте, а не от потери сервера: для второго нужен
другой носитель, и это отдельная задача.

## Обновление

```bash
cd /opt/study-bot
git pull
sudo systemctl reload study-bot
```

## Откат

```bash
cd /opt/study-bot
git checkout v1.0.0
docker compose build
docker compose up -d
```

База при откате не трогается: она в каталоге `data`, а не в образе.

## Что здесь не сделано и почему

- **Бота не видно снаружи.** У него нет веб-интерфейса и нет вебхука: long
  polling не требует ни домена, ни сертификата, и это на одну деталь меньше.
  Если понадобится вебхук, нужен будет домен с HTTPS.
- **Резервные копии только на этом же сервере.** Копия на другом носителе —
  отдельная задача; пока её нет, потеря сервера означает потерю базы.
- **Пользователей много не будет.** База — SQLite, авторизации нет: бот
  работает с задачами того, кто ему пишет. Для одного человека этого
  достаточно, а для команды понадобился бы Postgres и разграничение прав.
