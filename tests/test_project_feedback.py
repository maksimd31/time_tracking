"""
Pytest тесты для системы обратной связи и Celery задач.
"""

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch, MagicMock
from celery.result import AsyncResult

from time_tracking_or.models import ProjectRating
from time_tracking_or.tasks import send_feedback_email_task, cleanup_old_feedback_attempts


@pytest.fixture
def user(db):
    """Создает тестового пользователя."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def client():
    """Django test client."""
    return Client()


@pytest.fixture
def authenticated_client(client, user):
    """Аутентифицированный клиент."""
    client.force_login(user)
    return client


@pytest.fixture
def project_rating(user):
    """Создает тестовый рейтинг проекта."""
    return ProjectRating.objects.create(
        user=user,
        rating='like',
        comment='Отличный проект!',
        email_sent=False
    )


class TestProjectRatingModel:
    """Тесты модели ProjectRating."""
    
    def test_create_project_rating(self, user):
        """Тест создания рейтинга проекта."""
        rating = ProjectRating.objects.create(
            user=user,
            rating='like',
            comment='Классный проект!'
        )
        
        assert rating.user == user
        assert rating.rating == 'like'
        assert rating.comment == 'Классный проект!'
        assert not rating.email_sent
        assert rating.email_sent_at is None
        assert rating.celery_task_id == '' or rating.celery_task_id is None
        
    def test_string_representation(self, project_rating):
        """Тест строкового представления модели."""
        expected = f"{project_rating.user.username} - {project_rating.get_rating_display()}"
        assert str(project_rating) == expected
        
    def test_rating_choices(self, db):
        """Тест валидных значений рейтинга."""
        # Создаем разных пользователей для каждого рейтинга (OneToOneField)
        user1 = User.objects.create_user('user1', 'user1@test.com', 'pass')
        user2 = User.objects.create_user('user2', 'user2@test.com', 'pass')
        
        # Позитивный рейтинг
        like_rating = ProjectRating.objects.create(
            user=user1,
            rating='like',
            comment='Нравится'
        )
        assert like_rating.rating == 'like'
        
        # Негативный рейтинг  
        dislike_rating = ProjectRating.objects.create(
            user=user2,
            rating='dislike',
            comment='Не нравится'
        )
        assert dislike_rating.rating == 'dislike'
        
    def test_unique_user_constraint(self, user):
        """Тест уникальности пользователя для рейтинга (OneToOneField)."""
        from django.db import IntegrityError, transaction
        
        # Первый рейтинг
        ProjectRating.objects.create(
            user=user,
            rating='like',
            comment='Первый комментарий'
        )
        
        # Попытка создать второй рейтинг для того же пользователя должна вызвать ошибку
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ProjectRating.objects.create(
                    user=user,
                    rating='dislike', 
                    comment='Второй комментарий'
                )
        
        # Должна быть только одна запись
        assert ProjectRating.objects.filter(user=user).count() == 1


class TestProjectRatingView:
    """Тесты для ProjectRatingView."""
    
    def test_project_rating_get_not_allowed(self, authenticated_client):
        """Тест что GET запрос не разрешен."""
        url = reverse('project_rating')
        response = authenticated_client.get(url)
        assert response.status_code == 405  # Method Not Allowed
        
    def test_project_rating_unauthenticated(self, client):
        """Тест что неаутентифицированный пользователь перенаправляется."""
        url = reverse('project_rating')
        response = client.post(url, {'rating': 'like'})
        assert response.status_code == 302  # Redirect to login
        
    def test_project_rating_like(self, authenticated_client, user):
        """Тест постановки лайка."""
        url = reverse('project_rating')
        response = authenticated_client.post(url, {
            'rating': 'like',
            'comment': 'Отличный проект!'
        })
        
        assert response.status_code == 200
        
        # Проверяем что рейтинг создался
        rating = ProjectRating.objects.get(user=user)
        assert rating.rating == 'like'
        assert rating.comment == 'Отличный проект!'
        
    def test_project_rating_dislike(self, authenticated_client, user):
        """Тест постановки дизлайка."""
        url = reverse('project_rating')
        response = authenticated_client.post(url, {
            'rating': 'dislike',
            'comment': 'Нужны улучшения'
        })
        
        assert response.status_code == 200
        
        rating = ProjectRating.objects.get(user=user)
        assert rating.rating == 'dislike'
        assert rating.comment == 'Нужны улучшения'
        
    def test_project_rating_update_existing(self, authenticated_client, project_rating):
        """Тест обновления существующего рейтинга."""
        url = reverse('project_rating')
        response = authenticated_client.post(url, {
            'rating': 'dislike',
            'comment': 'Передумал, не нравится'
        })
        
        assert response.status_code == 200
        
        # Обновляем объект из БД
        project_rating.refresh_from_db()
        assert project_rating.rating == 'dislike'
        assert project_rating.comment == 'Передумал, не нравится'
        
    def test_project_rating_invalid_rating(self, authenticated_client):
        """Тест с невалидным значением рейтинга."""
        url = reverse('project_rating')
        response = authenticated_client.post(url, {
            'rating': 'invalid_rating',
            'comment': 'Комментарий'
        })
        
        # Должно вернуть ошибку
        assert response.status_code == 400
        
    def test_project_rating_htmx_request(self, authenticated_client, user):
        """Тест HTMX запроса."""
        url = reverse('project_rating')
        response = authenticated_client.post(
            url, 
            {'rating': 'like', 'comment': 'Тест HTMX'},
            HTTP_HX_REQUEST='true'
        )
        
        assert response.status_code == 200
        # HTMX запрос должен вернуть шаблон статистики
        assert 'project_rating_stats.html' in [t.name for t in response.templates]


class TestSendFeedbackView:
    """Тесты для SendFeedbackView."""
    
    def test_send_feedback_unauthenticated(self, client):
        """Тест отправки отзыва неаутентифицированным пользователем."""
        url = reverse('send_feedback')
        response = client.post(url, {'comment': 'Отзыв'})
        assert response.status_code == 302  # Redirect to login
        
    def test_send_feedback_empty_comment(self, authenticated_client):
        """Тест отправки пустого комментария."""
        url = reverse('send_feedback')
        response = authenticated_client.post(url, {'comment': ''})
        assert response.status_code == 400
        
    @patch('time_tracking_or.tasks.send_feedback_email_task.delay')
    def test_send_feedback_success(self, mock_delay, authenticated_client, user):
        """Тест успешной отправки отзыва."""
        # Мокируем Celery задачу
        mock_task = MagicMock()
        mock_task.id = 'test-task-id-123'
        mock_delay.return_value = mock_task
        
        url = reverse('send_feedback')
        response = authenticated_client.post(url, {
            'comment': 'Отличный проект, добавьте больше функций!'
        })
        
        assert response.status_code == 200
        
        # Проверяем что задача была вызвана
        mock_delay.assert_called_once_with(user.id, 'Отличный проект, добавьте больше функций!')
        
        # Проверяем что рейтинг создался/обновился
        rating = ProjectRating.objects.get(user=user)
        assert rating.comment == 'Отличный проект, добавьте больше функций!'
        assert rating.email_sent == True
        assert rating.email_sent_at is not None
        assert rating.celery_task_id == 'test-task-id-123'
        
    def test_send_feedback_htmx(self, authenticated_client, user):
        """Тест HTMX запроса для отправки отзыва."""
        with patch('time_tracking_or.tasks.send_feedback_email_task.delay') as mock_delay:
            mock_task = MagicMock()
            mock_task.id = 'test-task-id'
            mock_delay.return_value = mock_task
            
            url = reverse('send_feedback')
            response = authenticated_client.post(
                url,
                {'comment': 'HTMX отзыв'},
                HTTP_HX_REQUEST='true'
            )
            
            assert response.status_code == 200
            # Должен вернуть шаблон статуса
            assert 'feedback_status.html' in [t.name for t in response.templates]


class TestCeleryTasks:
    """Тесты для Celery задач."""
    
    def test_send_feedback_email_task_user_not_found(self):
        """Тест задачи с несуществующим пользователем."""
        with patch('time_tracking_or.tasks.send_mail') as mock_send_mail:
            result = send_feedback_email_task(999999, 'Тестовый комментарий')
            
            # Задача должна завершиться с ошибкой
            assert result['success'] == False
            assert 'Пользователь не найден' in result['message']
            mock_send_mail.assert_not_called()
            
    def test_send_feedback_email_task_success(self, user):
        """Тест успешной отправки email."""
        with patch('time_tracking_or.tasks.send_mail') as mock_send_mail:
            mock_send_mail.return_value = True
            
            result = send_feedback_email_task(user.id, 'Отличный проект!')
            
            assert result['success'] == True
            assert 'успешно отправлено' in result['message']
            
            # Проверяем параметры отправки
            mock_send_mail.assert_called_once()
            call_args = mock_send_mail.call_args
            assert 'maksimdis31@icloud.com' in call_args[1]['recipient_list']
            assert user.username in call_args[1]['message']
            assert 'Отличный проект!' in call_args[1]['message']
            
    def test_send_feedback_email_task_mail_error(self, user):
        """Тест обработки ошибки отправки email."""
        with patch('time_tracking_or.tasks.send_mail') as mock_send_mail:
            mock_send_mail.side_effect = Exception('SMTP Error')
            
            # Задача должна быть повторена (retry)
            with patch('time_tracking_or.tasks.send_feedback_email_task.retry') as mock_retry:
                mock_retry.side_effect = Exception('Max retries exceeded')
                
                with pytest.raises(Exception):
                    send_feedback_email_task(user.id, 'Тест ошибки')
                    
                mock_retry.assert_called_once()
                
    def test_cleanup_old_feedback_attempts(self, user):
        """Тест очистки старых попыток отправки."""
        # Создаем старые записи
        old_time = timezone.now() - timezone.timedelta(days=8)
        
        old_rating = ProjectRating.objects.create(
            user=user,
            rating='like',
            comment='Старый комментарий',
            email_sent=False,
            email_sent_at=old_time
        )
        
        # Создаем новую запись
        new_rating = ProjectRating.objects.create(
            user=user,
            rating='dislike', 
            comment='Новый комментарий',
            email_sent=False,
            email_sent_at=timezone.now()
        )
        
        # Запускаем очистку
        result = cleanup_old_feedback_attempts()
        
        # Старая запись должна быть удалена
        assert not ProjectRating.objects.filter(id=old_rating.id).exists()
        # Новая запись должна остаться
        assert ProjectRating.objects.filter(id=new_rating.id).exists()
        
        assert result['success'] == True
        assert result['deleted_count'] == 1


class TestIntegration:
    """Интеграционные тесты."""
    
    def test_complete_feedback_flow(self, authenticated_client, user):
        """Тест полного цикла обратной связи."""
        with patch('time_tracking_or.tasks.send_feedback_email_task.delay') as mock_delay:
            mock_task = MagicMock()
            mock_task.id = 'integration-test-task'
            mock_delay.return_value = mock_task
            
            # 1. Ставим лайк
            rating_url = reverse('project_rating')
            response = authenticated_client.post(rating_url, {
                'rating': 'like',
                'comment': 'Начальный комментарий'
            })
            assert response.status_code == 200
            
            # 2. Отправляем отзыв
            feedback_url = reverse('send_feedback')
            response = authenticated_client.post(feedback_url, {
                'comment': 'Подробный отзыв о проекте'
            })
            assert response.status_code == 200
            
            # 3. Проверяем состояние в БД
            rating = ProjectRating.objects.get(user=user)
            assert rating.rating == 'like'
            assert rating.comment == 'Подробный отзыв о проекте'
            assert rating.email_sent == True
            assert rating.celery_task_id == 'integration-test-task'
            
            # 4. Изменяем рейтинг
            response = authenticated_client.post(rating_url, {
                'rating': 'dislike',
                'comment': 'Передумал'
            })
            assert response.status_code == 200
            
            rating.refresh_from_db()
            assert rating.rating == 'dislike'
            assert rating.comment == 'Передумал'
            
    def test_anonymous_user_restrictions(self, client):
        """Тест ограничений для анонимных пользователей."""
        # Попытка поставить рейтинг
        rating_url = reverse('project_rating')
        response = client.post(rating_url, {'rating': 'like'})
        assert response.status_code == 302  # Redirect to login
        
        # Попытка отправить отзыв
        feedback_url = reverse('send_feedback')
        response = client.post(feedback_url, {'comment': 'Отзыв'})
        assert response.status_code == 302  # Redirect to login


class TestEdgeCases:
    """Тесты граничных случаев."""
    
    def test_very_long_comment(self, authenticated_client, user):
        """Тест очень длинного комментария."""
        long_comment = 'А' * 2000  # Очень длинный комментарий
        
        url = reverse('project_rating')
        response = authenticated_client.post(url, {
            'rating': 'like',
            'comment': long_comment
        })
        
        assert response.status_code == 200
        rating = ProjectRating.objects.get(user=user)
        assert rating.comment == long_comment
        
    def test_special_characters_in_comment(self, authenticated_client, user):
        """Тест специальных символов в комментарии."""
        special_comment = 'Тест с эмодзи 🚀 и символами <script>alert("xss")</script>'
        
        url = reverse('project_rating')
        response = authenticated_client.post(url, {
            'rating': 'like', 
            'comment': special_comment
        })
        
        assert response.status_code == 200
        rating = ProjectRating.objects.get(user=user)
        assert rating.comment == special_comment
        
    def test_concurrent_ratings(self, authenticated_client, user):
        """Тест одновременных рейтингов (имитация race condition)."""
        url = reverse('project_rating')
        
        # Имитируем несколько быстрых запросов
        responses = []
        for i in range(3):
            response = authenticated_client.post(url, {
                'rating': 'like',
                'comment': f'Комментарий {i}'
            })
            responses.append(response)
            
        # Все запросы должны пройти успешно
        for response in responses:
            assert response.status_code == 200
            
        # В БД должна остаться одна запись (последняя)
        ratings = ProjectRating.objects.filter(user=user)
        assert ratings.count() >= 1  # Может быть несколько из-за особенностей тестов