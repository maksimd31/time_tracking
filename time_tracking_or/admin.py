"""Admin registrations for counters, intervals, and daily summaries."""

from django.contrib import admin

from .models import DailySummary, ProjectRating, TimeCounter, TimeInterval


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


@admin.register(ProjectRating)
class ProjectRatingAdmin(admin.ModelAdmin):
    """Manage project ratings and feedback."""
    list_display = ('user', 'rating', 'email_sent', 'email_sent_at', 'created_at', 'updated_at')
    list_filter = ('rating', 'email_sent', 'created_at', 'email_sent_at')
    search_fields = ('user__username', 'comment')
    readonly_fields = ('created_at', 'updated_at', 'email_sent_at')
    
    fieldsets = (
        (None, {
            'fields': ('user', 'rating', 'comment')
        }),
        ('Отправка на email', {
            'fields': ('email_sent', 'email_sent_at', 'celery_task_id'),
            'classes': ('collapse',)
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Order by most recent ratings."""
        return super().get_queryset(request).order_by('-created_at')
