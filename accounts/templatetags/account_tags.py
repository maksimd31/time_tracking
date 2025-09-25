from django import template

from accounts.models import Profile

register = template.Library()


@register.simple_tag
def user_profile(user):
    """Возвращает словарь с профилем и безопасным URL аватара."""
    if not user or not getattr(user, 'is_authenticated', False):
        return {'profile': None, 'avatar_url': None, 'initial': 'U'}
    try:
        profile = user.profile
    except Profile.DoesNotExist:  # pragma: no cover - защита от отсутствия профиля
        profile = None

    avatar_url = None
    if profile:
        avatar_field = getattr(profile, 'avatar', None)
        if avatar_field:
            try:
                avatar_url = avatar_field.url
            except (ValueError, AttributeError):  # файл отсутствует или storage не настроен
                avatar_url = None

    initial = (user.get_full_name() or user.username or '').strip()[:1].upper() or 'U'

    return {
        'profile': profile,
        'avatar_url': avatar_url,
        'initial': initial,
    }
