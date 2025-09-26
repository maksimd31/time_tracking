"""Expose the Celery application instance for Django to autodiscover."""

from Time_tracking.celery import app as celery_app

__all__ = ('celery_app',)
