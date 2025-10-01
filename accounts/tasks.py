"""Celery tasks triggered by account lifecycle events."""

from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from time_tracking_or.models import TimeCounter


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_welcome_email(self, subject, message, to_email):
    """Send a welcome email, retrying on transient errors."""
    if not to_email:
        return
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [to_email],
        fail_silently=False,
    )


@shared_task
def cleanup_stale_guests():
    """Delete guest accounts without активных данных по истечении срока хранения."""
    retention_days = getattr(settings, "GUEST_ACCOUNT_RETENTION_DAYS", 14)
    cutoff = timezone.now() - timedelta(days=retention_days)

    user_model = get_user_model()
    counters_subquery = TimeCounter.objects.filter(user=OuterRef("pk"))

    stale_users = (
        user_model.objects.filter(username__startswith="guest_")
        .filter(date_joined__lt=cutoff)
        .filter(Q(last_login__lt=cutoff) | Q(last_login__isnull=True))
        .annotate(has_counters=Exists(counters_subquery))
        .filter(has_counters=False)
    )

    if not stale_users.exists():
        return 0

    deleted_count = stale_users.count()
    stale_users.delete()
    return deleted_count
