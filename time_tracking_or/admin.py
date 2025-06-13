from django.contrib import admin

# Register your models here.
from .models import TimeInterval, DailySummary


@admin.register(TimeInterval)
class IntervalFieldValueInline(admin.ModelAdmin):
    list_display = ('user', 'start_time', 'end_time', 'duration', 'break_duration', 'date_create')

@admin.register(DailySummary)
class DailySummaryAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'interval_count', 'total_time', 'date_create')
