# Generated by Django 5.1.6 on 2025-02-09 13:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('time_tracking_main', '0002_alter_timeinterval_duration'),
    ]

    operations = [
        migrations.AlterField(
            model_name='timeinterval',
            name='duration',
            field=models.DurationField(blank=True, null=True, verbose_name='Длительность'),
        ),
    ]
