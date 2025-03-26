from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.timezone import now, make_aware
from datetime import datetime, timedelta
import pytz
from .models import TimeInterval


class IndexView(LoginRequiredMixin,ListView):
    template_name = 'time_tracking_main/index.html'
    login_url = 'login'
    # context_object_name = 'time_intervals'

    def get_queryset(self):
        return TimeInterval.objects.all()


class TimeIntervalView(LoginRequiredMixin,ListView):
    """
    Основное представление для работы с интервалами времени.
    """
    template_name = 'time_tracking_main/time_interval_new.html'
    timezone = pytz.timezone('Europe/Moscow')
    login_url = 'login'
    context_object_name = 'intervals'

    def get_queryset(self):
        return TimeInterval.objects.all()



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
            messages.success(self.request,"Вы нажали кнопку СТАРТ. 'идет запись'")
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



