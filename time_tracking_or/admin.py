from django.contrib import admin

# Register your models here.
from .models import TimeInterval, DailySummary, TimeCounter


@admin.register(TimeCounter)
class TimeCounterAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'created_at', 'updated_at')
    search_fields = ('name', 'user__username')
    list_filter = ('user',)


@admin.register(TimeInterval)
class IntervalFieldValueInline(admin.ModelAdmin):
    list_display = ('user', 'start_time', 'end_time', 'duration', 'break_duration', 'date_create')

@admin.register(DailySummary)
class DailySummaryAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'interval_count', 'total_time', 'date_create')
