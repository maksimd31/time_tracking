from django.shortcuts import render

# Create your views here.
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.timezone import now, make_aware
from datetime import datetime, timedelta
import pytz

from services.utils import DailySummaryMixin
from .models import TimeInterval, DailySummary


class IndexView(LoginRequiredMixin, ListView):
    template_name = 'time_tracking_main/index.html'
    login_url = 'login'

    # context_object_name = 'time_intervals'
    #
    def get_queryset(self):
        return TimeInterval.objects.all()


class DailySummaryView(LoginRequiredMixin, ListView):
    template_name = 'time_tracking_main/daily_summary.html'
    # template_name = 'time_tracking_main/time_interval_new.html'

    login_url = 'login'
    context_object_name = 'daily_summaries'
    paginate_by = 5

    def get_queryset(self):
        return DailySummary.objects.filter(user=self.request.user).order_by('date')


class TimeIntervalView(LoginRequiredMixin, ListView):
    """
    Основное представление для работы с интервалами времени.
    """
    template_name = 'time_tracking_main/time_interval_new.html'
    timezone = pytz.timezone('Europe/Moscow')
    login_url = 'login'
    context_object_name = 'intervals'
    paginate_by = 5

    def get_selected_date(self):
        selected_date_str = self.request.GET.get('date', )
        if not selected_date_str:
            return now().astimezone(self.timezone).date()
        try:
            return datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except ValueError:
            return now().astimezone(self.timezone).date()

    def get_queryset(self):
        selected_date = self.get_selected_date()
        return TimeInterval.objects.filter(user=self.request.user, date_create__date=selected_date)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected_date = self.get_selected_date()
        intervals = self.get_queryset()
        # page_obj = self.paginate_queryset(self.paginate_by)
        formatted_intervals, total_duration = self.format_intervals(intervals)
        self.update_daily_summary(self.request.user, intervals, total_duration)
        daily_summaries = DailySummary.objects.filter(user=self.request.user).order_by('date')
        context.update({
            'formatted_intervals': formatted_intervals,
            'daily_summaries': daily_summaries,
            'selected_date': selected_date,
            # 'intervals': intervals,
            # 'page_obj': page_obj,
        })
        return context

    @staticmethod
    def format_intervals(intervals):
        formatted_intervals = []
        total_duration = timedelta()

        for interval in intervals:
            duration = interval.duration if interval.duration is not None else timedelta(0)
            formatted_intervals.append({
                'start_time': interval.start_time,
                'end_time': interval.end_time,
                'duration': duration,
            })
            total_duration += duration

        return formatted_intervals, total_duration

    @staticmethod
    def update_daily_summary(user, intervals, total_duration):
        today = now().date()
        daily_summary, created = DailySummary.objects.get_or_create(user=user, date=today)
        daily_summary.interval_count = intervals.count()
        daily_summary.total_time = total_duration
        daily_summary.save()



class StartIntervalView(CreateView):
    """
    Старт интервала
    """
    model = TimeInterval
    fields = ['start_time']
    success_url = reverse_lazy('time_interval_view')
    timezone = pytz.timezone('Europe/Moscow')

    def form_valid(self, form):
        """
        Логика при успешной отправке формы.
        """
        active_interval = TimeInterval.objects.filter(user=self.request.user, end_time__isnull=True).first()
        if active_interval:
            # Если есть активный интервал, показываем предупреждение
            messages.warning(self.request, "У вас уже есть активный интервал. Завершите его перед началом нового.")
            return redirect(self.success_url)
        else:
            # Если активного интервала нет, создаем новый
            form.instance.user = self.request.user
            form.instance.start_time = now().astimezone(self.timezone).time()
            messages.success(self.request, "Вы нажали кнопку СТАРТ. 'идет запись'")
            return super().form_valid(form)


class StopIntervalView(CreateView):
    model = TimeInterval
    fields = ['end_time']
    success_url = reverse_lazy('time_interval_view')
    timezone = pytz.timezone('Europe/Moscow')

    def form_valid(self, form):
        active_interval = TimeInterval.objects.filter(user=self.request.user, end_time__isnull=True).last()
        if active_interval:
            current_time = now().astimezone(self.timezone)
            if active_interval.start_time and (
                    current_time - make_aware(datetime.combine(current_time.date(), active_interval.start_time))
            ) > timedelta(hours=24):
                active_interval.end_time = current_time.time()
                messages.warning(
                    self.request, "Интервал автоматически завершен, так как он был активен более 24 часов."
                )
            else:
                active_interval.end_time = current_time.time()
                messages.success(self.request, "Интервал успешно завершен.")
            active_interval.save()
        else:
            messages.warning(self.request, "Нет активного интервала для завершения.")
        return redirect('time_interval_view')
