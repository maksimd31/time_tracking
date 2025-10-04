import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from time_tracking_or.models import TimeCounter, TimeInterval, DailySummary
from datetime import time, timedelta, date

@pytest.fixture(autouse=True)
def _email_backend(settings, monkeypatch):
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    # Заглушка Celery задачи
    def _noop(*args, **kwargs):
        return None
    monkeypatch.setattr('accounts.signals.send_welcome_email.delay', _noop, raising=False)
    return settings

@pytest.fixture
def user(db):
    return User.objects.create_user(username='tester', password='pass12345', email='tester@example.com')

@pytest.fixture
def other_user(db):
    return User.objects.create_user(username='other', password='pass12345', email='other@example.com')

@pytest.fixture
def auth_client(client, user):
    client.login(username='tester', password='pass12345')
    return client

@pytest.fixture
def counter(user):
    return TimeCounter.objects.create(user=user, name='Work', color='#ffffff')

@pytest.fixture
def interval(counter, user):
    ti = TimeInterval.objects.create(
        counter=counter,
        user=user,
        day=timezone.localdate(),
        start_time=time(9, 0, 0),
        end_time=time(10, 30, 0),
    )
    return ti

@pytest.fixture
def daily_summary(user):
    return DailySummary.objects.create(user=user, date=timezone.localdate(), interval_count=1, total_time=timedelta(hours=1))

@pytest.fixture
def hx_headers():
    return {"HTTP_HX-Request": "true"}

@pytest.fixture
def mock_vk_requests(monkeypatch):
    class Resp:
        def __init__(self, status=200, data=None):
            self.status_code = status
            self._data = data or {}
            self.text = 'raw'
        def json(self):
            return self._data
    def fake_post(url, data=None, headers=None):
        return Resp(200, {"access_token": "abc123"})
    def fake_get(url, headers=None):
        return Resp(200, {"sub": "999", "name": "VK User"})
    monkeypatch.setattr('accounts.views.requests.post', fake_post)
    monkeypatch.setattr('accounts.views.requests.get', fake_get)
    return True


# Дополнительные fixtures для тестирования системы обратной связи
@pytest.fixture
def project_rating_user(db):
    """Пользователь для тестирования рейтингов проекта."""
    return User.objects.create_user(
        username='ratinguser',
        email='rating@test.com',
        password='testpass123'
    )


@pytest.fixture
def authenticated_rating_client(project_rating_user):
    """Аутентифицированный клиент для тестов рейтингов."""
    from django.test import Client
    client = Client()
    client.force_login(project_rating_user)
    return client


@pytest.fixture
def sample_project_rating(project_rating_user):
    """Образец рейтинга проекта."""
    from time_tracking_or.models import ProjectRating
    return ProjectRating.objects.create(
        user=project_rating_user,
        rating='like',
        comment='Тестовый комментарий',
        email_sent=False
    )


@pytest.fixture
def mock_celery_email_task():
    """Мок для Celery задачи отправки email."""
    from unittest.mock import MagicMock
    mock_task = MagicMock()
    mock_task.id = 'test-celery-task-123'
    mock_task.state = 'SUCCESS'
    return mock_task
