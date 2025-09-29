import multiprocessing
import os
from pathlib import Path

# Базовая директория проекта
BASE_DIR = Path(__file__).resolve().parent.parent

# Настройки из переменных окружения (с дефолтами)
HOST = os.getenv("GUNICORN_HOST", "127.0.0.1")
PORT = os.getenv("GUNICORN_PORT", "8001")
BIND = os.getenv("GUNICORN_BIND", f"{HOST}:{PORT}")

# Можно вместо TCP использовать unix сокет (при наличии переменной):
#   export GUNICORN_SOCKET=/srv/time_tracking/run/gunicorn.sock
# И тогда systemd unit не указывает --bind
SOCKET_PATH = os.getenv("GUNICORN_SOCKET")

# Кол-во воркеров (по формуле 2 * CPU + 1, но с ограничением)
CPU_COUNT = multiprocessing.cpu_count()
workers = int(os.getenv("GUNICORN_WORKERS", str(min(8, 2 * CPU_COUNT + 1))))

# Тип воркера (sync / gthread / uvicorn.workers.UvicornWorker и т.д.)
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "sync")

# Таймауты
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "30"))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "2"))

# Логи
log_level = os.getenv("GUNICORN_LOG_LEVEL", "info")
accesslog = os.getenv("GUNICORN_ACCESS_LOG", "-")  # "-" = stdout
errorlog = os.getenv("GUNICORN_ERROR_LOG", "-")

# PID файл (опционально)
pidfile = os.getenv("GUNICORN_PIDFILE", "") or None

# Прелоад приложения (экономит память / ускоряет fork, но осторожно с ленивыми ресурсами)
preload_app = os.getenv("GUNICORN_PRELOAD", "True") == "True"

# Максимальное кол-во запросов до перезапуска воркера (для борьбы с утечками памяти)
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "0")) or 0
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "0")) or 0

# Привязка
if SOCKET_PATH:
    bind = f"unix:{SOCKET_PATH}"
else:
    bind = BIND

# Дополнительные хуки (пример: печать перед стартом воркера)

def when_ready(server):  # noqa: D401
    server.log.info("Gunicorn starting: bind=%s workers=%s class=%s", bind, workers, worker_class)


def post_fork(server, worker):  # noqa: D401
    worker.log.info("Worker spawned (pid: %s)", worker.pid)


def worker_int(worker):  # noqa: D401
    worker.log.warning("Worker received INT or QUIT signal")


def worker_abort(worker):  # noqa: D401
    worker.log.warning("Worker aborted (pid: %s)", worker.pid)

