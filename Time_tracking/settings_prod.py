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