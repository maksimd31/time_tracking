"""Helper filters used by chart widgets in dashboard templates."""

from django import template

register = template.Library()


@register.filter
def index(sequence, position):
    """Return item at index `position` or `None` if out of range."""
    try:
        return sequence[position]
    except (IndexError, TypeError):
        return None


@register.filter
def percent_of(value, max_value):
    """Compute percent of max value guarding against zero division."""
    try:
        value = float(value)
        max_value = float(max_value)
        if max_value <= 0:
            return 0
        percent = (value / max_value) * 100
        return round(percent, 2)
    except (TypeError, ValueError, ZeroDivisionError):
        return 0


@register.filter
def percent_of_total(value, total):
    """Compute percent of total value, returning zero on invalid input."""
    try:
        value = float(value)
        total = float(total)
        if total <= 0:
            return 0
        percent = (value / total) * 100
        return round(percent, 2)
    except (TypeError, ValueError, ZeroDivisionError):
        return 0
