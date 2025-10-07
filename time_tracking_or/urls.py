"""URL configuration for counter dashboards and interval endpoints."""

from django.urls import path

from .views import (
    CheckTaskStatusView,
    CounterHistoryView,
    CounterIntervalDeleteView,
    CounterIntervalUpdateView,
    CounterManualIntervalCreateView,
    CounterPauseView,
    CounterStartView,
    CounterStopView,
    CounterSummaryView,
    DeleteIntervalViewHTMX,
    IntervalDetailView,
    ProjectRatingView,
    SendFeedbackView,
    TimeCounterCreateView,
    TimeCounterDeleteView,
    TimeCounterListView,
    TimeCounterUpdateView,
)

urlpatterns = [
    path('', TimeCounterListView.as_view(), name='home'),
    path('counters/create/', TimeCounterCreateView.as_view(), name='counter_create'),
    path('counters/<int:pk>/update/', TimeCounterUpdateView.as_view(), name='counter_update'),
    path('counters/<int:pk>/delete/', TimeCounterDeleteView.as_view(), name='counter_delete'),
    path('counters/<int:pk>/start/', CounterStartView.as_view(), name='counter_start'),
    path('counters/<int:pk>/pause/', CounterPauseView.as_view(), name='counter_pause'),
    path('counters/<int:pk>/stop/', CounterStopView.as_view(), name='counter_stop'),
    path('counters/<int:pk>/history/', CounterHistoryView.as_view(), name='counter_history'),
    path('counters/<int:pk>/manual/', CounterManualIntervalCreateView.as_view(), name='counter_manual_interval'),
    path('summary/', CounterSummaryView.as_view(), name='counter_summary'),
    path('intervals/<int:pk>/update/', CounterIntervalUpdateView.as_view(), name='interval_update'),
    path('intervals/<int:pk>/delete/', CounterIntervalDeleteView.as_view(), name='interval_delete'),
    path('interval/<int:pk>/delete/', DeleteIntervalViewHTMX.as_view(), name='interval_delite_htmx'),
    path('intervals/<int:pk>/', IntervalDetailView.as_view(), name='interval_detail'),
    path('project/rating/', ProjectRatingView.as_view(), name='project_rating'),
    path('project/feedback/', SendFeedbackView.as_view(), name='send_feedback'),
    # Новый эндпоинт для проверки статуса Celery задачи отправки фидбэка
    path('project/task-status/<str:task_id>/', CheckTaskStatusView.as_view(), name='task_status'),
]
