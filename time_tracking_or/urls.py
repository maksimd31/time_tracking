from django.urls import path
from .views import (
    TimeIntervalView, StartIntervalView, StopIntervalView, DailySummaryView, AddManualIntervalView, DeleteIntervalView,
    UpdateIntervalView, IntervalDeteil, IntervalDetailNew, IntervalRowHtmxView,
    DeleteIntervalViewHTMX)

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
    path('interval_detail_new/<int:pk>/', IntervalDetailNew.as_view(), name='interval_detail_new'),
    # path('time-interval/reset/', ResetIntervalsView.as_view(), name='reset_intervals'),
    path('interval/<int:pk>/row/', IntervalRowHtmxView.as_view(), name='interval_row_htmx'),
    path('interval/<int:pk>/delete/', DeleteIntervalViewHTMX.as_view(), name='interval_delite_htmx'),

]
