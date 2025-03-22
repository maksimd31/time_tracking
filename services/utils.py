from uuid import uuid4
from pytils.translit import slugify


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
