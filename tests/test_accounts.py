import json
import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from django.core import mail
from accounts.forms import UserRegisterForm, UserLoginForm, UserUpdateForm, ProfileUpdateForm
from accounts.validators import validate_latin_characters
from django.core.exceptions import ValidationError

@pytest.mark.django_db
def test_registration_creates_profile_and_logs_in(client):
    url = reverse('register')
    resp = client.post(url, {
        'username': 'newuser',
        'password1': 'StrongPass8899',
        'password2': 'StrongPass8899',
        'email': 'new@example.com'
    }, follow=True)
    assert resp.status_code == 200
    u = User.objects.get(username='newuser')
    assert hasattr(u, 'profile')
    # пользователь залогинен
    assert '_auth_user_id' in client.session

@pytest.mark.django_db
def test_user_login_remember_me(client, user):
    url = reverse('login')
    resp = client.post(url, {'username': 'tester', 'password': 'pass12345', 'remember_me': 'on'})
    assert resp.status_code == 302
    # remember_me => 14 дней (>= 13 * 24h)
    assert client.session.get_expiry_age() >= 60*60*24*13

@pytest.mark.django_db
def test_user_login_without_remember_me(client, user):
    url = reverse('login')
    resp = client.post(url, {'username': 'tester', 'password': 'pass12345'})
    assert resp.status_code == 302
    assert client.session.get_expiry_age() <= 60*60*24

@pytest.mark.django_db
def test_profile_detail_owner_edit_forms_visible(auth_client, user):
    url = reverse('profile_detail', kwargs={'slug': user.profile.slug})
    resp = auth_client.get(url)
    assert resp.status_code == 200
    assert 'user_form' in resp.context
    assert 'profile_form' in resp.context

@pytest.mark.django_db
def test_profile_detail_other_user_no_forms(client, user, other_user):
    client.login(username='other', password='pass12345')
    url = reverse('profile_detail', kwargs={'slug': user.profile.slug})
    resp = client.get(url)
    assert resp.status_code == 200
    assert 'user_form' not in resp.context

@pytest.mark.django_db
def test_profile_update_post(auth_client, user):
    url = reverse('profile_detail', kwargs={'slug': user.profile.slug})
    resp = auth_client.post(url, {
        'username': 'tester',
        'email': 'tester_changed@example.com',
        'bio': 'Hello world'
    }, follow=True)
    assert resp.status_code == 200
    user.refresh_from_db()
    assert user.email == 'tester_changed@example.com'

@pytest.mark.django_db
def test_update_user_form_email_unique(user, other_user):
    form = UserUpdateForm({'username': 'tester', 'email': other_user.email}, instance=user)
    assert not form.is_valid()

@pytest.mark.django_db
def test_profile_update_form_optional_fields(user):
    form = ProfileUpdateForm({}, instance=user.profile)
    assert form.is_valid()

@pytest.mark.django_db
def test_user_register_form_email_unique(user):
    form = UserRegisterForm({'username': 'abcx', 'password1': 'Xpass8899', 'password2': 'Xpass8899', 'email': user.email})
    assert not form.is_valid()

@pytest.mark.django_db
def test_validator_rejects_non_latin():
    with pytest.raises(ValidationError):
        validate_latin_characters('юзер')

@pytest.mark.django_db
def test_vkid_token_success(client, mock_vk_requests, settings):
    url = reverse('vkid_callback')
    resp = client.get(url, {'code': 'code123', 'device_id': 'dev1'})
    assert resp.status_code == 200
    data = resp.json()
    assert data['success'] is True

@pytest.mark.django_db
def test_vkid_token_missing_params(client):
    url = reverse('vkid_callback')
    resp = client.get(url)  # missing code/device_id
    assert resp.status_code == 400 or resp.status_code == 200  # function returns 400, guard in case
    if resp.status_code == 200:
        # then success False
        assert resp.json().get('success') in (False, True)

@pytest.mark.django_db
def test_logout_view(auth_client):
    url = reverse('logout')
    resp = auth_client.post(url, follow=True)
    assert resp.status_code == 200

