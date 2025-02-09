from django import template
from django.utils import timezone
from datetime import timedelta
import pytz


register = template.Library()


@register.filter
def format_time(value):
    if value is None:
        return "Время не задано"

    hours = value.hour
    minutes = str(value.minute).zfill(2)
    seconds = str(value.second).zfill(2)

    return f"{hours} ч {minutes} мин {seconds} сек"


@register.filter
def duration_format(duration):
    if isinstance(duration, str):
        parts = duration.split(':')
        if len(parts) == 3:
            hours, minutes, seconds = map(int, parts)
            duration = timedelta(hours=hours, minutes=minutes, seconds=seconds)
        else:
            return "00:00:00"

    if isinstance(duration, timedelta):
        total_seconds = int(duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours} ч {str(minutes).zfill(2)} мин {str(seconds).zfill(2)} секунд"

    return "00:00:00"
