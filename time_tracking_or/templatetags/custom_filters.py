"""Custom template filters for formatting durations and helper lookups."""

from datetime import timedelta

from django import template
from django.utils import timezone
from django.utils.safestring import mark_safe
from pytils.dt import ru_strftime

register = template.Library()


@register.filter
def format_time(value):
    """Return a localized string describing a `datetime.time` value."""
    if value is None:
        return "Время не задано"

    hours = value.hour
    minutes = str(value.minute).zfill(2)
    seconds = str(value.second).zfill(2)

    return f"{hours} ч {minutes} мин {seconds} сек"


@register.filter
def duration_format(duration):
    """Convert `timedelta` or `HH:MM:SS` string into readable text."""
    if isinstance(duration, str):
        parts = duration.split(':')
        if len(parts) == 3:
            hours, minutes, seconds = map(int, parts)
            duration = timedelta(hours=hours, minutes=minutes, seconds=seconds)
        else:
            return  "Неверный формат времени"


    if isinstance(duration, timedelta):
        total_seconds = int(duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours} ч {str(minutes).zfill(2)} мин {str(seconds).zfill(2)} секунд"

    return "Неверный формат времени"




@register.filter
def get_summary_interval_count(daily_summaries, selected_date):
    """Return interval count for the summary matching the selected day."""
    if not hasattr(daily_summaries, 'filter'):  # Проверяем, поддерживает ли объект метод filter
        return "Нет данных"

    summary = daily_summaries.filter(date=selected_date).first()
    if summary:
        return summary.interval_count

    return "Нет данных"


@register.filter
def get_summary_total_time(daily_summaries, selected_date):
    """Return formatted total time for the provided day if present."""
    summary = daily_summaries.filter(date=selected_date).first()
    if summary:
        return duration_format(summary.total_time)

    return "Нет данных"


@register.filter
def ru_date(value, fmt="%d %B %Y"):
    """Render a Python date/datetime using Russian month names."""
    if not value:
        return ""
    try:
        return ru_strftime(fmt, value)
    except Exception:
        return value


@register.filter
def get_item(mapping, key):
    """Safe dict lookup that avoids template errors when key missing."""
    if isinstance(mapping, dict):
        return mapping.get(key)
    return None


@register.filter
def duration_seconds(duration):
    """Return duration in whole seconds handling both strings and timedeltas."""
    if isinstance(duration, timedelta):
        return int(duration.total_seconds())
    try:
        hours, minutes, seconds = map(int, str(duration).split(':'))
        return hours * 3600 + minutes * 60 + seconds
    except Exception:
        return 0


@register.filter
def wrap_long_name(value, chunk_size=10):
    """Вставляет перенос строки через каждые chunk_size символов."""
    if not value:
        return ""
    try:
        chunk = int(chunk_size)
    except (TypeError, ValueError):
        chunk = 10
    if chunk <= 0:
        chunk = 10
    if len(value) <= chunk:
        return value
    parts = [value[i:i + chunk] for i in range(0, len(value), chunk)]
    return mark_safe('<wbr>'.join(parts))



#
# @register.filter
# def get_field_value(obj, field):
#     return getattr(obj, field)

# # time_tracking_or/templatetags/custom_filters.py
# from django import template
#
# register = template.Library()
#
# @register.filter
# def duration_format(value):
#     # value — это timedelta
#     if not value:
#         return "00:00:00"
#     total_seconds = int(value.total_seconds())
#     hours = total_seconds // 3600
#     minutes = (total_seconds % 3600) // 60
#     seconds = total_seconds % 60
#     return f"{hours:02}:{minutes:02}:{seconds:02}"
