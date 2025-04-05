from accounts.models import Profile
from django.contrib import admin

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """
    Админ-панель модели профиля
    """
    list_display = ('user', 'slug')

    list_display_links = ('user', 'slug')
    search_fields = ('user__username', 'slug')


