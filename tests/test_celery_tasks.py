"""
Pytest тесты специально для Celery задач.
"""

import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth.models import User
from django.utils import timezone
from celery.exceptions import Retry

from time_tracking_or.tasks import send_feedback_email_task, cleanup_old_feedback_attempts
from time_tracking_or.models import ProjectRating


@pytest.mark.celery
class TestSendFeedbackEmailTask:
    """Тесты для задачи отправки email."""
    
    @pytest.fixture
    def user(self, db):
        """Создает пользователя для тестов."""
        return User.objects.create_user(
            username='celery_test_user',
            email='celery@test.com',
            password='testpass123'
        )
    
    def test_send_feedback_email_success(self, user):
        """Тест успешной отправки email."""
        with patch('time_tracking_or.tasks.send_mail') as mock_send_mail:
            mock_send_mail.return_value = None  # send_mail возвращает None при успехе
            
            result = send_feedback_email_task(user.id, 'Отличный проект!')
            
            assert result['success'] is True
            assert 'успешно отправлено' in result['message']
            assert result['user_id'] == user.id
            
            # Проверяем что send_mail был вызван правильно
            mock_send_mail.assert_called_once()
            call_kwargs = mock_send_mail.call_args[1]
            
            assert 'maksimdis31@icloud.com' in call_kwargs['recipient_list']
            assert user.username in call_kwargs['subject']
            assert 'Отличный проект!' in call_kwargs['message']
            assert user.email in call_kwargs['message']
    
    def test_send_feedback_email_user_not_found(self):
        """Тест с несуществующим пользователем."""
        result = send_feedback_email_task(999999, 'Тест')
        
        assert result['success'] is False
        assert 'Пользователь не найден' in result['message']
        assert result['user_id'] == 999999
    
    def test_send_feedback_email_retry_on_failure(self, user):
        """Тест retry логики при ошибке отправки."""
        with patch('time_tracking_or.tasks.send_mail') as mock_send_mail:
            mock_send_mail.side_effect = Exception('SMTP connection failed')
            
            # Мокируем retry метод
            with patch.object(send_feedback_email_task, 'retry') as mock_retry:
                mock_retry.side_effect = Retry('Retrying...')
                
                with pytest.raises(Retry):
                    send_feedback_email_task(user.id, 'Test retry')
                
                # Проверяем что retry был вызван
                mock_retry.assert_called_once()
                # Проверяем параметры retry
                retry_kwargs = mock_retry.call_args[1]
                assert retry_kwargs['countdown'] == 60  # exponential backoff
                assert retry_kwargs['max_retries'] == 3
    
    def test_send_feedback_email_max_retries_exceeded(self, user):
        """Тест когда превышено максимальное количество попыток."""
        with patch('time_tracking_or.tasks.send_mail') as mock_send_mail:
            mock_send_mail.side_effect = Exception('Persistent SMTP error')
            
            # Имитируем превышение retry лимита
            with patch.object(send_feedback_email_task, 'retry') as mock_retry:
                mock_retry.side_effect = send_feedback_email_task.MaxRetriesExceededError()
                
                result = send_feedback_email_task(user.id, 'Test max retries')
                
                assert result['success'] is False
                assert 'превышено максимальное количество попыток' in result['message']
    
    def test_send_feedback_email_content_formatting(self, user):
        """Тест правильного форматирования содержимого email."""
        with patch('time_tracking_or.tasks.send_mail') as mock_send_mail:
            comment = 'Добавьте функцию экспорта данных!'
            
            send_feedback_email_task(user.id, comment)
            
            call_kwargs = mock_send_mail.call_args[1]
            message = call_kwargs['message']
            
            # Проверяем что все нужные элементы присутствуют
            assert f'Пользователь: {user.username}' in message
            assert f'Email: {user.email}' in message
            assert comment in message
            assert 'Дата:' in message
            assert 'Пожелания:' in message
    
    @pytest.mark.parametrize("comment", [
        'Простой комментарий',
        'Комментарий с эмодзи 🚀💻',
        'Комментарий\nс\nпереносами\nстрок',
        'Комментарий с "кавычками" и \'апострофами\'',
        'Комментарий с <html>тегами</html>',
        'А' * 1000,  # Длинный комментарий
    ])
    def test_send_feedback_email_various_comments(self, user, comment):
        """Тест отправки email с различными типами комментариев."""
        with patch('time_tracking_or.tasks.send_mail') as mock_send_mail:
            result = send_feedback_email_task(user.id, comment)
            
            assert result['success'] is True
            mock_send_mail.assert_called_once()
            
            call_kwargs = mock_send_mail.call_args[1]
            assert comment in call_kwargs['message']


@pytest.mark.celery
class TestCleanupOldFeedbackAttemptsTask:
    """Тесты для задачи очистки старых попыток."""
    
    @pytest.fixture
    def users_and_ratings(self, db):
        """Создает пользователей и рейтинги для тестов."""
        users = []
        ratings = []
        
        for i in range(3):
            user = User.objects.create_user(
                username=f'cleanup_user_{i}',
                email=f'cleanup{i}@test.com',
                password='testpass123'
            )
            users.append(user)
        
        # Создаем старые записи (7+ дней назад)
        old_time = timezone.now() - timezone.timedelta(days=8)
        for i in range(2):
            rating = ProjectRating.objects.create(
                user=users[i],
                rating='like',
                comment=f'Старый комментарий {i}',
                email_sent=False,
                email_sent_at=old_time
            )
            ratings.append(rating)
        
        # Создаем новую запись (менее 7 дней)
        new_time = timezone.now() - timezone.timedelta(days=3)
        rating = ProjectRating.objects.create(
            user=users[2],
            rating='dislike',
            comment='Новый комментарий',
            email_sent=False,
            email_sent_at=new_time
        )
        ratings.append(rating)
        
        # Создаем успешно отправленную запись (не должна удаляться)
        sent_rating = ProjectRating.objects.create(
            user=users[0],
            rating='like',
            comment='Отправленный комментарий',
            email_sent=True,
            email_sent_at=old_time
        )
        ratings.append(sent_rating)
        
        return users, ratings
    
    def test_cleanup_old_feedback_attempts_success(self, users_and_ratings):
        """Тест успешной очистки старых попыток."""
        users, ratings = users_and_ratings
        
        # Проверяем начальное состояние
        assert ProjectRating.objects.count() == 4
        
        # Запускаем очистку
        result = cleanup_old_feedback_attempts()
        
        # Проверяем результат
        assert result['success'] is True
        assert result['deleted_count'] == 2  # Должно удалить 2 старые неотправленные записи
        
        # Проверяем что остались только нужные записи
        remaining_ratings = ProjectRating.objects.all()
        assert remaining_ratings.count() == 2
        
        # Должна остаться новая запись и отправленная запись
        remaining_ids = set(remaining_ratings.values_list('id', flat=True))
        expected_ids = {ratings[2].id, ratings[3].id}  # новая и отправленная
        assert remaining_ids == expected_ids
    
    def test_cleanup_old_feedback_attempts_no_old_records(self, db):
        """Тест очистки когда нет старых записей."""
        # Создаем только новые записи
        user = User.objects.create_user(
            username='new_user',
            email='new@test.com',
            password='testpass123'
        )
        
        ProjectRating.objects.create(
            user=user,
            rating='like',
            comment='Новый комментарий',
            email_sent=False,
            email_sent_at=timezone.now()
        )
        
        result = cleanup_old_feedback_attempts()
        
        assert result['success'] is True
        assert result['deleted_count'] == 0
        assert ProjectRating.objects.count() == 1
    
    def test_cleanup_old_feedback_attempts_empty_db(self, db):
        """Тест очистки пустой базы."""
        result = cleanup_old_feedback_attempts()
        
        assert result['success'] is True
        assert result['deleted_count'] == 0
    
    def test_cleanup_old_feedback_attempts_only_sent_records(self, db):
        """Тест очистки когда есть только отправленные записи."""
        user = User.objects.create_user(
            username='sent_user',
            email='sent@test.com',
            password='testpass123'
        )
        
        # Создаем старую отправленную запись
        old_time = timezone.now() - timezone.timedelta(days=10)
        ProjectRating.objects.create(
            user=user,
            rating='like',
            comment='Старый отправленный комментарий',
            email_sent=True,
            email_sent_at=old_time
        )
        
        result = cleanup_old_feedback_attempts()
        
        assert result['success'] is True
        assert result['deleted_count'] == 0
        assert ProjectRating.objects.count() == 1


@pytest.mark.integration 
@pytest.mark.celery
class TestCeleryTasksIntegration:
    """Интеграционные тесты для Celery задач."""
    
    def test_email_task_and_cleanup_integration(self, db):
        """Тест интеграции между отправкой email и очисткой."""
        # Создаем пользователя
        user = User.objects.create_user(
            username='integration_user',
            email='integration@test.com',
            password='testpass123'
        )
        
        # Создаем рейтинг
        rating = ProjectRating.objects.create(
            user=user,
            rating='like',
            comment='Тестовый комментарий',
            email_sent=False
        )
        
        # Имитируем неудачную отправку email (создаем старую попытку)
        old_time = timezone.now() - timezone.timedelta(days=8)
        rating.email_sent_at = old_time
        rating.save()
        
        # Запускаем очистку
        cleanup_result = cleanup_old_feedback_attempts()
        
        # Запись должна быть удалена
        assert cleanup_result['success'] is True
        assert cleanup_result['deleted_count'] == 1
        assert not ProjectRating.objects.filter(id=rating.id).exists()
    
    @patch('time_tracking_or.tasks.send_mail')
    def test_successful_email_prevents_cleanup(self, mock_send_mail, db):
        """Тест что успешно отправленные email не удаляются при очистке."""
        user = User.objects.create_user(
            username='success_user',
            email='success@test.com', 
            password='testpass123'
        )
        
        # Отправляем email через задачу
        result = send_feedback_email_task(user.id, 'Успешный комментарий')
        assert result['success'] is True
        
        # Создаем рейтинг как будто он был создан после отправки
        old_time = timezone.now() - timezone.timedelta(days=8)
        rating = ProjectRating.objects.create(
            user=user,
            rating='like',
            comment='Успешный комментарий',
            email_sent=True,  # Отмечаем как отправленный
            email_sent_at=old_time
        )
        
        # Запускаем очистку
        cleanup_result = cleanup_old_feedback_attempts()
        
        # Отправленная запись не должна быть удалена
        assert ProjectRating.objects.filter(id=rating.id).exists()


@pytest.mark.slow
@pytest.mark.celery
class TestCeleryTasksPerformance:
    """Тесты производительности Celery задач."""
    
    def test_cleanup_large_dataset(self, db):
        """Тест очистки большого количества записей."""
        # Создаем много пользователей и записей
        users = []
        for i in range(50):
            user = User.objects.create_user(
                username=f'perf_user_{i}',
                email=f'perf{i}@test.com',
                password='testpass123'
            )
            users.append(user)
        
        # Создаем старые записи
        old_time = timezone.now() - timezone.timedelta(days=8)
        for user in users:
            ProjectRating.objects.create(
                user=user,
                rating='like',
                comment=f'Комментарий от {user.username}',
                email_sent=False,
                email_sent_at=old_time
            )
        
        import time
        start_time = time.time()
        
        result = cleanup_old_feedback_attempts()
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Проверяем что очистка прошла быстро (менее 5 секунд для 50 записей)
        assert execution_time < 5.0
        assert result['success'] is True
        assert result['deleted_count'] == 50