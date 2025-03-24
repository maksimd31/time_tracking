from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView
from django.views.generic import DetailView, UpdateView
from django.db import transaction
from .models import Profile
from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.views import LoginView, LogoutView
from .forms import UserLoginForm, UserRegisterForm, UserUpdateForm, ProfileUpdateForm,CustomPasswordChangeForm



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



class ChangePasswordView(LoginRequiredMixin,SuccessMessageMixin, PasswordChangeView):
    """
    Представление для смены пароля
    """
    form_class = CustomPasswordChangeForm
    template_name = 'accounts/change_password.html'
    success_message = "!"
    success_url = reverse_lazy('profile_detail')


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

        return context


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


class UserLoginView(SuccessMessageMixin, LoginView):
    """
    Авторизация
    """
    form_class = UserLoginForm
    template_name = 'accounts/user_login.html'
    next_page = 'home'
    success_message = 'Добро пожаловать!'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Вход на сайт'
        return context


class UserLogoutView(LogoutView):
    """
    Выход с сайта
    """
    next_page = 'home'



