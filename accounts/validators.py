from django.core.exceptions import ValidationError
import re


def validate_latin_characters(value):
    if not re.match(r'^[a-zA-Z0-9_]+$', value):
        raise ValidationError('Введите только латинские буквы и цифры, это никнейм')
