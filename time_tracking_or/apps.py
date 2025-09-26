"""Application configuration for the time tracking domain app."""

from django.apps import AppConfig


class TimeTrackingOrConfig(AppConfig):
    """Load time-tracking app defaults."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'time_tracking_or'
