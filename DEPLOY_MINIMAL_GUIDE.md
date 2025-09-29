# Минимальное и оптимизированное руководство по деплою проекта `time_tracking`

Это упрощённый ("легковесный") гайд по деплою без Docker на слабый сервер (1–2 CPU / 1–2 GB RAM) с упором на:
- минимальный расход ресурсов
- быстрый отклик
- простое обновление через `git pull` / скрипт
- возможность со временем перейти к более продвинутому (blue/green) сценарию (см. `README_DEPLOY.md` / `DEPLOY_FULL_GUIDE.md`).

Если нужен полный развернутый вариант — используйте `DEPLOY_FULL_GUIDE.md`.

---
## 1. Целевая архитектура
```
Client → Nginx → (unix socket) → Gunicorn → Django → (PostgreSQL, Redis)
                       │
                       └─ статика /media с диска
```
Redis и Celery можно подключить позже. Для старта необходимы: Python + Nginx + Gunicorn + (PostgreSQL или SQLite).

---
## 2. Системные пакеты (Ubuntu 22.04 / Debian 12)
```bash
sudo apt update
sudo apt install -y python3-venv python3-dev build-essential libpq-dev \
  postgresql postgresql-contrib nginx git curl ca-certificates
# (Опционально) Redis, если планируете кеш и Celery:
sudo apt install -y redis-server
```

---
## 3. База данных (PostgreSQL) — можно отложить
```bash
sudo -u postgres psql
CREATE DATABASE time_tracking;\nCREATE USER time_user WITH PASSWORD 'StrongPass';\nGRANT ALL PRIVILEGES ON DATABASE time_tracking TO time_user;\n\q
```
Для самой первой обкатки можно временно использовать SQLite (но не для продакшена).

---
## 4. Структура директорий
```
/srv/time_tracking/
  app/       # git рабочая копия
  env/       # python venv
  run/       # gunicorn.sock / pid
  logs/      # при желании
  media/     # MEDIA_ROOT
  scripts/   # служебные скрипты (update.sh)
```
Создание:
```bash
sudo mkdir -p /srv/time_tracking/{app,env,run,logs,media,scripts}
sudo chown -R $USER:$USER /srv/time_tracking
```

---
## 5. Клонирование кода
```bash
cd /srv/time_tracking/app
git clone <REPO_URL> .
```

---
## 6. Виртуальное окружение и зависимости
```bash
python3 -m venv /srv/time_tracking/env
source /srv/time_tracking/env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt --no-cache-dir
```

---
## 7. Конфигурация окружения `.env`
Скопируйте пример (если есть `.env.example`) и отредактируйте:
```
DEBUG=False
SECRET_KEY=замените_на_длинный_секрет
ALLOWED_HOSTS=example.com,www.example.com
DB_ENGINE=django.db.backends.postgresql
DB_NAME=time_tracking
DB_USER=time_user
DB_PASS=StrongPass
DB_HOST=127.0.0.1
DB_PORT=5432
```
(Если пока SQLite — можно не задавать DB_*.)

---
## 8. Production settings: `settings_prod.py`
Создайте файл `Time_tracking/settings_prod.py` (если не существует):
```python
from .settings import *  # noqa

DEBUG = False
ALLOWED_HOSTS = [h for h in os.environ.get('ALLOWED_HOSTS', 'localhost').split(',') if h]
STATIC_ROOT = BASE_DIR / 'static_collected'

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

CELERY_TASK_ALWAYS_EAGER = False  # на случай, если добавите Celery
```
(Позже можно расширить логирование / кеш.)

---
## 9. Миграции и статика
```bash
cd /srv/time_tracking/app
source ../env/bin/activate
export DJANGO_SETTINGS_MODULE=Time_tracking.settings_prod
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser  # при необходимости
python manage.py check --deploy
```

---
## 10. Тестовый запуск Gunicorn
```bash
gunicorn Time_tracking.wsgi:application \
  --env DJANGO_SETTINGS_MODULE=Time_tracking.settings_prod \
  --bind 127.0.0.1:8001 --workers 2 --threads 2 --timeout 120
```
Проверьте: `curl -I 127.0.0.1:8001/` затем остановите (Ctrl+C).

---
## 11. systemd unit (Gunicorn через unix socket)
Файл `/etc/systemd/system/time_tracking_gunicorn.service`:
```
[Unit]
Description=Gunicorn Time Tracking
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/srv/time_tracking/app
Environment="DJANGO_SETTINGS_MODULE=Time_tracking.settings_prod"
Environment="PATH=/srv/time_tracking/env/bin"
ExecStart=/srv/time_tracking/env/bin/gunicorn Time_tracking.wsgi:application \
  --bind unix:/srv/time_tracking/run/gunicorn.sock \
  --workers 2 --threads 2 --timeout 120 --graceful-timeout 30 \
  --access-logfile - --error-logfile -
Restart=on-failure

[Install]
WantedBy=multi-user.target
```
Активация:
```bash
sudo chown -R www-data:www-data /srv/time_tracking/run
sudo systemctl daemon-reload
sudo systemctl enable --now time_tracking_gunicorn
sudo systemctl status time_tracking_gunicorn
```

---
## 12. Nginx конфиг
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
Включение:
```bash
sudo ln -s /etc/nginx/sites-available/time_tracking /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```
TLS (по желанию):
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d example.com -d www.example.com
```

---
## 13. Простое обновление (git pull + миграции)
Скрипт `/srv/time_tracking/scripts/update.sh` (создайте вручную на сервере):
```bash
#!/usr/bin/env bash
set -euo pipefail
APP_DIR="/srv/time_tracking/app"
VENV="/srv/time_tracking/env"
SERVICE="time_tracking_gunicorn"
DJANGO_SETTINGS="Time_tracking.settings_prod"
REQ_FILE="$APP_DIR/requirements.txt"
HASH_FILE="$APP_DIR/.req.hash"

cd "$APP_DIR"
echo "[1] git fetch/pull"
git fetch --all --prune
git reset --hard origin/main

source "$VENV/bin/activate"
NEW_HASH=$(sha256sum "$REQ_FILE" | awk '{print $1}')
OLD_HASH=""; [ -f "$HASH_FILE" ] && OLD_HASH=$(cat "$HASH_FILE")
if [ "$NEW_HASH" != "$OLD_HASH" ]; then
  echo "[2] requirements changed -> reinstall"
  pip install --no-cache-dir -r "$REQ_FILE"
  echo "$NEW_HASH" > "$HASH_FILE"
else
  echo "[2] requirements unchanged"
fi

export DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS
python manage.py migrate --noinput
python manage.py collectstatic --noinput

echo "[3] reload gunicorn"
sudo systemctl reload "$SERVICE" || sudo systemctl restart "$SERVICE"

echo "[4] done"
```
Права:
```bash
chmod +x /srv/time_tracking/scripts/update.sh
```
Использование:
```bash
bash /srv/time_tracking/scripts/update.sh
```

---
## 14. Health-check (опционально)
Простой view:
```python
from django.http import JsonResponse

def health(request):
    return JsonResponse({"status": "ok"})
```
`urls.py`:
```python
from path.to.view import health
urlpatterns += [path('health/', health)]
```
Проверка:
```bash
curl -f http://127.0.0.1/health/
```

---
## 15. Оптимизация под слабый сервер
- Gunicorn: workers=2 (1 vCPU) или 3 (2 vCPU); threads=2.
- Не включайте preload (экономия RAM). Добавите позже для быстрого reload.
- DEBUG=False обязательно.
- Меньше логирования (оставьте только ошибочное/важное).
- Кэш (Redis / LocMem) для горячих фрагментов шаблонов.
- Следите за RAM: `htop`, уменьшайте workers при OOM.

---
## 16. Быстрая шпаргалка
```bash
# Активировать окружение
source /srv/time_tracking/env/bin/activate
export DJANGO_SETTINGS_MODULE=Time_tracking.settings_prod

# Миграции / статика
python manage.py migrate
python manage.py collectstatic --noinput

# Сервис gunicorn
sudo systemctl status time_tracking_gunicorn
sudo systemctl reload time_tracking_gunicorn

# Обновление
bash /srv/time_tracking/scripts/update.sh

# Логи
journalctl -u time_tracking_gunicorn -f

# Проверка
curl -I https://example.com
curl -f http://127.0.0.1/health/
```

---
## 17. Чеклист перед продом
[ ] SECRET_KEY задан и уникален
[ ] DEBUG=False
[ ] ALLOWED_HOSTS без '*'
[ ] Миграции применены
[ ] Статика собрана (static_collected есть)
[ ] Nginx конфиг валиден (nginx -t)
[ ] Gunicorn сервис active
[ ] Health-check ok
[ ] HTTPS работает

---
## 18. Как обновить в 3 шага
1. Локально: git push main
2. На сервере: `bash /srv/time_tracking/scripts/update.sh`
3. Проверить health: `curl -f http://127.0.0.1/health/`

Rollback (простой): `git checkout <старый_коммит>` + повторный `update.sh`.

---
## 19. Следующие шаги (при росте)
- Добавить Celery + Redis (очереди задач)
- Включить Sentry / мониторинг
- Перейти на releases/ + blue/green для безпростойного релиза
- CDN или S3 для медиа, если вырастут

---
Готово. Этот файл описывает минимальный быстрый сценарий. За расширенной версией обращайтесь к `DEPLOY_FULL_GUIDE.md`.

