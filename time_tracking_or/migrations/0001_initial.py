# Generated by Django 5.1.7 on 2025-04-01 16:27

import datetime
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DailySummary',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('interval_count', models.PositiveIntegerField(default=0, verbose_name='Количество интервалов')),
                ('total_time', models.DurationField(default=datetime.timedelta(0), verbose_name='Общее время')),
                ('date_create', models.DateTimeField(auto_now_add=True, null=True)),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='TimeInterval',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_time', models.TimeField(blank=True, null=True, verbose_name='старт')),
                ('end_time', models.TimeField(blank=True, null=True, verbose_name='стоп')),
                ('duration', models.DurationField(blank=True, null=True, verbose_name='Длительность')),
                ('break_duration', models.DurationField(blank=True, null=True, verbose_name='Перерыв')),
                ('date_create', models.DateTimeField(auto_now_add=True, null=True)),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='time_intervals', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
