from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Profile
from .validators import validate_latin_characters


class SignUpForm(UserCreationForm):

    username = forms.CharField(max_length=100, label="", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Логин'}), validators=[validate_latin_characters])

    email = forms.EmailField(max_length=100, label="", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Email '}))

    password1 = forms.CharField(max_length=100, label="", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Пароль'}))

    password2 = forms.CharField(max_length=100, label="", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Подтверждение пароля'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

# widget=forms.PasswordInput()


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        max_length=100,
        label="",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Логин'}),
        validators=[validate_latin_characters]
    )

    password = forms.CharField(max_length=100, label="", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Пароль'}))

    remember_me = forms.BooleanField(
        required=False,
        label="Запомнить меня",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = User
        fields = ['username', 'password', 'remember_me']


class UpdateUserForm(forms.ModelForm):
    username = forms.CharField(max_length=100,
                               required=True,
                               widget=forms.TextInput())
    email = forms.EmailField(required=True,
                             widget=forms.TextInput())

    class Meta:
        model = User
        fields = ['username', 'email']


class UpdateProfileForm(forms.ModelForm):
    avatar = forms.ImageField(widget=forms.FileInput())
    bio = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}))

    class Meta:
        model = Profile
        fields = ['avatar', 'bio']
