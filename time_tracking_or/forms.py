from django.forms import ModelForm, TextInput
from django import forms
from .models import TimeInterval

class TimeIntervalFormEdit(ModelForm):
    class Meta:
        model = TimeInterval
        fields = ['start_time', 'end_time']
        widgets = {
            'start_time': TextInput(attrs={'type': 'time'}),
            'end_time': TextInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['start_time'].label = 'Старт'
        self.fields['end_time'].label = 'Стоп'
        # Если поле break_duration не используется в форме, не добавлять label
        if 'break_duration' in self.fields:
            self.fields['break_duration'].label = 'Перерыв'

    def clean(self):
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

