# time_tracking
Проект для личного пользования. 

Учет времени

Проект построен на django, включает в себя функционал аутентификация и учета времени, данный проект создавался с целью
учета времени потраченного на обучение. 

Включает в себе функционал:
    1. "Старт" запуск отсчета времени и "стоп" конец отсчета, и записывается интервал в модель. 
\




#
# # Отключаем проверку CSRF для этого представления (используется для внешних POST-запросов)
# @csrf_exempt
# def vkid_token(request):
#     import json  # Импортируем модуль для работы с JSON
#
#     # Разрешаем только POST-запросы
#     if request.method != 'POST':
#         return JsonResponse({'error': 'Only POST allowed'}, status=405)
#
#     try:
#         # Декодируем тело запроса из JSON в Python-словарь
#         data = json.loads(request.body.decode())
#         # Получаем значения code, device_id и code_verifier из запроса
#         code = data.get('code')
#         device_id = data.get('device_id')
#         code_verifier = data.get('code_verifier')
#
#         print(data)
#         print(code, device_id, code_verifier)
#
#         # Проверяем, что все необходимые параметры присутствуют
#         if not code or not device_id or not code_verifier:
#             return JsonResponse({'error': 'No code, device_id, or code_verifier provided'}, status=400)
#
#         # Получаем client_id и redirect_uri из переменных окружения или настроек Django
#         client_id = os.getenv('SOCIAL_AUTH_VK_OAUTH2_KEY') or getattr(settings, 'SOCIAL_AUTH_VK_OAUTH2_KEY', None)
#         redirect_uri = os.getenv('SOCIAL_AUTH_VK_OAUTH2_REDIRECT_URI') or getattr(settings, 'SOCIAL_AUTH_VK_OAUTH2_REDIRECT_URI', None)
#
#         # Формируем данные для POST-запроса к VK ID OAuth
#         payload = {
#             'grant_type': 'authorization_code',  # Тип запроса — обмен кода на токен
#             'code': code,                        # Код авторизации VK
#             'device_id': device_id,              # Идентификатор устройства
#             'code_verifier': code_verifier,      # Проверочный код PKCE
#             'client_id': client_id,              # ID приложения VK
#             'redirect_uri': redirect_uri,        # Redirect URI, зарегистрированный в VK
#         }
#         # Заголовки для запроса (тип содержимого — форма)
#         headers = {'Content-Type': 'application/x-www-form-urlencoded'}
#
#         # Отправляем POST-запрос на сервер VK для обмена кода на токен
#         resp = requests.post('https://id.vk.com/oauth2/auth', data=payload, headers=headers)
#
#         try:
#             # Пытаемся распарсить ответ VK как JSON
#             resp_json = resp.json()
#         except Exception:
#             # Если ответ не JSON — возвращаем ошибку с текстом ответа
#             return JsonResponse({'error': 'VK ID response is not JSON', 'raw': resp.text, 'status_code': resp.status_code}, status=502)
#
#         # Если запрос успешен и в ответе есть access_token
#         if resp.status_code == 200 and 'access_token' in resp_json:
#             # Здесь можно реализовать login(request, user) по user_id из токена
#             return JsonResponse(resp_json)
#
#         # Если нет access_token — возвращаем ответ VK и статус
#         return JsonResponse({'vk_response': resp_json, 'status_code': resp.status_code}, status=resp.status_code)
#     except Exception as e:
#         # Любая другая ошибка — возвращаем её описание
#         return JsonResponse({'error': str(e)}, status=500)


# class SignUpView(generic.CreateView):
#     form_class = SignUpForm
#     success_url = reverse_lazy("login")
#     initial = None  # принимает {'key': 'value'}
#     template_name = "registration2/signup.html"
#
#     def dispatch(self, request, *args, **kwargs):
#         # перенаправит на домашнюю страницу, если пользователь попытается получить доступ к странице регистрации после авторизации
#         if request.user.is_authenticated:
#             return redirect(to='/')
#         return super().dispatch(request, *args, **kwargs)  # Добавлено
#
#     def get(self, request, *args, **kwargs):
#         form = self.form_class(initial=self.initial)
#         return render(request, self.template_name, {'form': form})
#
#     def post(self, request, *args, **kwargs):
#         form = self.form_class(request.POST)
#
#         if form.is_valid():
#             form.save()
#
#             username = form.cleaned_data.get('username')
#             messages.success(request, f'Вы успешно зарегистрировались {username}')
#
#             return redirect(to='login')
#
#         return render(request, self.template_name, {'form': form})

# def form_valid(self, form):
#     response = super().form_valid(form)
#     messages.success(self.request, "Вы успешно зарегистрировались")
#     return response

#
# class CustomLoginView(LoginView):
#     form_class = LoginForm
#
#     def form_valid(self, form):
#         remember_me = form.cleaned_data.get('remember_me')
#
#         if not remember_me:
#             # Установим время истечения сеанса равным 0 секундам. Таким образом, он автоматически закроет сеанс после закрытия браузера. И обновим данные.
#             self.request.session.set_expiry(0)
#             self.request.session.modified = True
#
#         # В противном случае сеанс браузера будет таким же как время сеанса cookie "SESSION_COOKIE_AGE", определенное в settings.py
#         return super(CustomLoginView, self).form_valid(form)

#
# @login_required
# def profile(request):
#     if request.method == 'POST':
#         user_form = UpdateUserForm(request.POST, instance=request.user)
#         profile_form = UpdateProfileForm(request.POST, request.FILES, instance=request.user.profile)
#
#         if user_form.is_valid() and profile_form.is_valid():
#             user_form.save()
#             profile_form.save()
#             messages.success(request, 'Готово')
#             return redirect(to='users-profile')
#     else:
#         user_form = UpdateUserForm(instance=request.user)
#         profile_form = UpdateProfileForm(instance=request.user.profile)
#
#     return render(request, 'registration2/profile.html', {'user_form': user_form, 'profile_form': profile_form})


#
# import traceback
# import os
# import requests
# from django.http import JsonResponse
# from django.contrib.auth import login
# from django.contrib.auth import get_user_model
#
#
# def vkid_callback(request):
#     # Получаем параметры code и device_id из GET-запроса
#     code = request.GET.get('code')
#     device_id = request.GET.get('device_id')
#
#     # Проверяем, что оба параметра присутствуют
#     if not code or not device_id:
#         return JsonResponse({'success': False, 'message': 'Missing code or device_id'}, status=400)
#
#     # Устанавливаем client_id, client_secret и redirect_uri для VK ID OAuth
#     client_id = '53649137'
#     client_secret = os.getenv('SOCIAL_AUTH_VK_OAUTH2_SECRET') or 'ZWSkWRxDlB79hQUMELn6'
#     redirect_uri = 'https://225e-92-42-96-168.ngrok-free.app/vkid/callback/'
#
#     # Выводим параметры в консоль для отладки
#     print('client_id:', client_id)
#     print('client_secret:', client_secret)
#     print('redirect_uri:', redirect_uri)
#     print('code:', code)
#     print('device_id:', device_id)
#
#     # URL для получения токена VK ID
#     token_url = 'https://id.vk.com/oauth/token'
#
#     # Заголовки для POST-запроса
#     headers = {
#         'Content-Type': 'application/x-www-form-urlencoded'
#     }
#     # Формируем payload для обмена code на access_token
#     payload = {
#         'grant_type': 'authorization_code',
#         'code': code,
#         'device_id': device_id,
#         'client_id': client_id,
#         'client_secret': client_secret,
#         'redirect_uri': redirect_uri,
#     }
#
#     try:
#         # Делаем POST-запрос к VK ID для получения токена
#         response = requests.post(token_url, data=payload, headers=headers)
#         response.raise_for_status()  # выбросит исключение при ошибке HTTP
#         data = response.json()  # парсим ответ как JSON
#     except requests.exceptions.RequestException as e:
#         # Ошибка сети или HTTP — возвращаем ошибку
#         return JsonResponse({'success': False, 'message': f'Network error: {str(e)}'}, status=500)
#     except ValueError:
#         # Ответ не является JSON — возвращаем ошибку
#         return JsonResponse({'success': False, 'message': f'Invalid JSON response: {response.text}'}, status=500)
#
#     # Проверяем, что в ответе есть access_token
#     if 'access_token' not in data:
#         return JsonResponse({'success': False, 'message': f'Error from VK: {data}'}, status=400)
#
#     try:
#         # Получаем access_token и user_id из ответа VK
#         access_token = data['access_token']
#         user_id = data.get('user_id') or 'vkid_user'
#
#         # Получаем модель пользователя Django
#         User = get_user_model()
#         # Ищем или создаём пользователя с username на основе user_id VK
#         user, created = User.objects.get_or_create(username=f'vkid_{user_id}')
#         # Выполняем вход пользователя в систему
#         login(request, user)
#     except Exception as e:
#         # Любая ошибка — возвращаем ошибку с трассировкой
#         traceback_str = traceback.format_exc()
#         return JsonResponse({'success': False, 'message': str(e), 'traceback': traceback_str}, status=500)
#
#     # Всё прошло успешно — возвращаем успех
#     return JsonResponse({'success': True})

#
# # Отключаем проверку CSRF для этого представления (используется для внешних POST-запросов)
# @csrf_exempt
# def vkid_token(request):
#     import json  # Импортируем модуль для работы с JSON
#
#     # Разрешаем только POST-запросы
#     if request.method != 'POST':
#         return JsonResponse({'error': 'Only POST allowed'}, status=405)
#
#     try:
#         # Декодируем тело запроса из JSON в Python-словарь
#         data = json.loads(request.body.decode())
#         # Получаем значения code, device_id и code_verifier из запроса
#         code = data.get('code')
#         device_id = data.get('device_id')
#         code_verifier = data.get('code_verifier')
#
#         print(data)
#         print(code, device_id, code_verifier)
#
#         # Проверяем, что все необходимые параметры присутствуют
#         if not code or not device_id or not code_verifier:
#             return JsonResponse({'error': 'No code, device_id, or code_verifier provided'}, status=400)
#
#         # Получаем client_id и redirect_uri из переменных окружения или настроек Django
#         client_id = os.getenv('SOCIAL_AUTH_VK_OAUTH2_KEY') or getattr(settings, 'SOCIAL_AUTH_VK_OAUTH2_KEY', None)
#         redirect_uri = os.getenv('SOCIAL_AUTH_VK_OAUTH2_REDIRECT_URI') or getattr(settings,
#                                                                                   'SOCIAL_AUTH_VK_OAUTH2_REDIRECT_URI',
#                                                                                   None)
#
#         # Формируем данные для POST-запроса к VK ID OAuth
#         payload = {
#             'grant_type': 'authorization_code',  # Тип запроса — обмен кода на токен
#             'code': code,  # Код авторизации VK
#             'device_id': device_id,  # Идентификатор устройства
#             'code_verifier': code_verifier,  # Проверочный код PKCE
#             'client_id': client_id,  # ID приложения VK
#             'redirect_uri': redirect_uri,  # Redirect URI, зарегистрированный в VK
#         }
#         # Заголовки для запроса (тип содержимого — форма)
#         headers = {'Content-Type': 'application/x-www-form-urlencoded'}
#
#         # Отправляем POST-запрос на сервер VK для обмена кода на токен
#         resp = requests.post('https://id.vk.com/oauth2/auth', data=payload, headers=headers)
#
#         try:
#             # Пытаемся распарсить ответ VK как JSON
#             resp_json = resp.json()
#         except Exception:
#             # Если ответ не JSON — возвращаем ошибку с текстом ответа
#             return JsonResponse(
#                 {'error': 'VK ID response is not JSON', 'raw': resp.text, 'status_code': resp.status_code}, status=502)
#
#         # Если запрос успешен и в ответе есть access_token
#         if resp.status_code == 200 and 'access_token' in resp_json:
#             # Здесь можно реализовать login(request, user) по user_id из токена
#             return JsonResponse(resp_json)
#
#         # Если нет access_token — возвращаем ответ VK и статус
#         return JsonResponse({'vk_response': resp_json, 'status_code': resp.status_code}, status=resp.status_code)
#     except Exception as e:
#         # Любая другая ошибка — возвращаем её описание
#         return JsonResponse({'error': str(e)}, status=500)
