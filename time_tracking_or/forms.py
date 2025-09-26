"""Forms for counters and intervals with custom widgets and validation."""

from django.forms import ModelForm, TextInput, TimeInput
from django import forms
from .models import TimeInterval, TimeCounter


class TimeCounterForm(forms.ModelForm):
    """Bind name/color fields for creating or editing a counter."""
    class Meta:
        model = TimeCounter
        fields = ['name', 'color']
        widgets = {
            'name': TextInput(attrs={'class': 'form-control', 'placeholder': 'Название счетчика'}),
            'color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
        }

class TimeIntervalFormEdit(ModelForm):
    """Edit existing intervals with basic temporal validation."""
    class Meta:
        model = TimeInterval
        fields = ['day', 'start_time', 'end_time']
        widgets = {
            'day': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'start_time': TimeInput(format='%H:%M', attrs={'type': 'time', 'class': 'form-control', 'step': '1'}),
            'end_time': TimeInput(format='%H:%M', attrs={'type': 'time', 'class': 'form-control', 'step': '1'}),
        }

    def __init__(self, *args, **kwargs):
        """Adjust labels and hide the immutable day field for edits."""
        super().__init__(*args, **kwargs)
        self.fields['day'].label = 'Дата'
        self.fields['start_time'].label = 'Старт'
        self.fields['end_time'].label = 'Стоп'
        # Если поле break_duration не используется в форме, не добавлять label
        if 'break_duration' in self.fields:
            self.fields['break_duration'].label = 'Перерыв'
        if self.instance and self.instance.pk:
            self.fields['day'].widget = forms.HiddenInput()

    def clean(self):
        """Validate that the end time is not before the start time."""
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        # Проверяем, что оба времени заданы и оба типа time
        if start_time is not None and end_time is not None:
            if isinstance(start_time, str):
                from datetime import time
                start_time = time.fromisoformat(start_time)
            if isinstance(end_time, str):
                from datetime import time
                end_time = time.fromisoformat(end_time)
            if end_time < start_time:
                self.add_error('end_time', 'Время окончания не может быть раньше времени начала!')
                # Добавим общее сообщение формы
                from django.core.exceptions import ValidationError
                raise ValidationError('Время окончания не может быть раньше времени начала!')
        return cleaned_data
