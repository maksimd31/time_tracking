"""Application configuration for the accounts app."""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Wire up account signals when the app boots."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        """Import signal handlers to register them with Django."""
        import accounts.signals
