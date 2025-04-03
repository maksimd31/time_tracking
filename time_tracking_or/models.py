from django.db import models
from django.contrib.auth.models import User
from datetime import datetime, timedelta
from django.utils import timezone


class TimeInterval(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE, related_name='time_intervals')
    start_time = models.TimeField(null=True, blank=True, verbose_name='старт')
    end_time = models.TimeField(null=True, blank=True, verbose_name='стоп')
    duration = models.DurationField(null=True, blank=True, verbose_name='Длительность')
    break_duration = models.DurationField(null=True, blank=True, verbose_name='Перерыв')
    date_create = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.start_time and self.end_time:
            self.duration = (datetime.combine(datetime.min, self.end_time) -
                             datetime.combine(datetime.min, self.start_time))
        super().save(*args, **kwargs)


class DailySummary(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    date = models.DateField()
    interval_count = models.PositiveIntegerField(default=0, verbose_name='Количество интервалов')
    total_time = models.DurationField(default=timezone.timedelta(), verbose_name='Общее время')
    date_create = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    # intervals = models.ManyToManyField(TimeInterval, related_name='daily_summaries')


    def __str__(self):
        return f"{self.date} - {self.user.username}"

