"""Database models for counters, intervals, and daily summaries."""

from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

class TimeCounter(models.Model):
    """A named timer that groups time intervals for a user."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='time_counters')
    name = models.CharField(max_length=255, verbose_name='Название')
    slug = models.SlugField(max_length=255, blank=True, verbose_name='URL')
    color = models.CharField(max_length=7, default='#4e79a7', verbose_name='Цвет')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'slug')
        ordering = ('name',)
        verbose_name = 'Счетчик'
        verbose_name_plural = 'Счетчики'

    def __str__(self):
        """Return human readable representation with owner."""
        return f"{self.name} ({self.user.username})"

    def save(self, *args, **kwargs):
        """Auto-generate slug for new counters and persist changes."""
        if not self.slug:
            from services.utils import unique_slugify
            self.slug = unique_slugify(self, self.name, self.slug)
        super().save(*args, **kwargs)

    @property
    def is_running(self):
        """Return whether the counter currently has an open interval."""
        return self.intervals.filter(end_time__isnull=True).exists()


class TimeInterval(models.Model):
    """Concrete slice of time recorded under a counter."""
    counter = models.ForeignKey(TimeCounter, on_delete=models.CASCADE, related_name='intervals', null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='time_intervals', null=True, blank=True)
    day = models.DateField(default=timezone.localdate, verbose_name='День')
    start_time = models.TimeField(null=True, blank=True, verbose_name='старт')
    end_time = models.TimeField(null=True, blank=True, verbose_name='стоп')
    duration = models.DurationField(null=True, blank=True, verbose_name='Длительность')
    break_duration = models.DurationField(null=True, blank=True, verbose_name='Перерыв')
    date_create = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        ordering = ('-day', '-date_create')
        verbose_name = 'Интервал'
        verbose_name_plural = 'Интервалы'

    def save(self, *args, **kwargs):
        """Normalize ownership data and recalculate duration before saving."""
        if not self.counter_id:
            raise ValueError('Counter must be set for TimeInterval')
        if self.counter_id and self.user_id != self.counter.user_id:
            self.user = self.counter.user
        if not self.day:
            self.day = timezone.localdate()
        if self.start_time and self.end_time:
            start_dt = datetime.combine(datetime.min, self.start_time)
            end_dt = datetime.combine(datetime.min, self.end_time)
            if end_dt < start_dt:
                end_dt += timedelta(days=1)
            self.duration = end_dt - start_dt
        super().save(*args, **kwargs)

    @property
    def updated(self):  # для sitemap
        return self.date_create

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('interval_detail', kwargs={'pk': self.pk})


class DailySummary(models.Model):
    """Denormalized daily totals for quick dashboard access."""
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    date = models.DateField()
    interval_count = models.PositiveIntegerField(default=0, verbose_name='Количество интервалов')
    total_time = models.DurationField(default=timedelta, verbose_name='Общее время')
    date_create = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        unique_together = ('user', 'date')
        ordering = ('-date',)
        verbose_name = 'Суточный итог'
        verbose_name_plural = 'Суточные итоги'

    def __str__(self):
        """Display the day and username for admin lists."""
        return f"{self.date} - {self.user.username}"
