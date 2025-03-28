from django.db import models
from django.contrib.auth.models import User
from datetime import datetime, timedelta



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
