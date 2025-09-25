import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Time_tracking.settings')

app = Celery('Time_tracking')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()
