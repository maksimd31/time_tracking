import pytest
from datetime import timedelta, time, datetime
from django.template import Context, Template
from django.contrib.auth.models import AnonymousUser, User
from accounts.templatetags.account_tags import user_profile
from time_tracking_or.templatetags import chart_tags, custom_filters

@pytest.mark.django_db
def test_user_profile_anonymous():
    anon = AnonymousUser()
    data = user_profile(anon)
    assert data['profile'] is None
    assert data['initial'] == 'U'

@pytest.mark.django_db
def test_user_profile_initial(user):
    data = user_profile(user)
    assert data['profile'] == user.profile
    assert data['initial'] == 'T'

@pytest.mark.parametrize('sequence,pos,expected', [([1,2,3],1,2), ('abc',2,'c'), (None,0,None)])
def test_chart_index(sequence,pos,expected):
    assert chart_tags.index(sequence,pos) == expected

@pytest.mark.parametrize('value,maxv,expected', [(50,100,50.0),(0,0,0),(5,0,0),('x',10,0)])
def test_chart_percent_of(value,maxv,expected):
    assert chart_tags.percent_of(value,maxv) == expected

@pytest.mark.parametrize('value,total,expected', [(25,100,25.0),(0,0,0),(5,'x',0)])
def test_chart_percent_total(value,total,expected):
    assert chart_tags.percent_of_total(value,total) == expected

@pytest.mark.parametrize('val,expected', [
    (time(9,5,7), '9 ч 05 мин 07 сек'),
    (None, 'Время не задано')
])
def test_format_time(val, expected):
    assert custom_filters.format_time(val) == expected

@pytest.mark.parametrize('val,expected', [
    (timedelta(hours=1, minutes=2, seconds=3), '1 ч 02 мин 03 секунд'),
    ('01:02:03','1 ч 02 мин 03 секунд'),
    ('bad', 'Неверный формат времени')
])
def test_duration_format(val, expected):
    assert custom_filters.duration_format(val) == expected

@pytest.mark.parametrize('dur,expected', [
    (timedelta(seconds=3661), 3661),
    ('01:01:01', 3661),
    ('bad', 0)
])
def test_duration_seconds(dur, expected):
    assert custom_filters.duration_seconds(dur) == expected

@pytest.mark.parametrize('value,chunk,res', [
    ('short', 10, 'short'),
    ('averyverylongname', 5, 'avery<wbr>veryl<wbr>ongna<wbr>me'),
])
def test_wrap_long_name(value, chunk, res):
    out = custom_filters.wrap_long_name(value, chunk)
    assert out.replace('\n','') == res

@pytest.mark.parametrize('mapping,key,expected', [({'a':1},'a',1), ({},'x',None), ('notdict','k',None)])
def test_get_item(mapping,key,expected):
    assert custom_filters.get_item(mapping,key) == expected

@pytest.mark.django_db
def test_get_summary_filters(user, django_assert_num_queries):
    from time_tracking_or.models import DailySummary
    today = datetime.today().date()
    ds = DailySummary.objects.create(user=user, date=today, interval_count=2, total_time=timedelta(hours=1))
    qs = DailySummary.objects.filter(user=user)
    assert custom_filters.get_summary_interval_count(qs, today) == 2
    assert '1 ч' in custom_filters.get_summary_total_time(qs, today)

@pytest.mark.parametrize('val', [None, datetime.now()])
def test_ru_date_no_error(val):
    custom_filters.ru_date(val)

