from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

class UserLoginRememberMeTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='testuser', password='testpass123')
        self.login_url = reverse('login')

    def test_login_without_remember_me(self):
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'testpass123',
            # 'remember_me' не передаём
        })
        self.assertEqual(response.status_code, 302)  # редирект после логина
        session_expiry = self.client.session.get_expiry_age()
        self.assertLessEqual(session_expiry, 60 * 60 * 24)  # сессия не более суток (обычно 0 — до закрытия браузера)

    def test_login_with_remember_me(self):
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'testpass123',
            'remember_me': 'on',
        })
        self.assertEqual(response.status_code, 302)
        session_expiry = self.client.session.get_expiry_age()
        self.assertGreaterEqual(session_expiry, 60 * 60 * 24 * 13)  # сессия примерно 2 недели


class UserRegistrationAutoLoginTest(TestCase):
    def test_user_is_logged_in_after_registration(self):
        register_url = reverse('register')
        response = self.client.post(register_url, {
            'username': 'newuser',
            'password1': 'securepass12345',
            'password2': 'securepass12345',
            'email': 'newuser@example.com'
        })
        self.assertEqual(response.status_code, 302)
        # после регистрации пользователь должен быть аутентифицирован
        user = get_user_model().objects.get(username='newuser')
        self.assertTrue('_auth_user_id' in self.client.session)
        self.assertEqual(int(self.client.session['_auth_user_id']), user.id)
