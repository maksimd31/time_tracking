"""
Pytest тесты для URL patterns и View responses.
"""

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse, resolve
from unittest.mock import patch

from time_tracking_or.views import ProjectRatingView, SendFeedbackView
from time_tracking_or.models import ProjectRating


class TestURLPatterns:
    """Тесты URL маршрутов."""
    
    def test_project_rating_url_resolves(self):
        """Тест что URL project_rating правильно разрешается."""
        url = reverse('project_rating')
        resolver = resolve(url)
        assert resolver.func.view_class == ProjectRatingView
    
    def test_send_feedback_url_resolves(self):
        """Тест что URL send_feedback правильно разрешается."""
        url = reverse('send_feedback')
        resolver = resolve(url)
        assert resolver.func.view_class == SendFeedbackView
    
    def test_project_rating_url_path(self):
        """Тест правильности пути для project_rating."""
        url = reverse('project_rating')
        assert url == '/project/rating/'
    
    def test_send_feedback_url_path(self):
        """Тест правильности пути для send_feedback."""
        url = reverse('send_feedback')
        assert url == '/project/feedback/'


class TestProjectRatingViewDetailed:
    """Детальные тесты для ProjectRatingView."""
    
    @pytest.fixture
    def user(self, db):
        return User.objects.create_user(
            username='rating_user',
            email='rating@test.com',
            password='testpass123'
        )
    
    @pytest.fixture
    def client_logged_in(self, user):
        client = Client()
        client.force_login(user)
        return client
    
    def test_project_rating_context_data(self, client_logged_in, user):
        """Тест данных контекста в ответе."""
        url = reverse('project_rating')
        response = client_logged_in.post(url, {
            'rating': 'like',
            'comment': 'Отличный проект!'
        })
        
        assert response.status_code == 200
        # Проверяем что в контексте есть нужные данные
        assert 'stats' in response.context
        
    def test_project_rating_statistics_calculation(self, client_logged_in, user, db):
        """Тест правильности расчета статистики."""
        # Создаем дополнительных пользователей и рейтинги
        user2 = User.objects.create_user('user2', 'user2@test.com', 'pass')
        user3 = User.objects.create_user('user3', 'user3@test.com', 'pass')
        
        ProjectRating.objects.create(user=user2, rating='like', comment='Нравится')
        ProjectRating.objects.create(user=user3, rating='dislike', comment='Не нравится')
        
        url = reverse('project_rating')
        response = client_logged_in.post(url, {
            'rating': 'like',
            'comment': 'Мой отзыв'
        })
        
        stats = response.context['stats']
        assert stats['total_ratings'] == 3
        assert stats['like_count'] == 2
        assert stats['dislike_count'] == 1
        assert stats['like_percentage'] == 67  # 2/3 * 100 округленно
    
    def test_project_rating_update_existing_rating(self, client_logged_in, user):
        """Тест обновления существующего рейтинга."""
        # Создаем первоначальный рейтинг
        ProjectRating.objects.create(
            user=user,
            rating='like',
            comment='Первый комментарий'
        )
        
        url = reverse('project_rating')
        response = client_logged_in.post(url, {
            'rating': 'dislike',
            'comment': 'Изменил мнение'
        })
        
        assert response.status_code == 200
        
        # Проверяем что рейтинг обновился
        rating = ProjectRating.objects.get(user=user)
        assert rating.rating == 'dislike'
        assert rating.comment == 'Изменил мнение'
        
        # Проверяем что создалась только одна запись
        assert ProjectRating.objects.filter(user=user).count() == 1
    
    def test_project_rating_htmx_vs_regular_request(self, client_logged_in):
        """Тест различия между HTMX и обычными запросами."""
        url = reverse('project_rating')
        
        # Обычный запрос
        response_regular = client_logged_in.post(url, {
            'rating': 'like',
            'comment': 'Обычный запрос'
        })
        
        # HTMX запрос
        response_htmx = client_logged_in.post(
            url, 
            {'rating': 'dislike', 'comment': 'HTMX запрос'},
            HTTP_HX_REQUEST='true'
        )
        
        # Оба должны быть успешными
        assert response_regular.status_code == 200
        assert response_htmx.status_code == 200
        
        # HTMX должен вернуть фрагмент, обычный - полную страницу
        # (в нашем случае оба возвращают один шаблон, но логика может отличаться)
    
    @pytest.mark.parametrize("rating_value,expected_status", [
        ('like', 200),
        ('dislike', 200),
        ('invalid', 400),
        ('', 400),
        (None, 400),
    ])
    def test_project_rating_validation(self, client_logged_in, rating_value, expected_status):
        """Тест валидации различных значений рейтинга."""
        url = reverse('project_rating')
        data = {'comment': 'Тестовый комментарий'}
        
        if rating_value is not None:
            data['rating'] = rating_value
            
        response = client_logged_in.post(url, data)
        assert response.status_code == expected_status


class TestSendFeedbackViewDetailed:
    """Детальные тесты для SendFeedbackView."""
    
    @pytest.fixture
    def user(self, db):
        return User.objects.create_user(
            username='feedback_user',
            email='feedback@test.com',
            password='testpass123'
        )
    
    @pytest.fixture
    def client_logged_in(self, user):
        client = Client()
        client.force_login(user)
        return client
    
    def test_send_feedback_empty_comment_variations(self, client_logged_in):
        """Тест различных вариантов пустых комментариев."""
        url = reverse('send_feedback')
        
        empty_variations = ['', '   ', '\n\n', '\t\t', None]
        
        for empty_value in empty_variations:
            data = {}
            if empty_value is not None:
                data['comment'] = empty_value
                
            response = client_logged_in.post(url, data)
            assert response.status_code == 400
    
    @patch('time_tracking_or.tasks.send_feedback_email_task.delay')
    def test_send_feedback_creates_or_updates_rating(self, mock_delay, client_logged_in, user):
        """Тест создания или обновления рейтинга при отправке отзыва."""
        mock_task = type('MockTask', (), {'id': 'test-task-123'})()
        mock_delay.return_value = mock_task
        
        url = reverse('send_feedback')
        
        # Первый отзыв - должен создать новый рейтинг
        response = client_logged_in.post(url, {
            'comment': 'Первый отзыв'
        })
        assert response.status_code == 200
        
        rating = ProjectRating.objects.get(user=user)
        assert rating.comment == 'Первый отзыв'
        assert rating.rating == 'like'  # По умолчанию
        assert rating.email_sent
        
        # Второй отзыв - должен обновить существующий
        response = client_logged_in.post(url, {
            'comment': 'Обновленный отзыв'
        })
        assert response.status_code == 200
        
        rating.refresh_from_db()
        assert rating.comment == 'Обновленный отзыв'
        
        # Должна быть только одна запись
        assert ProjectRating.objects.filter(user=user).count() == 1
    
    @patch('time_tracking_or.tasks.send_feedback_email_task.delay')
    def test_send_feedback_response_format(self, mock_delay, client_logged_in):
        """Тест формата ответа."""
        mock_task = type('MockTask', (), {'id': 'response-test-456'})()
        mock_delay.return_value = mock_task
        
        url = reverse('send_feedback')
        
        # HTMX запрос
        response = client_logged_in.post(
            url,
            {'comment': 'Тестовый отзыв'},
            HTTP_HX_REQUEST='true'
        )
        
        assert response.status_code == 200
        assert 'feedback_status.html' in [t.name for t in response.templates]
        
        # Обычный запрос (должен редиректить)
        response = client_logged_in.post(url, {'comment': 'Обычный отзыв'})
        assert response.status_code == 302  # Redirect
    
    @patch('time_tracking_or.tasks.send_feedback_email_task.delay')
    def test_send_feedback_celery_task_parameters(self, mock_delay, client_logged_in, user):
        """Тест правильности параметров передаваемых в Celery задачу."""
        mock_task = type('MockTask', (), {'id': 'params-test-789'})()
        mock_delay.return_value = mock_task
        
        url = reverse('send_feedback')
        comment = 'Детальный отзыв с параметрами'
        
        client_logged_in.post(url, {'comment': comment})
        
        # Проверяем что задача была вызвана с правильными параметрами
        mock_delay.assert_called_once_with(user.id, comment)
    
    @patch('time_tracking_or.tasks.send_feedback_email_task.delay')
    def test_send_feedback_task_id_saved(self, mock_delay, client_logged_in, user):
        """Тест сохранения ID задачи в базе данных."""
        task_id = 'saved-task-id-999'
        mock_task = type('MockTask', (), {'id': task_id})()
        mock_delay.return_value = mock_task
        
        url = reverse('send_feedback')
        client_logged_in.post(url, {'comment': 'Отзыв с сохранением ID'})
        
        rating = ProjectRating.objects.get(user=user)
        assert rating.celery_task_id == task_id


class TestViewPermissions:
    """Тесты прав доступа к views."""
    
    def test_anonymous_user_redirected_to_login(self):
        """Тест перенаправления анонимного пользователя на логин."""
        client = Client()
        
        # Тестируем project_rating
        rating_url = reverse('project_rating')
        response = client.post(rating_url, {'rating': 'like'})
        assert response.status_code == 302
        assert '/login/' in response.url or '/accounts/login/' in response.url
        
        # Тестируем send_feedback
        feedback_url = reverse('send_feedback')
        response = client.post(feedback_url, {'comment': 'Отзыв'})
        assert response.status_code == 302
        assert '/login/' in response.url or '/accounts/login/' in response.url
    
    def test_authenticated_user_access(self, db):
        """Тест доступа аутентифицированного пользователя."""
        user = User.objects.create_user('auth_user', 'auth@test.com', 'pass')
        client = Client()
        client.force_login(user)
        
        # project_rating должен быть доступен
        rating_url = reverse('project_rating')
        response = client.post(rating_url, {
            'rating': 'like',
            'comment': 'Тест доступа'
        })
        assert response.status_code == 200
        
        # send_feedback должен быть доступен
        with patch('time_tracking_or.tasks.send_feedback_email_task.delay') as mock_delay:
            mock_delay.return_value = type('MockTask', (), {'id': 'access-test'})()
            
            feedback_url = reverse('send_feedback')
            response = client.post(feedback_url, {'comment': 'Тест доступа к отзывам'})
            assert response.status_code == 200


class TestViewsErrorHandling:
    """Тесты обработки ошибок в views."""
    
    @pytest.fixture
    def user(self, db):
        return User.objects.create_user('error_user', 'error@test.com', 'pass')
    
    @pytest.fixture
    def client_logged_in(self, user):
        client = Client()
        client.force_login(user)
        return client
    
    @patch('time_tracking_or.tasks.send_feedback_email_task.delay')
    def test_send_feedback_celery_task_error(self, mock_delay, client_logged_in):
        """Тест обработки ошибки при запуске Celery задачи."""
        mock_delay.side_effect = Exception('Celery connection failed')
        
        url = reverse('send_feedback')
        response = client_logged_in.post(url, {'comment': 'Отзыв с ошибкой'})
        
        # Должен вернуть ошибку 500
        assert response.status_code == 500
    
    def test_project_rating_database_error(self, client_logged_in):
        """Тест обработки ошибки базы данных."""
        url = reverse('project_rating')
        
        # Имитируем ошибку БД через патчинг
        with patch('time_tracking_or.models.ProjectRating.objects.get_or_create') as mock_get_or_create:
            mock_get_or_create.side_effect = Exception('Database connection lost')
            
            response = client_logged_in.post(url, {
                'rating': 'like',
                'comment': 'Тест ошибки БД'
            })
            
            assert response.status_code == 500
    
    def test_project_rating_invalid_post_data(self, client_logged_in):
        """Тест обработки некорректных POST данных."""
        url = reverse('project_rating')
        
        # Отправляем данные неправильного типа
        invalid_data_sets = [
            {'rating': ['like']},  # список вместо строки
            {'rating': {'invalid': 'dict'}},  # словарь
            {'comment': 123},  # число вместо строки
        ]
        
        for invalid_data in invalid_data_sets:
            response = client_logged_in.post(url, invalid_data)
            # Должен обрабатывать ошибки корректно (либо 400, либо 500)
            assert response.status_code in [400, 500]