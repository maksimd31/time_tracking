# README_DEPLOY.md

Подробное руководство по продакшен-деплою проекта **time_tracking** на сервер без Docker с использованием: **Nginx + Gunicorn + PostgreSQL + Redis + Celery (worker/beat)**.

---
## 0. Быстрый TL;DR для опытных
1. Установить системные пакеты (Python, Postgres, Redis, Nginx, git).
2. Создать /srv/time_tracking/{app,env,run,logs,g bakcups} и клонировать репозиторий в app/.
3. python -m venv env && source env/bin/activate && pip install -r requirements.txt
4. Скопировать `.env.example` -> `.env`, заполнить, настроить `ALLOWED_HOSTS` и ключи.
5. export DJANGO_SETTINGS_MODULE=Time_tracking.settings_prod
6. migrate, collectstatic, создать суперпользователя.
7. systemd unit: time_tracking_gunicorn + celery_worker (+ celery_beat).
8. Настроить Nginx на unix сокет /srv/time_tracking/run/gunicorn.sock.
9. HTTPS через certbot.
10. Деплой обновлений: `deploy/prepare_release.sh` -> (проверка) -> `deploy/apply_release.sh`.
11. Rollback: `deploy/rollback_release.sh --list` / `--target`.

---
## 1. Обзор
Проект — Django приложение для учёта времени. Прод окружение предусматривает:
- Gunicorn (WSGI) как приложение
- Nginx как reverse proxy + статика/медиа
- PostgreSQL как основная БД
- Redis как брокер и/или backend результатов Celery
- Celery worker (и при необходимости beat для периодических задач)
- Systemd для управления сервисами

### 1.1 Архитектура (упрощённо)
```
[Browser]
   │
   ▼
[Nginx]  -- (serve /static, /media) -->  Файловая система
   │
   ├── proxy_pass -> unix:/srv/time_tracking/run/gunicorn.sock -> [Gunicorn -> Django]
   │
   └── /sitemap.xml и прочие URL → Django

[Django] <-> [PostgreSQL]
[Django] <-> [Redis] (broker + results + (опц.) cache)

Celery Worker <-> Redis <-> Django
Celery Beat   <-> Redis (расписание) (опционально)
```

---
## 2. Минимальные требования сервера
| Компонент      | Рекомендовано                |
|----------------|------------------------------|
| CPU            | 1–2 ядра для старта          |
| RAM            | 1–2 GB                       |
| OS             | Ubuntu 22.04 LTS / Debian 12 |
| Python         | 3.11 / 3.12                  |
| PostgreSQL     | 14+                          |
| Redis          | 6+ / 7+                      |

---
## 3. Структура директорий (рекомендуемый layout)
```
/srv/time_tracking/
  app/                 # git clone (или текущая активная версия)
  env/                 # python venv (общий)
  run/                 # gunicorn.sock, pid-файлы
  logs/                # логи приложения / celery
  backups/             # старые версии (blue/green переключения)
  media/               # (если MEDIA_ROOT вынесен отдельно)
  deploy/              # скрипты деплоя
```

---
## 4. Переменные окружения
См. файл: `.env.example` (в репозитории). Создайте `.env` на сервере (НЕ коммить в git):
```bash
cp .env.example .env
# Отредактируйте SECRET_KEY, ALLOWED_HOSTS, SMTP и OAuth ключи
```
Критично: `SECRET_KEY`, `DEBUG=False`, корректные `DB_*`.

---
## 5. Production settings
Используйте модуль: `Time_tracking.settings_prod` (файл `Time_tracking/settings_prod.py`). Отличия:
- DEBUG=False
- STATIC_ROOT=static_collected
- Логирование в файлы (app.log, celery.log) в каталоге logs
- Отключён CELERY_TASK_ALWAYS_EAGER
- Опции безопасности (SECURE_*, HSTS и т.д.)

Экспорт перед командами:
```bash
export DJANGO_SETTINGS_MODULE=Time_tracking.settings_prod
```

---
## 6. Установка системных пакетов (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install -y python3-venv python3-dev build-essential libpq-dev \
  postgresql postgresql-contrib redis-server nginx git curl ca-certificates unzip
```
(Опционально: `ufw`, `fail2ban`.)

---
## 7. Настройка PostgreSQL
```bash
sudo -u postgres psql
CREATE DATABASE time_tracking;
CREATE USER time_user WITH PASSWORD 'StrongSecretPass';
GRANT ALL PRIVILEGES ON DATABASE time_tracking TO time_user;
\q
```
В `.env` пропишите значения.

---
## 8. Настройка Redis
`/etc/redis/redis.conf`:
```
supervised systemd
bind 127.0.0.1
protected-mode yes
# requirepass StrongRedisPass
```
Перезапуск и автозапуск:
```bash
sudo systemctl enable --now redis-server
redis-cli ping
```

---
## 9. Клонирование проекта и виртуальное окружение
```bash
sudo mkdir -p /srv/time_tracking/{app,env,run,logs,backups}
sudo chown -R $USER:$USER /srv/time_tracking
cd /srv/time_tracking/app
git clone <REPO_URL> .
python3 -m venv ../env
source ../env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---
## 10. Миграции и статические файлы
```bash
export DJANGO_SETTINGS_MODULE=Time_tracking.settings_prod
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser  # опционально
python manage.py check --deploy
```

---
## 11. Тестовый запуск Gunicorn
```bash
source /srv/time_tracking/env/bin/activate
export DJANGO_SETTINGS_MODULE=Time_tracking.settings_prod
gunicorn Time_tracking.wsgi:application --bind 127.0.0.1:8001 --workers 3
```

---
## 12. Systemd unit для Gunicorn (unix socket)
`/etc/systemd/system/time_tracking_gunicorn.service`:
```
[Unit]
Description=Gunicorn TimeTracking
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/srv/time_tracking/app
Environment="DJANGO_SETTINGS_MODULE=Time_tracking.settings_prod"
Environment="PATH=/srv/time_tracking/env/bin"
ExecStart=/srv/time_tracking/env/bin/gunicorn Time_tracking.wsgi:application \
  --bind unix:/srv/time_tracking/run/gunicorn.sock \
  --workers 3 --timeout 120 --graceful-timeout 30
Restart=on-failure

[Install]
WantedBy=multi-user.target
```
Активация:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now time_tracking_gunicorn
sudo systemctl status time_tracking_gunicorn
```

---
## 13. Nginx конфигурация
`/etc/nginx/sites-available/time_tracking`:
```
server {
    listen 80;
    server_name example.com www.example.com;

    client_max_body_size 20M;

    location /static/ {
        alias /srv/time_tracking/app/static_collected/;
        add_header Cache-Control "public, max-age=604800";
    }

    location /media/ {
        alias /srv/time_tracking/media/; # если MEDIA_ROOT вынесен наружу
    }

    location / {
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_pass http://unix:/srv/time_tracking/run/gunicorn.sock;
    }
}
```
Активация:
```bash
sudo ln -s /etc/nginx/sites-available/time_tracking /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```
HTTPS (Let’s Encrypt):
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d example.com -d www.example.com
```

---
## 14. Celery: worker и beat
`/etc/systemd/system/celery_worker.service` и `celery_beat.service` (пример уже был выше, не дублируем). Обновите пути если меняли структуру.

---
## 15. Скрипты автоматизации деплоя (blue/green)
В каталоге `deploy/` добавлены скрипты:

| Скрипт | Назначение |
|--------|------------|
| `prepare_release.sh` | Распаковка архива новой версии в `time_tracking_new/`, копирование .env, проверка зависимостей |
| `apply_release.sh` | Предварительная установка зависимостей, миграции, collectstatic, остановка сервисов, переключение директорий, запуск сервисов, health-check |
| `rollback_release.sh` | Откат к предыдущей версии из `backups/` |

Процесс обновления:
1. Скопировать архив новой версии (zip или tar.gz) в корень `/srv/time_tracking`.
2. Выполнить: `bash deploy/prepare_release.sh` (создаст `time_tracking_new/`).
3. Проверить содержимое (settings_prod, статика, миграции). При необходимости отредактировать `.env`.
4. Выполнить: `bash deploy/apply_release.sh`.
5. При неудаче: `bash deploy/rollback_release.sh --list` и затем `bash deploy/rollback_release.sh --target app_YYYYmmdd_HHMMSS`.

Особенности:
- Старые версии складываются в `backups/` (именование: `app_YYYYmmdd_HHMMSS`).
- По умолчанию зависимости ставятся только если изменился `requirements.txt`.
- Миграции и collectstatic выполняются ДО переключения.
- Health-check (локальный) после запуска.

---
## 16. Логи и лог-ротация
(см. предыдущий раздел — без изменений) Настройте logrotate если нужно.

---
## 17. Zero-downtime деплой (базовый)
Можно использовать последовательность из раздела 15. Для более мягкого reload — добавьте `--preload` к Gunicorn и используйте `systemctl reload`, либо сигналы USR2 (не описано тут подробно).

---
## 18. Health-check endpoint
Рекомендуется создать простой view `/health/` и использовать его в мониторинге.

---
## 19. Резервное копирование
(Без изменений относительно предыдущей версии README) — pg_dump + rsync медиа.

---
## 20. Безопасность
(См. предыдущий раздел — ключевые пункты: SSH-ключи, обновления, HSTS, ограничение ALLOWED_HOSTS.)

---
## 21. Траблшутинг
(Таблица сохранена из предыдущей версии — не дублируем.)

---
## 22. Масштабирование
(Как и ранее: горизонтальное масштабирование, кеш, Sentry, мониторинг.)

---
## 23. Быстрые команды шпаргалка
```bash
# Активация окружения
source /srv/time_tracking/env/bin/activate

# Миграции / статика
python manage.py migrate --settings=Time_tracking.settings_prod
python manage.py collectstatic --noinput --settings=Time_tracking.settings_prod

# Celery
celery -A Time_tracking worker -l info
celery -A Time_tracking beat -l info

# Gunicorn тест
gunicorn Time_tracking.wsgi:application --bind 127.0.0.1:8001 --workers 3 \
  --env DJANGO_SETTINGS_MODULE=Time_tracking.settings_prod

# Проверка Redis
redis-cli ping

# Проверка PostgreSQL
psql -h 127.0.0.1 -U time_user -d time_tracking -c "SELECT 1;"

# Логи
journalctl -u time_tracking_gunicorn -f
journalctl -u celery_worker -f

# Blue/green deploy
bash deploy/prepare_release.sh
bash deploy/apply_release.sh
# Откат
bash deploy/rollback_release.sh --list
bash deploy/rollback_release.sh --target app_YYYYmmdd_HHMMSS
```

---
## 24. Pre-flight чеклист
| Шаг | Команда / Проверка |
|-----|---------------------|
| Настройки | `python manage.py check --deploy` |
| Миграции | `python manage.py showmigrations` |
| Режим | `DEBUG=False` и settings_prod используется |
| Статика | Файлы в `static_collected/` есть |
| Секреты | SECRET_KEY, SMTP заданы, ALLOWED_HOSTS без `*` |
| Gunicorn | `systemctl status time_tracking_gunicorn` active |
| Celery | `systemctl status celery_worker` active |
| Redis | `redis-cli info | head` |
| Postgres | psql подключение успешно |
| HTTPS | `curl -I https://example.com` 200/301 |
| Health-check | `curl -f http://127.0.0.1/health/` ok |

---
**Готово.** Используйте раздел 15 для безопасных обновлений и быстрых откатов.
