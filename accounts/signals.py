"""Signal handlers for provisioning profiles and sending welcome emails."""

from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from services.utils import unique_slugify
from .models import Profile
from .tasks import send_welcome_email

GUEST_PREFIX = "guest_"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):  # noqa: D401
    """Create a profile and queue welcome email for real (non-guest) users.

    Guest users are auto-created by middleware (see GuestIPAuthenticationMiddleware)
    and must NOT receive profiles or welcome emails. We identify them by:
      1. Username prefix 'guest_'; OR
      2. Unusable password (middleware sets unusable password for guests).
    """
    if not created:
        return

    # Skip guest accounts
    if instance.username.startswith(GUEST_PREFIX) or not instance.has_usable_password():
        return

    # Создание профиля
    profile = Profile.objects.create(user=instance)

    # Генерация уникального slug
    profile.slug = unique_slugify(profile, instance.username, profile.slug)
    profile.save(update_fields=['slug'])

    # Отправка приветственного сообщения (если email указан)
    to_email = instance.email
    if to_email:
        subject = instance.first_name or 'Добро пожаловать'
        message = f'Добро пожаловать {instance.username}'
        send_welcome_email.delay(subject, message, to_email)
