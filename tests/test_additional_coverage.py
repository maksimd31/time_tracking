import pytest
from django.urls import reverse
from django.utils import timezone
from datetime import time, timedelta, date
from time_tracking_or.models import TimeInterval, TimeCounter
from django.contrib.auth.models import User

@pytest.mark.django_db
def test_timecounter_update_delete(auth_client, counter):
    # update
    resp = auth_client.post(reverse('counter_update', args=[counter.id]), {'name': 'WorkRenamed', 'color': '#abcdef'})
    assert resp.status_code in (302, 200)
    counter.refresh_from_db()
    assert counter.name == 'WorkRenamed'
    # delete
    resp2 = auth_client.post(reverse('counter_delete', args=[counter.id]), follow=True)
    assert resp2.status_code == 200
    assert not TimeCounter.objects.filter(id=counter.id).exists()

@pytest.mark.django_db
def test_interval_delete_standard(auth_client, counter):
    ti = TimeInterval.objects.create(counter=counter, user=counter.user, day=timezone.localdate(), start_time=time(8), end_time=time(9))
    resp = auth_client.post(reverse('interval_delete', args=[ti.id]), follow=True)
    assert resp.status_code == 200
    assert not TimeInterval.objects.filter(id=ti.id).exists()

@pytest.mark.django_db
def test_history_invalid_dates(auth_client, counter):
    url = reverse('counter_history', args=[counter.id]) + '?start=bad&end=also-bad'
    resp = auth_client.get(url)
    assert resp.status_code == 200
    assert resp.context['filter_start'] is None
    assert resp.context['filter_end'] is None

@pytest.mark.django_db
def test_interval_detail_view(auth_client, counter):
    ti = TimeInterval.objects.create(counter=counter, user=counter.user, day=timezone.localdate(), start_time=time(7), end_time=time(8))
    resp = auth_client.get(reverse('interval_detail', args=[ti.id]))
    assert resp.status_code == 200
    assert resp.context['interval'].id == ti.id

@pytest.mark.django_db
def test_asgi_wsgi_import():
    # простое импортирование для покрытия
    import Time_tracking.asgi  # noqa
    import Time_tracking.wsgi  # noqa

@pytest.mark.django_db
def test_dashboard_hx_no_intervals(auth_client):
    resp = auth_client.get(reverse('home'), **{"HTTP_HX-Request": "true"})
    assert resp.status_code == 200

@pytest.mark.django_db
def test_start_second_counter_hx(auth_client, counter):
    # start first
    auth_client.post(reverse('counter_start', args=[counter.id]))
    c2 = TimeCounter.objects.create(user=counter.user, name='Another', color='#111111')
    resp = auth_client.post(reverse('counter_start', args=[c2.id]), **{"HTTP_HX-Request": "true"})
    assert resp.status_code in (200, 302)

@pytest.mark.django_db
def test_history_hx_active_interval(auth_client, counter):
    # start interval so it's active
    auth_client.post(reverse('counter_start', args=[counter.id]))
    # Create 11 finished intervals to trigger pagination + active interval for active_total calc
    for i in range(11):
        TimeInterval.objects.create(counter=counter, user=counter.user, day=timezone.localdate(), start_time=time(1,0,0), end_time=time(2,0,0))
    resp = auth_client.post(reverse('counter_start', args=[counter.id]), {'history': '1', 'page': 'bad'}, **{"HTTP_HX-Request": "true"})
    # This will attempt to start while one running -> message + hx dashboard history or dashboard update
    # Now pause with history hx to get history branch with active interval present
    resp2 = auth_client.post(reverse('counter_pause', args=[counter.id]), {'history': '1'}, **{"HTTP_HX-Request": "true"})
    assert resp2.status_code == 200
    content = resp2.content.decode('utf-8')
    assert 'history-intervals' in content

@pytest.mark.django_db
def test_interval_update_hx_with_filters(auth_client, counter):
    ti = TimeInterval.objects.create(counter=counter, user=counter.user, day=timezone.localdate(), start_time=time(9), end_time=time(10))
    url = reverse('interval_update', args=[ti.id])
    resp = auth_client.post(url + '?mode=edit', {
        'day': timezone.localdate(),
        'start_time': '09:00:00',
        'end_time': '09:30:00',
        'num': '5',
        'start': 'bad-date',
        'end': 'also-bad'
    }, **{"HTTP_HX-Request": "true"})
    assert resp.status_code == 200

@pytest.mark.django_db
def test_delete_interval_htmx_with_filters(auth_client, counter):
    ti = TimeInterval.objects.create(counter=counter, user=counter.user, day=timezone.localdate(), start_time=time(9), end_time=time(10))
    resp = auth_client.delete(reverse('interval_delite_htmx', args=[ti.id]) + f'?start={timezone.localdate()}&end={timezone.localdate()}', **{"HTTP_HX-Request": "true"})
    assert resp.status_code == 200

@pytest.mark.django_db
def test_password_change_flow(auth_client, user):
    url = reverse('password_change')
    resp = auth_client.post(url, {
        'old_password': 'pass12345',
        'new_password1': 'NewStrongPass123',
        'new_password2': 'NewStrongPass123'
    })
    assert resp.status_code in (302, 200)
    # re-login with new password
    from django.contrib.auth import authenticate
    u = authenticate(username='tester', password='NewStrongPass123')
    assert u is not None

