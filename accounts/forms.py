from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm


class SignUpForm(UserCreationForm):

    username = forms.CharField(max_length=100, label="", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Имя пользователя'}))

    email = forms.EmailField(max_length=100, label="", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Email '}))

    password1 = forms.CharField(max_length=100, label="", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Пароль'}))

    password2 = forms.CharField(max_length=100, label="", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Подтверждение пароля'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

# widget=forms.PasswordInput()


class LoginForm(AuthenticationForm):
    username = forms.CharField(max_length=100, label="", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Имя пользователя'}))

    password = forms.CharField(max_length=100, label="", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Пароль'}))

    remember_me = forms.BooleanField(
        required=False,
        label="Запомнить меня",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = User
        fields = ['username', 'password', 'remember_me']
