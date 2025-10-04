"""Celery tasks for project feedback and email notifications."""

import ssl
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User

# Обход SSL проблемы на macOS для development
if settings.DEBUG:
    ssl._create_default_https_context = ssl._create_unverified_context


@shared_task(bind=True, max_retries=3)
def send_feedback_email_task(self, user_id, comment):
    """
    Send user feedback email to developer.
    
    Args:
        user_id (int): ID of the user sending feedback
        comment (str): User's feedback text
    
    Returns:
        dict: Result with success status and message
    """
    try:
        # Получаем пользователя
        user = User.objects.get(id=user_id)
        
        # Формируем письмо
        subject = f'Пожелания по проекту Time Tracking от {user.username}'
        
        message = f"""
Новые пожелания по развитию проекта Time Tracking!

От пользователя: {user.username} ({user.email if user.email else 'email не указан'})
Дата регистрации: {user.date_joined.strftime('%d.%m.%Y %H:%M')}
Дата отправки: {timezone.now().strftime('%d.%m.%Y %H:%M')}

Пожелания:
{comment}

---
Это автоматическое сообщение от системы Time Tracking.
Отправлено через Celery task в фоновом режиме.
        """
        
        # Отправляем email
        from django.core.mail import send_mail
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=['maksimdis31@icloud.com'],
            fail_silently=False,
        )
        
        return {
            'success': True,
            'message': f'Email успешно отправлен для пользователя {user.username}',
            'user_id': user_id
        }
        
    except User.DoesNotExist:
        error_msg = f'Пользователь с ID {user_id} не найден'
        return {
            'success': False,
            'message': error_msg,
            'user_id': user_id
        }
        
    except Exception as exc:
        # Повторяем задачу при ошибке
        if self.request.retries < self.max_retries:
            # Экспоненциальная задержка: 60s, 120s, 240s
            countdown = 60 * (2 ** self.request.retries)
            raise self.retry(exc=exc, countdown=countdown)
        
        # Если все попытки неудачны
        error_msg = f'Ошибка отправки email после {self.max_retries} попыток: {str(exc)}'
        return {
            'success': False,
            'message': error_msg,
            'user_id': user_id
        }


@shared_task
def cleanup_old_feedback_attempts():
    """
    Cleanup task to remove old failed email attempts.
    Can be run periodically to clean up the database.
    """
    from .models import ProjectRating
    from datetime import timedelta
    
    # Удаляем записи старше 30 дней без отправленного email
    cutoff_date = timezone.now() - timedelta(days=30)
    
    old_ratings = ProjectRating.objects.filter(
        email_sent=False,
        created_at__lt=cutoff_date
    )
    
    count = old_ratings.count()
    old_ratings.update(comment='', email_sent=True)  # Помечаем как обработанные
    
    return {
        'success': True,
        'message': f'Очищено {count} старых записей обратной связи'
    }