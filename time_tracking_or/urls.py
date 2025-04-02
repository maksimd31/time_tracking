from django.urls import path
from . import views
from django.urls import path
from .views import (
    TimeIntervalView, StartIntervalView, StopIntervalView, DailySummaryView)
# from crm_car_wash.new_time_register import views

urlpatterns = [
    path('', views.IndexView.as_view(), name='home'),
    path('time-interval/', TimeIntervalView.as_view(), name='time_interval_view'),
    path('time-interval/start/', StartIntervalView.as_view(), name='start_interval'),
    path('time-interval/stop/', StopIntervalView.as_view(), name='stop_interval'),
    path('daily-summary/', DailySummaryView.as_view(), name='daily_summary_view'),


    # path('time-interval/reset/', ResetIntervalsView.as_view(), name='reset_intervals'),
    # path('time-interval/delete-summary/', DeleteSummaryView.as_view(), name='delete_summary'),
    # path('time-interval/add-manual/', AddManualIntervalView.as_view(), name='add_manual_interval'),
    # path('intervals/<str:date>/', IntervalsForDateView.as_view(), name='intervals_for_date'),

]
