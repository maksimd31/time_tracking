from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from services.utils import unique_slugify
from .models import Profile
from .tasks import send_welcome_email

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:

        # Создание профиля
        # profile = Profile.objects.create(user=instance)
        profile = Profile.objects.create(user=instance)

        # # Генерация уникального slug
        profile.slug = unique_slugify(profile, instance.username, profile.slug)
        profile.save(update_fields=['slug'])

        # Отправка приветственного сообщения
        subject = instance.first_name or 'Добро пожаловать'
        message = f'Добро пожаловать {instance.username}'
        to_email = instance.email
        if to_email:
            send_welcome_email.delay(subject, message, to_email)
