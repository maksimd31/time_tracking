"""Views handling authentication flow, profile management, and VKID hook."""

import os
import logging
from django.contrib.auth import login, get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView
from django.http.response import HttpResponseBadRequest
from django.views.generic import DetailView, UpdateView
from django.db import transaction
from .models import Profile
from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.views import LoginView, LogoutView
from .forms import UserLoginForm, UserRegisterForm, UserUpdateForm, ProfileUpdateForm, CustomPasswordChangeForm
import requests
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
import secrets
from django.shortcuts import render, redirect
from dotenv import load_dotenv
from django.contrib import messages
from time_tracking_or.models import DailySummary, TimeCounter, TimeInterval

load_dotenv()

logger = logging.getLogger('vk_auth')

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


def _transfer_guest_data(guest_user_id, target_user):
    """Move guest counters and intervals to the authenticated user."""
    if not guest_user_id or not target_user:
        return

    try:
        guest_user_id = int(guest_user_id)
    except (TypeError, ValueError):
        return

    if guest_user_id == target_user.id:
        return

    UserModel = get_user_model()
    try:
        guest_user = UserModel.objects.get(id=guest_user_id)
    except UserModel.DoesNotExist:
        return

    with transaction.atomic():
        TimeCounter.objects.filter(user=guest_user).update(user=target_user)
        TimeInterval.objects.filter(user=guest_user).update(user=target_user)
        DailySummary.objects.filter(user=guest_user).update(user=target_user)
        guest_user.delete()

class ChangePasswordView(LoginRequiredMixin, SuccessMessageMixin, PasswordChangeView):
    """Allow an authenticated user to change their password."""
    form_class = CustomPasswordChangeForm
    template_name = 'accounts/change_password.html'
    success_message = "!"

    def get_success_url(self):
        """Send the user back to their profile after password change."""
        return reverse_lazy('profile_detail', kwargs={'slug': self.request.user.profile.slug})


class ProfileDetailView(LoginRequiredMixin, DetailView):
    """Display profile information and inline update forms."""
    model = Profile
    context_object_name = 'profile'
    template_name = 'accounts/profile_detail.html'

    def get_context_data(self, **kwargs):
        """Supply profile object plus bound forms for the owner."""
        context = super().get_context_data(**kwargs)
        context['title'] = f'Профиль пользователя: {self.object.user.username}'
        context['user'] = self.object.user
        if self.request.user == self.object.user:
            context.setdefault('user_form', UserUpdateForm(instance=self.object.user))
            context.setdefault('profile_form', ProfileUpdateForm(instance=self.object))
        return context

    def post(self, request, *args, **kwargs):
        """Process inline profile updates coming from HTMX or full POST."""
        self.object = self.get_object()
        if request.user != self.object.user:
            messages.error(request, 'Вы не можете изменять профиль другого пользователя.')
            return redirect('profile_detail', slug=self.object.slug)

        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=self.object)

        if user_form.is_valid() and profile_form.is_valid():
            with transaction.atomic():
                user_form.save()
                profile_form.save()
            messages.success(request, 'Настройки профиля обновлены.')
            return redirect('profile_detail', slug=self.object.slug)

        context = self.get_context_data()
        context['user_form'] = user_form
        context['profile_form'] = profile_form
        return self.render_to_response(context)


class ProfileUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Legacy endpoint that proxies to inline profile editing."""
    model = Profile
    form_class = ProfileUpdateForm
    template_name = 'accounts/profile_edit.html'
    success_message = 'Запись была успешно обновлена!'

    def get_object(self, queryset=None):
        """Return the profile owned by the current request user."""
        return self.request.user.profile

    def get_context_data(self, **kwargs):
        """Attach both profile and user forms to the context."""
        context = super().get_context_data(**kwargs)
        context['title'] = f'Редактирование профиля пользователя: {self.request.user.username}'
        if self.request.POST:
            context['user_form'] = UserUpdateForm(self.request.POST, instance=self.request.user)
        else:
            context['user_form'] = UserUpdateForm(instance=self.request.user)
        return context

    def form_valid(self, form):
        """Validate both forms inside a transaction before saving."""
        context = self.get_context_data()
        user_form = context['user_form']
        with transaction.atomic():
            if all([form.is_valid(), user_form.is_valid()]):
                user_form.save()
                form.save()
            else:
                context.update({'user_form': user_form})
                return self.render_to_response(context)
        return super().form_valid(form)

    def get_success_url(self):
        """Return to the detailed profile page on success."""
        return reverse_lazy('profile_detail', kwargs={'slug': self.object.slug})


class UserRegisterView(SuccessMessageMixin, CreateView):
    """Create a new user account and immediately log them in."""
    form_class = UserRegisterForm
    success_url = reverse_lazy('home')
    template_name = 'accounts/user_register.html'
    success_message = 'Вы успешно зарегистрировались. Можете войти на сайт!'

    def get_context_data(self, **kwargs):
        """Attach page title for template consumption."""
        context = super().get_context_data(**kwargs)
        context['title'] = 'Регистрация на сайте'
        raw_limit = self.request.GET.get('guest_limit')
        limit_from_url = None
        if raw_limit is not None:
            try:
                limit_from_url = max(int(raw_limit), 0)
            except (TypeError, ValueError):
                limit_from_url = None
        context['guest_counter_limit'] = limit_from_url or getattr(settings, 'GUEST_COUNTER_LIMIT', 0)
        context['guest_limit_prompt'] = bool(limit_from_url)
        return context

    def form_valid(self, form):
        """Persist the user and authenticate them via default backend."""
        guest_user_id = self.request.session.get('guest_user_id')
        response = super().form_valid(form)
        user = self.object
        backend = 'django.contrib.auth.backends.ModelBackend'
        login(self.request, user, backend=backend)
        _transfer_guest_data(guest_user_id, user)
        self.request.session['is_guest'] = False
        self.request.session.pop('guest_ip', None)
        self.request.session.pop('guest_user_id', None)
        return response


class UserLoginView(SuccessMessageMixin, LoginView):
    """Authenticate existing users with optional remember-me."""
    form_class = UserLoginForm
    template_name = 'accounts/user_login.html'
    next_page = 'home'
    success_message = 'Добро пожаловать!'

    def form_valid(self, form):
        """Adjust session expiry according to the remember-me checkbox."""
        guest_user_id = self.request.session.get('guest_user_id')
        response = super().form_valid(form)
        _transfer_guest_data(guest_user_id, self.request.user)
        self.request.session['is_guest'] = False
        self.request.session.pop('guest_ip', None)
        self.request.session.pop('guest_user_id', None)
        remember_me = form.cleaned_data.get('remember_me')
        if not remember_me:
            self.request.session.set_expiry(60 * 60 * 24)
        else:
            self.request.session.set_expiry(1209600)
        return response

    def get_context_data(self, **kwargs):
        """Attach page title for templates and VKID widget config."""
        context = super().get_context_data(**kwargs)
        context['title'] = 'Вход на сайт'
        from django.conf import settings
        context['vkid_app_id'] = getattr(settings, 'VKID_APP_ID', None)
        context['vkid_redirect_url'] = getattr(settings, 'VKID_REDIRECT_URL', None)
        context['vkid_scope'] = getattr(settings, 'VKID_SCOPE', '')
        context['vkid_frontend_exchange'] = os.getenv('VKID_FRONTEND_EXCHANGE', 'False') == 'True'
        return context


class UserLogoutView(LogoutView):
    """Log out the current user and redirect to the dashboard."""
    next_page = 'home'


from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json


# Отключаем проверку CSRF для этого view (для тестирования, в продакшене лучше использовать CSRF!)
@csrf_exempt
def vkid_token(request):
    """Handle VK ID auth callback (test-only helper).

    Теперь поддерживает два варианта:
    1) Backend exchange: приходит code + device_id (+ optional code_verifier) – сервер сам меняет код на access_token.
    2) Frontend exchange: приходит access_token прямо с фронта (VKID.Auth.exchangeCode) – сервер только получает user_info.

    Дополнительно: сохраняем имя, email и аватар пользователя (если доступны).
    """
    import json
    from django.core.files.base import ContentFile
    from django.db import transaction

    def _apply_user_info(user, user_info: dict):
        """Обновить first_name/last_name/email на основе user_info без агрессивного перезаписи.
        Поддерживаем ключи: name, first_name, last_name, email, given_name, family_name, picture/avatar/photo.
        """
        changed = False
        # Имя
        first_name = user_info.get('first_name') or user_info.get('given_name')
        last_name = user_info.get('last_name') or user_info.get('family_name')
        # Если есть единое поле name и нет отдельных
        if not (first_name or last_name) and user_info.get('name'):
            full = user_info.get('name').strip()
            parts = full.split(' ', 1)
            first_name = parts[0]
            if len(parts) > 1:
                last_name = parts[1]
        if first_name and not user.first_name:
            user.first_name = first_name[:150]
            changed = True
        if last_name and not user.last_name:
            user.last_name = last_name[:150]
            changed = True
        # Email — только если у пользователя ещё пусто
        email = user_info.get('email')
        if email and not user.email:
            user.email = email[:254]
            changed = True
        if changed:
            user.save(update_fields=['first_name', 'last_name', 'email'])

        # Профиль (создаём если сигналы отключены/не сработали)
        from .models import Profile
        profile, _ = Profile.objects.get_or_create(user=user)

        # Аватар: ищем поле picture/photo/avatar с URL
        avatar_url = (
            user_info.get('picture') or user_info.get('photo') or user_info.get('avatar') or user_info.get('photo_200')
        )
        # Скачиваем только если у профиля дефолт и есть валидный http(s) URL
        if avatar_url and isinstance(avatar_url, str) and avatar_url.startswith('http'):
            # Не перекачиваем, если уже не default
            if profile.avatar and 'default' not in str(profile.avatar.name):
                return
            try:
                r = requests.get(avatar_url, timeout=5)
                ct = r.headers.get('Content-Type', '') if hasattr(r, 'headers') else ''
                if r.status_code == 200 and r.content and ('image/' in ct or avatar_url.lower().endswith(('.jpg', '.jpeg', '.png'))):
                    ext = '.jpg'
                    for cand in ('.png', '.jpeg', '.jpg'):
                        if avatar_url.lower().endswith(cand):
                            ext = cand
                            break
                    profile.avatar.save(f'vkid_{user.pk}{ext}', ContentFile(r.content), save=True)
            except Exception as e:
                # Лог — не падаем из-за аватара
                logger.warning('VKID AVATAR DOWNLOAD ERROR: %s', e)

    try:
        if request.method == 'GET':
            code = request.GET.get('code')
            device_id = request.GET.get('device_id')
            code_verifier = request.GET.get('code_verifier')
            access_token_front = request.GET.get('access_token')
        elif request.method == 'POST':
            data = json.loads(request.body.decode() or '{}')
            code = data.get('code')
            device_id = data.get('device_id')
            code_verifier = data.get('code_verifier')
            access_token_front = data.get('access_token')
        else:
            return JsonResponse({'success': False, 'message': 'Only GET and POST allowed'}, status=405)

        logger.info('VKID CALLBACK PARAMS: code=%s device_id=%s code_verifier=%s frontend_token=%s', code, device_id, bool(code_verifier), bool(access_token_front))

        # Вариант 2: уже есть access_token – пропускаем обмен
        if access_token_front:
            user_info_resp = requests.get(
                'https://id.vk.com/oauth2/user_info',
                headers={'Authorization': f'Bearer {access_token_front}'}
            )
            try:
                user_info = user_info_resp.json()
            except Exception:
                logger.error('VKID user info parse error (frontend). Raw=%s', user_info_resp.text)
                return JsonResponse({'success': False, 'message': 'VKID user info error', 'raw': user_info_resp.text}, status=500)
            vk_user_id = user_info.get('sub')
            if not vk_user_id:
                return JsonResponse({'success': False, 'message': 'No VK user id'}, status=400)
            UserModel = get_user_model()
            with transaction.atomic():
                user, _ = UserModel.objects.get_or_create(username=f'vkid_{vk_user_id}')
                _apply_user_info(user, user_info)
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return JsonResponse({'success': True, 'user_info': user_info, 'mode': 'frontend'})

        # Вариант 1 (как раньше): нужен code + device_id
        if not code or not device_id:
            return JsonResponse({'success': False, 'message': 'No code or device_id provided'}, status=400)

        client_id = os.getenv('SOCIAL_AUTH_VK_OAUTH2_KEY') or getattr(settings, 'SOCIAL_AUTH_VK_OAUTH2_KEY', None)
        redirect_uri = os.getenv('SOCIAL_AUTH_VK_OAUTH2_REDIRECT_URI') or getattr(settings, 'SOCIAL_AUTH_VK_OAUTH2_REDIRECT_URI', None)

        payload = {
            'grant_type': 'authorization_code',
            'code': code,
            'device_id': device_id,
            'client_id': client_id,
            'redirect_uri': redirect_uri,
        }
        if code_verifier:
            payload['code_verifier'] = code_verifier
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        token_url = 'https://id.vk.com/oauth2/token'

        try:
            resp = requests.post(token_url, data=payload, headers=headers)
            try:
                resp_json = resp.json()
            except Exception:
                logger.error('VKID token exchange raw response parse error. Raw=%s', resp.text)
                return JsonResponse({'success': False, 'message': 'VKID token exchange error', 'raw': resp.text, 'status_code': resp.status_code}, status=500)

            if resp.status_code == 200 and 'access_token' in resp_json:
                access_token = resp_json['access_token']
                user_info_resp = requests.get(
                    'https://id.vk.com/oauth2/user_info',
                    headers={'Authorization': f'Bearer {access_token}'}
                )
                try:
                    user_info = user_info_resp.json()
                except Exception:
                    logger.error('VKID user info parse error (backend). Raw=%s', user_info_resp.text)
                    return JsonResponse({'success': False, 'message': 'VKID user info error', 'raw': user_info_resp.text, 'status_code': user_info_resp.status_code}, status=500)
                vk_user_id = user_info.get('sub')
                if not vk_user_id:
                    logger.error('NO VK USER ID (backend): %s', user_info)
                    return JsonResponse({'success': False, 'message': 'No VK user id'}, status=400)
                UserModel = get_user_model()
                with transaction.atomic():
                    user, created = UserModel.objects.get_or_create(username=f'vkid_{vk_user_id}')
                    _apply_user_info(user, user_info)
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                logger.info('VKID backend login success user=%s mode=backend', user.username)
                return JsonResponse({'success': True, 'user_info': user_info, 'mode': 'backend'})
            logger.warning('VKID TOKEN RESPONSE ERROR status=%s body=%s', resp.status_code, resp_json)
            return JsonResponse({'success': False, 'message': resp_json}, status=resp.status_code)
        except Exception as e:
            logger.exception('VKID token exchange or user info error: %s', e)
            return JsonResponse({'success': False, 'message': f'VKID token exchange or user info error: {str(e)}'}, status=500)
    except Exception as e:
        logger.exception('VKID_TOKEN GENERAL ERROR: %s', e)
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
