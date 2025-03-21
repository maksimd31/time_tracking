from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
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
                               label="",
                               widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Логин'}),
                               validators=[validate_latin_characters])
    email = forms.EmailField(label="", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Email '}))

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
        label="",  # Убираем стандартную метку поля
        widget=forms.FileInput(attrs={
            'class': 'form-control',  # Добавляем класс для стилизации
            'placeholder': 'Загрузите ваш аватар',  # Добавляем текст подсказки
        })
    )

    class Meta:
        model = Profile
        fields = ('avatar',)  # Указываем, какие поля включить в форму


class UserRegisterForm(UserCreationForm):
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

    def __init__(self, *args, **kwargs):
        """
        Обновление стилей формы регистрации
        """
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({"placeholder": "Придумайте свой логин"})
        self.fields['password1'].widget.attrs.update({"placeholder": "Придумайте свой пароль"})
        self.fields['password2'].widget.attrs.update({"placeholder": "Повторите придуманный пароль"})
        self.fields['email'].widget.attrs.update({"placeholder": "Введите свой email"})
        self.fields['username'].label = ''
        self.fields['password1'].label = ''
        self.fields['password2'].label = ''
        self.fields['email'].label = ''

        for field in self.fields:
            self.fields[field].widget.attrs.update({"class": "form-control", "autocomplete": "off"})


class UserLoginForm(AuthenticationForm):
    """
    Форма авторизации на сайте
    """

    def __init__(self, *args, **kwargs):
        """
        Обновление стилей формы авторизации
        """
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({"placeholder": "Логин"})
        self.fields['password'].widget.attrs.update({"placeholder": "Пароль"})
        self.fields['username'].label = ''
        self.fields['password'].label = ''

        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                'autocomplete': 'off'
            })


class CustomPasswordChangeForm(PasswordChangeForm):
    """
    Обновление стилей формы авторизации
    """

    def __init__(self, *args, **kwargs):
        """
        Обновление стилей формы авторизации
        """
        super().__init__(*args, **kwargs)
        self.fields['old_password'].widget.attrs.update({"placeholder": "Старый пароль"})
        self.fields['new_password1'].widget.attrs.update({"placeholder": "Новый пароль"})
        self.fields['new_password2'].widget.attrs.update({"placeholder": "Повторите новый пароль"})

        self.fields['old_password'].label = ''
        self.fields['new_password1'].label = ''
        self.fields['new_password2'].label = ''


        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                'autocomplete': 'off'
            })
