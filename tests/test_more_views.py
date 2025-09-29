import pytest
from django.urls import reverse
from django.utils import timezone
from datetime import time, timedelta
from time_tracking_or.models import TimeCounter, TimeInterval
from django.contrib.auth.models import User
from services.utils import unique_slugify
from django.core import mail
from accounts.tasks import send_welcome_email

@pytest.mark.django_db
def test_dashboard_htmx_partial(auth_client, counter):
    # create another counter with data
    c2 = TimeCounter.objects.create(user=counter.user, name='Study', color='#000000')
    TimeInterval.objects.create(counter=counter, user=counter.user, day=timezone.localdate(), start_time=time(9), end_time=time(10))
    TimeInterval.objects.create(counter=c2, user=counter.user, day=timezone.localdate(), start_time=time(11), end_time=time(12,30))
    resp = auth_client.get(reverse('home'), **{"HTTP_HX-Request": "true"})
    assert resp.status_code == 200
    assert 'chart_labels' in resp.context

@pytest.mark.django_db
def test_history_hx_pause_flow(auth_client, counter):
    # start active interval
    auth_client.post(reverse('counter_start', args=[counter.id]))
    # pause with hx and history -> triggers hx_response history branch
    resp = auth_client.post(reverse('counter_pause', args=[counter.id]), {'history': '1'}, **{"HTTP_HX-Request": "true"})
    assert resp.status_code == 200
    # response should contain table container id
    assert "history-intervals" in resp.content.decode('utf-8')

@pytest.mark.django_db
def test_stop_hx_flow(auth_client, counter):
    auth_client.post(reverse('counter_start', args=[counter.id]))
    resp = auth_client.post(reverse('counter_stop', args=[counter.id]), {}, **{"HTTP_HX-Request": "true"})
    assert resp.status_code == 200

@pytest.mark.django_db
def test_interval_update_get_display(auth_client, counter):
    ti = TimeInterval.objects.create(counter=counter, user=counter.user, day=timezone.localdate(), start_time=time(9), end_time=time(10))
    url = reverse('interval_update', args=[ti.id]) + '?mode=display'
    resp = auth_client.get(url, **{"HTTP_HX-Request": "true"})
    assert resp.status_code == 200
    assert 'interval' in resp.context

@pytest.mark.django_db
def test_delete_interval_htmx_post(auth_client, counter):
    ti = TimeInterval.objects.create(counter=counter, user=counter.user, day=timezone.localdate(), start_time=time(9), end_time=time(10))
    resp = auth_client.post(reverse('interval_delite_htmx', args=[ti.id]), {'start': timezone.localdate()}, **{"HTTP_HX-Request": "true"})
    assert resp.status_code == 200
    assert '<!--deleted-->' in resp.content.decode('utf-8')

@pytest.mark.django_db
def test_summary_month_period(auth_client, counter):
    today = timezone.localdate()
    first = today.replace(day=1)
    TimeInterval.objects.create(counter=counter, user=counter.user, day=first, start_time=time(9), end_time=time(10))
    resp = auth_client.get(reverse('counter_summary') + '?period=month')
    assert resp.status_code == 200
    assert resp.context['period_key'] == 'month'

@pytest.mark.django_db
def test_selected_date_invalid(auth_client):
    resp = auth_client.get(reverse('home') + '?date=bad-date')
    assert resp.status_code == 200
    # falls back to today; context has selected_date
    assert 'selected_date' in resp.context

@pytest.mark.django_db
def test_unique_slugify_collision(user):
    c1 = TimeCounter.objects.create(user=user, name='Repeat', color='#111111')
    c2 = TimeCounter.objects.create(user=user, name='Repeat', color='#222222')
    assert c1.slug != c2.slug

@pytest.mark.django_db
def test_sitemap_interval(client, user, counter):
    ti = TimeInterval.objects.create(counter=counter, user=user, day=timezone.localdate(), start_time=time(9), end_time=time(9,30))
    resp = client.get('/sitemap.xml')
    assert resp.status_code == 200
    assert ti.get_absolute_url() in resp.content.decode('utf-8')

@pytest.mark.django_db
def test_send_welcome_email_direct(monkeypatch, settings):
    sent = {}
    def fake_send_mail(subject, message, from_email, recipient_list, fail_silently):
        sent['data'] = (subject, message, from_email, tuple(recipient_list))
        return 1
    monkeypatch.setattr('accounts.tasks.send_mail', fake_send_mail)
    send_welcome_email(subject='Hi', message='Body', to_email='x@example.com')
    assert 'data' in sent

@pytest.mark.django_db
def test_send_welcome_email_no_email():
    # should not raise
    send_welcome_email(subject='Hi', message='Body', to_email='')

