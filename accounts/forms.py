from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm, PasswordResetForm

from services.utils import FormStyleMixin, PlaceholderAndStyleMixin, RememberMeMixin
from .validators import validate_latin_characters
from django.contrib.auth.models import User
from .models import Profile
from django import forms


# class SignUpForm(UserCreationForm):
#     username = forms.CharField(max_length=100, label="",
#                                widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Логин'}),
#                                validators=[validate_latin_characters])
#     email = forms.EmailField(max_length=100, label="",
#                              widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Email '}))
#     password1 = forms.CharField(max_length=100, label="",
#                                 widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Пароль'}))
#     password2 = forms.CharField(max_length=100, label="", widget=forms.TextInput(
#         attrs={'class': 'form-control', 'placeholder': 'Подтверждение пароля'}))
#
#     class Meta:
#         model = User
#         fields = ['username', 'email', 'password1', 'password2']
#
#
# widget = forms.PasswordInput()


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        max_length=100,
        label="",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Логин'}),
        validators=[validate_latin_characters]
    )

    password = forms.CharField(max_length=100, label="",
                               widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Пароль'}))

    remember_me = forms.BooleanField(
        required=False,
        label="Запомнить меня",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = User
        fields = ['username', 'password', 'remember_me']


# class UpdateUserForm(forms.ModelForm):
#     username = forms.CharField(max_length=100,
#                                required=True,
#                                widget=forms.TextInput())
#     email = forms.EmailField(required=True,
#                              widget=forms.TextInput())
#
#     class Meta:
#         model = User
#         fields = ['username', 'email']


# class UpdateProfileForm(forms.ModelForm):
#     avatar = forms.ImageField(widget=forms.FileInput())
#     bio = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}))
#
#     class Meta:
#         model = Profile
#         fields = ['avatar', 'bio']


class UserUpdateForm(forms.ModelForm):
    """
    Форма обновления данных пользователя
    """
    username = forms.CharField(max_length=100,
                               label="Логин",
                               widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Логин'}),
                               validators=[validate_latin_characters])
    email = forms.EmailField(label="Email", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Email '}))

    class Meta:
        model = User
        fields = ('username', 'email',)

    def clean_email(self):
        """
        Проверка email на уникальность
        """
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Email адрес должен быть уникальным')
        return email


class ProfileUpdateForm(forms.ModelForm):
    """
    Форма обновления данных профиля пользователя
    """
    avatar = forms.ImageField(
        required=False,
        label="Фотография",
        widget=forms.FileInput(attrs={
            'class': 'form-control',
        })
    )
    bio = forms.CharField(
        required=False,
        label="О себе",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Кратко расскажите о себе'
        })
    )

    class Meta:
        model = Profile
        fields = ('avatar', 'bio')


class UserRegisterForm(PlaceholderAndStyleMixin,FormStyleMixin, UserCreationForm):
    """
    Переопределенная форма регистрации пользователей
    """

    class Meta(UserCreationForm.Meta):
        fields = ('username', 'password1', 'password2', 'email')

    def clean_email(self):
        """
        Проверка email на уникальность
        """
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError('Такой email уже используется в системе')
        return email

    placeholders = {
        'username': 'Придумайте свой логин',
        'password1': 'Придумайте свой пароль',
        'password2': 'Повторите придуманный пароль',
        'email': 'Введите свой email',
    }


class UserLoginForm(RememberMeMixin,PlaceholderAndStyleMixin, FormStyleMixin, AuthenticationForm):
    """
    Форма авторизации на сайте
    """

    placeholders = {
        'username': 'Логин',
        'password': 'Пароль'
    }




class CustomPasswordChangeForm(PlaceholderAndStyleMixin, FormStyleMixin, PasswordChangeForm):
    """
    Форма и обновление стилей формы авторизации
    """
    placeholders = {
        'old_password': 'Старый пароль',
        'new_password1': 'Новый пароль',
        'new_password2': 'Повторите новый пароль',
    }


class CustomPasswordResetForm(PlaceholderAndStyleMixin, FormStyleMixin, PasswordResetForm):

    placeholders = {
        'email' : 'Введите адрес своей почты'
    }
