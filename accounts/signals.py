# from django.core.mail import send_mail
# from django.db.models.signals import post_save
# from django.contrib.auth.models import User
# from django.dispatch import receiver
# from Time_tracking import settings
# from .models import Profile
#
#
# @receiver(post_save, sender=User)
# def create_profile(sender, instance, created, **kwargs):
#     if created:
#         Profile.objects.create(user=instance)
#
#
# @receiver(post_save, sender=User)
# def user_postsave(sender, instance, created, **kwargs):
#     if created:
#         subject = instance.first_name
#         message = f'Добро пожаловать {instance.username}'
#         from_email = settings.EMAIL_HOST_USER
#         to_email = instance.email
#         send_mail(
#             subject,
#             message,
#             from_email,
#             [to_email],
#             fail_silently=False
#         )
#
# @receiver(post_save, sender=User)
# def create_user_profile(sender, instance, created, **kwargs):
#     if created:
#         Profile.objects.create(user=instance)

from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from Time_tracking import settings
from services.utils import unique_slugify
from .models import Profile
from django.utils.text import slugify

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # Создание профиля
        # profile = Profile.objects.create(user=instance)
        profile = Profile.objects.create(user=instance)

        # # Генерация уникального slug
        profile.slug = unique_slugify(profile, instance.username, 'slug')  # Укажите имя поля 'slug'
        profile.save()

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