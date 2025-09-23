from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from Time_tracking import settings
from services.utils import unique_slugify
from .models import Profile

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
        subject = instance.first_name
        message = f'Добро пожаловать {instance.username}'
        from_email = settings.EMAIL_HOST_USER
        to_email = instance.email
        send_mail(
            subject,
            message,
            from_email,
            [to_email],
            fail_silently=False
        )
