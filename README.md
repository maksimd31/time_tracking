# time_tracking

![Django](https://img.shields.io/badge/Django-4.x-green?logo=django)
![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python)

**time_tracking** — это современное веб-приложение для персонального учёта времени, разработанное на Django.

---

## 📖 Описание
Проект предназначен для отслеживания и анализа времени, потраченного на обучение или другие активности. Основная цель — помочь пользователю эффективно управлять своим временем и видеть статистику по затраченным часам.

---

## 🚀 Деплой
Приложение задеплоено без использования Docker: развёртывание осуществляется на сервере Linux с использованием Nginx и Gunicorn. 

🌐 Демо: [vremya.fun](https://vremya.fun)

---

## ⚙️ Основной функционал
- Аутентификация пользователей (регистрация, вход, смена пароля)
- Запуск и остановка отсчёта времени (кнопки "Старт" и "Стоп")
- Сохранение интервалов времени в базе данных
- Просмотр и редактирование сохранённых интервалов
- Просмотр ежедневной и суммарной статистики
- Профиль пользователя с возможностью редактирования

---

## 🛠️ Технологии
- Python 3
- Django
- HTML, CSS, JavaScript
- Gunicorn, Nginx (продакшн)

---

## 📝 План реализации
1. Проектирование структуры базы данных и моделей
2. Реализация аутентификации и регистрации пользователей
3. Создание интерфейса для запуска/остановки таймера
4. Сохранение и отображение временных интервалов
5. Реализация статистики и отчетов
6. Добавление профиля пользователя и его редактирования
7. Тестирование и исправление ошибок
8. Деплой проекта

---

## ▶️ Запуск проекта локально
1. Клонируйте репозиторий
2. Установите зависимости из requirements.txt
3. Выполните миграции:
   ```bash
   python manage.py migrate
   ```
4. Запустите сервер:
   ```bash
   python manage.py runserver
   ```
5. Перейдите по адресу http://127.0.0.1:8000/

---

## 🎯 Назначение
Проект создан для личного использования, но может быть полезен всем, кто хочет вести учёт времени, затраченного на различные задачи.

---

## 🗂️ История изменений
Смотрите подробную историю изменений и релизов в файле [CHANGELOG.md](CHANGELOG.md).

---

## 🌱 План будущих обновлений
- Добавление мобильной версии интерфейса
- Интеграция с календарями (Google Calendar, Outlook)
- Экспорт и импорт данных (CSV, Excel)
- Уведомления и напоминания
- Расширенная аналитика и графики
- Поддержка нескольких языков (i18n)
- Интеграция с внешними сервисами (например, Telegram-бот)
- Улучшение безопасности и приватности данных
- Расширенные настройки профиля пользователя
# Руководство по запуску

## Требования

- Python 3.13
- PostgreSQL 14+
- Redis 7+
- Node / npm не требуются (используются CDN стили)

## Установка зависимостей

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Настройка `.env`

Пример содержимого:

```
SECRET_KEY=...
DEBUG=True

DB_ENGINE=django.db.backends.postgresql
DB_NAME=djangodb
DB_USER=mb
DB_PASS=mb
DB_HOST=127.0.0.1
DB_PORT=5432

EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=example@gmail.com
EMAIL_HOST_PASSWORD=...
EMAIL_PORT=587
EMAIL_USE_TLS=True

CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0
CELERY_TASK_ALWAYS_EAGER=False
```

Для локальной разработки можно оставить `CELERY_TASK_ALWAYS_EAGER=True`, тогда задачи выполняются синхронно.

## Подготовка базы данных

```bash
python3 manage.py migrate
python3 manage.py createsuperuser
```

## Запуск локально (без Docker)

1. Активируйте виртуальное окружение и убедитесь, что PostgreSQL и Redis работают на `127.0.0.1`.
2. Запустите Celery-воркер:
   ```bash
   celery -A Time_tracking worker -l info
   ```
3. В другом терминале запустите Django-сервер:
   ```bash
   python3 manage.py runserver
   ```

## Запуск на сервере (без Docker)

1. Установите системные пакеты:
   - Python 3.13, PostgreSQL, Redis
   - virtualenv, build-essential, libpq-dev
2. Клонируйте проект, создайте виртуальное окружение, установите зависимости и настройте `.env` как выше, но `DEBUG=False` и `EMAIL_BACKEND` укажите на SMTP.
3. Настройте системные сервисы (пример systemd unit):

   `/etc/systemd/system/time-tracking.service`
   ```ini
   [Unit]
   Description=Gunicorn for time tracking
   After=network.target

   [Service]
   User=www-data
   WorkingDirectory=/opt/time_tracking
   EnvironmentFile=/opt/time_tracking/.env
   ExecStart=/opt/time_tracking/.venv/bin/gunicorn Time_tracking.wsgi:application --bind 0.0.0.0:8000
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

   `/etc/systemd/system/time-tracking-celery.service`
   ```ini
   [Unit]
   Description=Celery Worker for time tracking
   After=network.target redis.service

   [Service]
   User=www-data
   WorkingDirectory=/opt/time_tracking
   EnvironmentFile=/opt/time_tracking/.env
   ExecStart=/opt/time_tracking/.venv/bin/celery -A Time_tracking worker -l info
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

   Включите сервисы `sudo systemctl enable --now time-tracking.service time-tracking-celery.service`.
4. Раздачу статических файлов настройте через Nginx после `python3 manage.py collectstatic` (если `DEBUG=False`).

## Запуск вспомогательных сервисов в Docker (опционально)

`docker-compose.yml` содержит сервисы `postgres` и `redis`.

```bash
docker compose up -d
```

Убедитесь, что `.env` указывает `DB_HOST=127.0.0.1` и `CELERY_BROKER_URL=redis://127.0.0.1:6379/0`.
