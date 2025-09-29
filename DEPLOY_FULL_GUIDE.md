# Полное руководство по деплою проекта `time_tracking` на голый сервер (Ubuntu/Debian)

Данный документ описывает пошаговый продакшен-деплой Django‑проекта на чистый VPS / сервер без Docker с использованием:
- Python (venv)
- PostgreSQL
- Redis (Celery broker + кеш Django + результаты задач)
- Gunicorn (WSGI)
- Nginx (reverse proxy, статика, медиа)
- Celery worker (+ beat при необходимости)
- Systemd юниты
- Скрипты blue/green деплоя (`deploy/prepare_release.sh`, `deploy/apply_release.sh`, `deploy/rollback_release.sh`)

> Все команды предполагают ОС: Ubuntu 22.04 LTS (аналогично для Debian 12 с минимальными отличиями). Выполняйте под пользователем с sudo (НЕ root напрямую — лучше через SSH-ключи).

---
## 0. Предпосылки
| Что | Описание |
|-----|----------|
| Домен | Пропишите A-запись на IP вашего сервера |
| Пользователь | Создайте sudo-пользователя (если ещё нет) |
| SSH | Настроен вход по ключу, пароль отключён (рекомендуется) |
| Часовой пояс | Настроен (Europe/Moscow или ваш) |
| Firewall | (опционально) ufw открыт для SSH, HTTP, HTTPS |

---
## 1. Создание пользователя и базовая защита (при необходимости)
```bash
# (Если вы всё ещё под root)
adduser deploy
usermod -aG sudo deploy

# Скопировать authorized_keys (если уже есть ключ у root):
rsync -av /root/.ssh /home/deploy/
chown -R deploy:deploy /home/deploy/.ssh
chmod 700 /home/deploy/.ssh && chmod 600 /home/deploy/.ssh/authorized_keys

# Настройка SSH демона (опционально):
sudo nano /etc/ssh/sshd_config
# Рекомендуется:
#   PermitRootLogin no
#   PasswordAuthentication no
sudo systemctl restart ssh
```
Опционально включите fail2ban, настроите ufw:
```bash
sudo apt install -y ufw
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

---
## 2. Системные пакеты
```bash
sudo apt update
sudo apt install -y python3-venv python3-dev build-essential libpq-dev \
  postgresql postgresql-contrib redis-server nginx git curl ca-certificates unzip
```
(Дополнительно: `htop`, `fail2ban`, `rsync`, `logrotate`, `certbot`.)

Настроить часовой пояс (если надо):
```bash
sudo timedatectl set-timezone Europe/Moscow
```

---
## 3. PostgreSQL: подготовка БД
```bash
sudo -u postgres psql
CREATE DATABASE time_tracking;
CREATE USER time_user WITH PASSWORD 'StrongSecretPass';
GRANT ALL PRIVILEGES ON DATABASE time_tracking TO time_user;
\q
```
(Используйте надёжный пароль; НЕ публикуйте его.)

Опционально: ограничить доступ снаружи — оставьте только локальное подключение через unix/127.0.0.1.

---
## 4. Redis: базовая настройка
Файл: `/etc/redis/redis.conf`
Рекомендуется убедиться в наличии строк:
```
supervised systemd
bind 127.0.0.1
protected-mode yes
# requirepass StrongRedisPass   # если хотите пароль (тогда обновите URL в .env)
```
Применить:
```bash
sudo systemctl enable --now redis-server
redis-cli ping  # ожидать PONG
```

---
## 5. Структура директорий проекта
```bash
sudo mkdir -p /srv/time_tracking/{app,env,run,logs,backups,media,deploy}
sudo chown -R $USER:$USER /srv/time_tracking
```
- `app/` — активная версия кода (prod)
- `env/` — единый виртуальный окружение Python
- `run/` — сокеты / pid файлы
- `logs/` — логи (app.log, celery.log)
- `backups/` — архивные версии кода (blue/green) и дампы
- `media/` — пользовательские файлы
- `deploy/` — скрипты деплоя (из репозитория)

---
## 6. Получение кода
### Способ A (рекомендуется) — Git
```bash
cd /srv/time_tracking/app
git clone <REPO_URL> .
```
### Способ B — через rsync с локальной машины
```bash
rsync -avz --delete \
  --exclude-from=deploy/rsync_exclude.txt \
  ./ user@SERVER:/srv/time_tracking/app/
```
### Способ C — архив
```bash
scp project_release.zip user@SERVER:/srv/time_tracking/
cd /srv/time_tracking
unzip project_release.zip -d app
```

---
## 7. Виртуальное окружение Python
```bash
python3 -m venv /srv/time_tracking/env
source /srv/time_tracking/env/bin/activate
pip install --upgrade pip
pip install -r /srv/time_tracking/app/requirements.txt
```

---
## 8. Файл окружения `.env`
В каталоге `app/` уже есть пример: `.env.example`.
```bash
cd /srv/time_tracking/app
cp .env.example .env
nano .env
```
Обязательно выставить:
```
DEBUG='False'
SECRET_KEY='замените_на_длинный_секрет'
ALLOWED_HOSTS='example.com,www.example.com'
DB_NAME='time_tracking'
DB_USER='time_user'
DB_PASS='StrongSecretPass'
```
Если Redis с паролем — обновите URL:
```
REDIS_CACHE_URL='redis://:StrongRedisPass@127.0.0.1:6379/2'
CELERY_BROKER_URL='redis://:StrongRedisPass@127.0.0.1:6379/0'
```
Права (опционально):
```bash
chmod 600 .env
```

---
## 9. Production settings
Используется модуль: `Time_tracking.settings_prod` (добавлен проектом). Включает:
- DEBUG=False
- STATIC_ROOT=static_collected
- Логирование в файлы
- django-redis кеш
- Отключён CELERY_TASK_ALWAYS_EAGER

Экспортируйте переменную (разово в оболочке или в systemd unit):
```bash
export DJANGO_SETTINGS_MODULE=Time_tracking.settings_prod
```

---
## 10. Миграции и статика
```bash
cd /srv/time_tracking/app
source ../env/bin/activate
export DJANGO_SETTINGS_MODULE=Time_tracking.settings_prod
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser  # (по необходимости)
python manage.py check --deploy
```

---
## 11. Тестовый запуск Gunicorn (вручную)
```bash
source /srv/time_tracking/env/bin/activate
export DJANGO_SETTINGS_MODULE=Time_tracking.settings_prod
gunicorn Time_tracking.wsgi:application --bind 127.0.0.1:8001 --workers 3
```
Проверка:
```bash
curl -I 127.0.0.1:8001/
```
Остановить (Ctrl+C).

---
## 12. Systemd unit для Gunicorn
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
sudo mkdir -p /srv/time_tracking/run
sudo chown www-data:www-data /srv/time_tracking/run
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
        alias /srv/time_tracking/media/;
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

---
## 14. HTTPS (Let’s Encrypt)
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d example.com -d www.example.com
```
Затем можно включить HSTS в `.env` (SECURE_HSTS_SECONDS=31536000) и настроить редирект на 443 (certbot делает это автоматически при выборе опции).

---
## 15. Celery: worker и beat
`/etc/systemd/system/celery_worker.service`:
```
[Unit]
Description=Celery Worker
After=network.target redis-server.service
Requires=redis-server.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/srv/time_tracking/app
Environment="DJANGO_SETTINGS_MODULE=Time_tracking.settings_prod"
Environment="PATH=/srv/time_tracking/env/bin"
Environment="CELERY_BROKER_URL=redis://127.0.0.1:6379/0"
Environment="CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/1"
ExecStart=/srv/time_tracking/env/bin/celery -A Time_tracking worker -l info --concurrency=3
Restart=always

[Install]
WantedBy=multi-user.target
```
(Опционально beat — аналогичный unit с ExecStart celery beat.)
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now celery_worker
sudo systemctl enable --now celery_beat  # если нужен
```
Проверка:
```bash
journalctl -u celery_worker -f
```

---
## 16. Кеширование (django-redis)
Уже настроено в `settings_prod.py` (CACHES['default']). Для включения кешированных сессий:
```
USE_CACHED_SESSIONS='True'
```
Для глобального page cache (осторожно!):
```
ENABLE_SITE_CACHE='True'
CACHE_MIDDLEWARE_SECONDS='60'
```

---
## 17. Health-check endpoint (рекомендуется)
Пример (создайте файл `services/health.py` и подключите url):
```python
# services/health.py
from django.http import JsonResponse
from django.core.cache import cache
from django.db import connections

def health_view(request):
    problems = []
    # DB
    try:
        connections['default'].cursor().execute('SELECT 1;')
    except Exception as e:
        problems.append(f'db:{e}')
    # Cache
    try:
        cache.set('health_ping', 'ok', 5)
        if cache.get('health_ping') != 'ok':
            problems.append('cache:set-get mismatch')
    except Exception as e:
        problems.append(f'cache:{e}')
    status = 'ok' if not problems else 'degraded'
    return JsonResponse({'status': status, 'problems': problems})
```
`urls.py`:
```python
from services.health import health_view
urlpatterns += [path('health/', health_view)]
```
Проверка:
```bash
curl -f http://127.0.0.1/health/
```

---
## 18. Blue/Green деплой (архив или rsync)
Скрипты уже в репозитории (`deploy/`). Рабочий цикл:
1. Локально собрать релиз (zip или rsync в `/srv/time_tracking/time_tracking_new`).
2. (Если архив) — загрузить архив и выполнить:
```bash
cd /srv/time_tracking
bash deploy/prepare_release.sh    # распаковывает в time_tracking_new/
```
3. Проверить содержимое `time_tracking_new/` (.env, миграции).
4. Применить:
```bash
bash deploy/apply_release.sh
```
Скрипт выполнит (до переключения): установки зависимостей (если изменился requirements.txt), миграции, collectstatic. Затем остановит сервисы, заменит директорию и перезапустит.
5. Откат при проблемах:
```bash
bash deploy/rollback_release.sh --list
bash deploy/rollback_release.sh --target app_YYYYmmdd_HHMMSS
```

---
## 19. Обновление зависимостей
Стратегии:
- Прямое обновление: `pip install -U пакет` → `pip freeze > requirements.txt` → деплой.
- pip-tools (добавить `requirements.in` и использовать `pip-compile`).
- Проверка устаревших: `pip list --outdated`.
- Проверка уязвимостей (дополнительно): `pip install safety && safety check -r requirements.txt`.

---
## 20. Бэкапы
### PostgreSQL
```bash
pg_dump -Fc -U time_user time_tracking > /srv/time_tracking/backups/db_$(date +%F_%H%M).dump
```
Cron (`crontab -e`):
```
0 2 * * * pg_dump -Fc -U time_user time_tracking > /srv/time_tracking/backups/db_$(date +\%F).dump
```
### Медиа
```bash
rsync -a /srv/time_tracking/media/ /backups/time_tracking_media/
```
### Код
Скрипты деплоя автоматически сохраняют старые версии (каталоги в `backups/`).

---
## 21. Логи
Файлы:
```
/srv/time_tracking/logs/app.log
/srv/time_tracking/logs/celery.log
```
Systemd журналы:
```bash
journalctl -u time_tracking_gunicorn -f
journalctl -u celery_worker -f
```
Пример logrotate `/etc/logrotate.d/time_tracking`:
```
/srv/time_tracking/logs/*.log {
  weekly
  rotate 8
  compress
  missingok
  notifempty
  copytruncate
}
```

---
## 22. Безопасность (минимум)
- Отключить root вход: `PermitRootLogin no`.
- Запретить пароли: `PasswordAuthentication no`.
- Ограничить ALLOWED_HOSTS (убрать `*`).
- Сменить SECRET_KEY (не держать в git).
- Резервное копирование БД + медиа ежедневно.
- Авто-обновления ОС (unattended-upgrades) или ручной цикл обновлений.
- HSTS после стабилизации HTTPS.
- Пароли сервисов ≥ 16 символов.
- Ограничить доступ к Redis (bind 127.0.0.1). Пароль при открытии наружу.

---
## 23. Траблшутинг (частые проблемы)
| Симптом | Возможная причина | Действие |
|---------|------------------|----------|
| 502 Bad Gateway | Gunicorn упал / нет сокета | `systemctl status time_tracking_gunicorn` |
| Celery задачи висят PENDING | Worker не подключён к брокеру | Проверить URL брокера, логи worker |
| Ошибки подключения к DB | Неверные креды / pg_hba.conf | Проверить .env, попробовать psql локально |
| 404 статика | Не выполняли collectstatic | Выполнить заново + проверить Nginx alias |
| Memory high | Слишком много workers/concurrency | Уменьшить Gunicorn workers / Celery concurrency |
| Cache не работает | Redis не доступен | `redis-cli ping`, проверить порт/пароль |

---
## 24. Быстрый cheat sheet
```bash
# Активировать окружение
source /srv/time_tracking/env/bin/activate
export DJANGO_SETTINGS_MODULE=Time_tracking.settings_prod

# Миграции / статика
python manage.py migrate
python manage.py collectstatic --noinput

# Сервисы
sudo systemctl restart time_tracking_gunicorn
sudo systemctl restart celery_worker

# Логи
journalctl -u time_tracking_gunicorn -f
journalctl -u celery_worker -f

# Redis / DB
redis-cli ping
psql -h 127.0.0.1 -U time_user -d time_tracking -c 'SELECT 1;'

# Blue/Green деплой
bash deploy/prepare_release.sh
bash deploy/apply_release.sh
bash deploy/rollback_release.sh --list

# Бэкап
pg_dump -Fc -U time_user time_tracking > backups/db_$(date +%F_%H%M).dump
```

---
## 25. Рекомендации развития
- Добавить Sentry (ошибки)
- Flower / Prometheus exporters (мониторинг)
- CI/CD (GitHub Actions → архив → ssh деплой)
- CDN / S3 для медиа (когда вырастут объёмы)
- Preload Gunicorn + graceful reload сигналы (минимальный простой)

---
### Готово
При следовании всем шагам вы получаете воспроизводимый, управляемый деплой с возможностью быстрого отката и расширения.

Если нужно — можно встроить автодамп БД в `apply_release.sh` перед переключением (обратитесь отдельно).

