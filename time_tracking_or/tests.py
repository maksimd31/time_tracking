from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import TimeCounter, TimeInterval


class HomeAnonymousViewTest(TestCase):
    def test_home_prompts_registration_for_anonymous_user(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'time_tracking_main/welcome.html')
        self.assertContains(response, reverse('register'))


class CounterViewsTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='demo', password='pass12345')
        self.client.force_login(self.user)
        self.counter_primary = TimeCounter.objects.create(user=self.user, name='Работа')
        self.counter_secondary = TimeCounter.objects.create(user=self.user, name='Учеба')

    def test_start_counter_creates_active_interval(self):
        response = self.client.post(reverse('counter_start', args=[self.counter_primary.pk]), follow=True)
        self.assertEqual(response.status_code, 200)
        interval = TimeInterval.objects.filter(counter=self.counter_primary, end_time__isnull=True).first()
        self.assertIsNotNone(interval)
        self.assertEqual(interval.user, self.user)
        self.assertEqual(interval.counter, self.counter_primary)

    def test_cannot_start_second_counter_while_first_is_active(self):
        self.client.post(reverse('counter_start', args=[self.counter_primary.pk]))
        response = self.client.post(reverse('counter_start', args=[self.counter_secondary.pk]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(TimeInterval.objects.filter(counter=self.counter_secondary).exists())
        active_primary = TimeInterval.objects.filter(counter=self.counter_primary, end_time__isnull=True).count()
        self.assertEqual(active_primary, 1)

    def test_stop_counter_sets_duration(self):
        self.client.post(reverse('counter_start', args=[self.counter_primary.pk]))
        interval = TimeInterval.objects.get(counter=self.counter_primary, end_time__isnull=True)
        interval.start_time = (timezone.localtime() - timedelta(minutes=30)).time()
        interval.save(update_fields=['start_time'])
        response = self.client.post(reverse('counter_stop', args=[self.counter_primary.pk]), follow=True)
        self.assertEqual(response.status_code, 200)
        interval.refresh_from_db()
        self.assertIsNotNone(interval.end_time)
        self.assertIsNotNone(interval.duration)
        self.assertGreaterEqual(interval.duration, timedelta(minutes=29))
