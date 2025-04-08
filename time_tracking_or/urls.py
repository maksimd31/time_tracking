from django.urls import path
from .views import (
    TimeIntervalView, StartIntervalView, StopIntervalView, DailySummaryView, AddManualIntervalView, DeleteIntervalView,
    UpdateIntervalView, IntervalDeteil)

urlpatterns = [
    # path('', views.IndexView.as_view(), name='home'),
    path('', TimeIntervalView.as_view(), name='home'),
    path('time-interval/start/', StartIntervalView.as_view(), name='start_interval'),
    path('time-interval/stop/', StopIntervalView.as_view(), name='stop_interval'),
    path('daily-summary/', DailySummaryView.as_view(), name='daily_summary_view'),
    path('add_manual_interval/', AddManualIntervalView.as_view(), name='add_manual_interval'),
    path('delete_interval/<int:pk>/', DeleteIntervalView.as_view(), name='delete_interval'),
    path('interval/<int:pk>/update/', UpdateIntervalView.as_view(), name='update_interval'),

    path('interval_detail/<int:pk>/', IntervalDeteil.as_view(), name='interval_detail'),

    # path('time-interval/reset/', ResetIntervalsView.as_view(), name='reset_intervals'),
    # path('time-interval/delete-summary/', DeleteSummaryView.as_view(), name='delete_summary'),
    # path('time-interval/add-manual/', AddManualIntervalView.as_view(), name='add_manual_interval'),
    # path('intervals/<str:date>/', IntervalsForDateView.as_view(), name='intervals_for_date'),

]
