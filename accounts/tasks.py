from django.conf import settings
from django.core.mail import send_mail
from celery import shared_task


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_welcome_email(self, subject, message, to_email):
    if not to_email:
        return
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [to_email],
        fail_silently=False,
    )
