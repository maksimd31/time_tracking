"""Admin registrations for counters, intervals, and daily summaries."""

from django.contrib import admin

from .models import TimeInterval, DailySummary, TimeCounter


@admin.register(TimeCounter)
class TimeCounterAdmin(admin.ModelAdmin):
    """Expose core counter fields for quick administration."""
    list_display = ('name', 'user', 'created_at', 'updated_at')
    search_fields = ('name', 'user__username')
    list_filter = ('user',)


@admin.register(TimeInterval)
class IntervalFieldValueInline(admin.ModelAdmin):
    """Read-only listing of recorded intervals."""
    list_display = ('user', 'start_time', 'end_time', 'duration', 'break_duration', 'date_create')


@admin.register(DailySummary)
class DailySummaryAdmin(admin.ModelAdmin):
    """Allow staff to inspect aggregated daily totals."""
    list_display = ('user', 'date', 'interval_count', 'total_time', 'date_create')
