"""Shared utility helpers used across multiple apps."""

from uuid import uuid4

from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from pytils.translit import slugify

from time_tracking_or.models import DailySummary


def unique_slugify(instance, slug, slug_field):
    """
    Генератор уникальных SLUG для моделей, в случае существования такого SLUG.
    """
    model = instance.__class__
    unique_slug = slug_field
    if not slug_field:
        unique_slug = slugify(slug)
    elif model.objects.filter(slug=slug_field).exclude(id=instance.id).exists():
        unique_slug = f'{slugify(slug)}-{uuid4().hex[:8]}'
    return unique_slug


class FormStyleMixin:
    """
    Миксин для добавления стилей ко всем полям формы.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'form-control',
                'autocomplete': 'off'
            })


class PlaceholderAndStyleMixin:
    """
    Миксин для автоматического добавления плейсхолдеров и стилей полям формы.
    """
    placeholders = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name in self.placeholders:
                field.widget.attrs.update({
                    'placeholder': self.placeholders[field_name]
                })
            # Общие атрибуты для всех полей
            field.widget.attrs.update({
                'class': 'form-control',
                'autocomplete': 'off'
            })


class RememberMeMixin:
    """
    Миксин для автоматической настройки поля 'remember_me' в форме.
    """
    remember_me_field = {
        'required': False,
        'label': 'Запомнить меня',
        'widget': forms.CheckboxInput(attrs={'class': 'form-check-input'})
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Автоматически добавляем поле 'remember_me'
        self.fields['remember_me'] = forms.BooleanField(**self.remember_me_field)

    def process_remember_me(self, cleaned_data):
        """
        Метод для обработки значения 'remember_me'.
        """
        return cleaned_data.get('remember_me', False)



class DailySummaryMixin(LoginRequiredMixin):
    def get_daily_summaries(self):
        return DailySummary.objects.filter(user=self.request.user).order_by('date')
