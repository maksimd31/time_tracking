
from django.forms import ModelForm, CharField, TextInput

from .models import TimeInterval

class TimeIntervalFormEdit(ModelForm):  # Форма для редактирования модели TimeInterval
    class Meta:  # Вложенный класс с метаданными формы
        model = TimeInterval  # Указываем связанную модель
        fields = ['start_time', 'end_time' ]  # Поля, которые будут в форме
        widgets = {  # Виджеты для отображения полей
            'start_time': TextInput(attrs={'type': 'time'}),  # Поле ввода времени для старта
            'end_time': TextInput(attrs={'type': 'time'}),    # Поле ввода времени для окончания
        }

    def __init__(self, *args, **kwargs):  # Конструктор формы
        super().__init__(*args, **kwargs)  # Вызов конструктора родителя
        self.fields['start_time'].label = 'Старт'  # Установка метки для поля старта
        self.fields['end_time'].label = 'Стоп'     # Установка метки для поля окончания
        self.fields['break_duration'].label = 'Перерыв'  # Установка метки для поля перерыва