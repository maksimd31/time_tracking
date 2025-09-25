import os
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

load_dotenv()

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

class ChangePasswordView(LoginRequiredMixin, SuccessMessageMixin, PasswordChangeView):
    """
    Представление для смены пароля
    """
    form_class = CustomPasswordChangeForm
    template_name = 'accounts/change_password.html'
    success_message = "!"

    def get_success_url(self):
        return reverse_lazy('profile_detail', kwargs={'slug': self.request.user.profile.slug})


class ProfileDetailView(LoginRequiredMixin, DetailView):
    """
    Представление для просмотра профиля
    """
    model = Profile
    context_object_name = 'profile'
    template_name = 'accounts/profile_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Профиль пользователя: {self.object.user.username}'
        context['user'] = self.object.user  # Добавляем user в контекст
        if self.request.user == self.object.user:
            context.setdefault('user_form', UserUpdateForm(instance=self.object.user))
            context.setdefault('profile_form', ProfileUpdateForm(instance=self.object))
        return context

    def post(self, request, *args, **kwargs):
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
    """
    Представление для редактирования профиля
    """
    model = Profile
    form_class = ProfileUpdateForm
    template_name = 'accounts/profile_edit.html'
    success_message = 'Запись была успешно обновлена!'

    def get_object(self, queryset=None):
        return self.request.user.profile

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Редактирование профиля пользователя: {self.request.user.username}'
        if self.request.POST:
            context['user_form'] = UserUpdateForm(self.request.POST, instance=self.request.user)
        else:
            context['user_form'] = UserUpdateForm(instance=self.request.user)
        return context

    def form_valid(self, form):
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
        return reverse_lazy('profile_detail', kwargs={'slug': self.object.slug})


class UserRegisterView(SuccessMessageMixin, CreateView):
    """
    Представление регистрации с формой регистрации
    """
    form_class = UserRegisterForm
    success_url = reverse_lazy('home')
    template_name = 'accounts/user_register.html'
    success_message = 'Вы успешно зарегистрировались. Можете войти на сайт!'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Регистрация на сайте'
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.object
        backend = 'django.contrib.auth.backends.ModelBackend'
        login(self.request, user, backend=backend)
        return response


class UserLoginView(SuccessMessageMixin, LoginView):
    """
    Авторизация
    """
    form_class = UserLoginForm
    template_name = 'accounts/user_login.html'
    next_page = 'home'
    success_message = 'Добро пожаловать!'

    def form_valid(self, form):
        """
        Если форма валидна, обработать 'remember_me' и выполнить вход.
        """
        response = super().form_valid(form)
        remember_me = form.cleaned_data.get('remember_me')
        if not remember_me:
            self.request.session.set_expiry(60 * 60 * 24)
        else:
            self.request.session.set_expiry(1209600)
        return response

    def get_context_data(self, **kwargs):
        """
        Передача дополнительных данных в контекст.
        """
        context = super().get_context_data(**kwargs)
        context['title'] = 'Вход на сайт'
        return context


class UserLogoutView(LogoutView):
    """
    Выход с сайта
    """
    next_page = 'home'


from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json


# Отключаем проверку CSRF для этого view (для тестирования, в продакшене лучше использовать CSRF!)
@csrf_exempt
def vkid_token(request):
    import json  # Импортируем модуль json для работы с JSON-данными
    try:
        # Обработка разных методов запроса
        if request.method == 'GET':
            # Получаем параметры из строки запроса (GET)
            code = request.GET.get('code')
            device_id = request.GET.get('device_id')
            code_verifier = request.GET.get('code_verifier')
        elif request.method == 'POST':
            # Получаем параметры из тела запроса (POST, JSON)
            data = json.loads(request.body.decode())
            code = data.get('code')
            device_id = data.get('device_id')
            code_verifier = data.get('code_verifier')
        else:
            # Если метод не GET и не POST — возвращаем ошибку
            return JsonResponse({'success': False, 'message': 'Only GET and POST allowed'}, status=405)

        # Логируем полученные параметры для отладки
        print('VKID CALLBACK PARAMS:', {'code': code, 'device_id': device_id, 'code_verifier': code_verifier})
        # Проверяем, что обязательные параметры присутствуют
        if not code or not device_id:
            return JsonResponse({'success': False, 'message': 'No code or device_id provided'}, status=400)

        # Получаем client_id и redirect_uri из переменных окружения или настроек Django
        client_id = os.getenv('SOCIAL_AUTH_VK_OAUTH2_KEY') or getattr(settings, 'SOCIAL_AUTH_VK_OAUTH2_KEY', None)
        redirect_uri = os.getenv('SOCIAL_AUTH_VK_OAUTH2_REDIRECT_URI') or getattr(settings, 'SOCIAL_AUTH_VK_OAUTH2_REDIRECT_URI', None)

        # Формируем payload для запроса токена VK ID
        payload = {
            'grant_type': 'authorization_code',  # Тип grant-а — авторизационный код
            'code': code,                        # Код авторизации
            'device_id': device_id,              # Идентификатор устройства
            'client_id': client_id,              # ID приложения VK
            'redirect_uri': redirect_uri,        # Redirect URI, который был указан при авторизации
        }
        # Если есть code_verifier (PKCE), добавляем его
        if code_verifier:
            payload['code_verifier'] = code_verifier
        # Заголовки для запроса (тип контента — form-urlencoded)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        # URL для получения access_token VK ID
        token_url = 'https://id.vk.com/oauth2/token'

        try:
            # Делаем POST-запрос к VK ID для обмена кода на access_token
            resp = requests.post(token_url, data=payload, headers=headers)
            try:
                # Пробуем распарсить ответ как JSON
                resp_json = resp.json()
            except Exception:
                # Если не удалось — выводим сырой ответ и возвращаем ошибку
                print('VKID TOKEN RAW RESPONSE:', resp.text)
                return JsonResponse({'success': False, 'message': 'VKID token exchange error', 'raw': resp.text, 'status_code': resp.status_code}, status=500)

            # Если запрос успешен и есть access_token
            if resp.status_code == 200 and 'access_token' in resp_json:
                access_token = resp_json['access_token']
                # Получаем информацию о пользователе через VK ID API
                user_info_resp = requests.get(
                    'https://id.vk.com/oauth2/user_info',
                    headers={'Authorization': f'Bearer {access_token}'}
                )
                try:
                    # Пробуем распарсить ответ как JSON
                    user_info = user_info_resp.json()
                except Exception:
                    # Если не удалось — выводим сырой ответ и возвращаем ошибку
                    print('VKID USER INFO RAW RESPONSE:', user_info_resp.text)
                    return JsonResponse({'success': False, 'message': 'VKID user info error', 'raw': user_info_resp.text, 'status_code': user_info_resp.status_code}, status=500)
                # Получаем VK user id из ответа
                vk_user_id = user_info.get('sub')
                if not vk_user_id:
                    # Если нет user id — ошибка
                    print('NO VK USER ID:', user_info)
                    return JsonResponse({'success': False, 'message': 'No VK user id'}, status=400)
                # Получаем модель пользователя Django
                User = get_user_model()
                # Ищем пользователя по username или создаём нового
                user, created = User.objects.get_or_create(username=f'vkid_{vk_user_id}')
                # Выполняем вход пользователя в Django
                login(request, user)
                # Возвращаем успешный ответ с информацией о пользователе
                return JsonResponse({'success': True, 'user_info': user_info})
            # Если не получили access_token — выводим ошибку и возвращаем ответ
            print('VKID TOKEN RESPONSE ERROR:', resp_json)
            return JsonResponse({'success': False, 'message': resp_json}, status=resp.status_code)
        except Exception as e:
            # Ловим ошибки обмена токена или получения user info
            print('VKID TOKEN EXCHANGE/USER INFO ERROR:', str(e))
            return JsonResponse({'success': False, 'message': f'VKID token exchange or user info error: {str(e)}'}, status=500)
    except Exception as e:
        # Ловим любые другие ошибки
        print('VKID_TOKEN GENERAL ERROR:', str(e))
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
