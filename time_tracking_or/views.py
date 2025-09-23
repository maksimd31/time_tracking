from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, DeleteView, UpdateView, DetailView
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.timezone import now, make_aware
from datetime import datetime, timedelta
import pytz
from django.http import HttpResponseRedirect
from .models import TimeInterval, DailySummary
from .forms import TimeIntervalFormEdit
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.views import View
from django.shortcuts import get_object_or_404, render
from django.contrib.messages import get_messages


class IndexView(LoginRequiredMixin, ListView):
    template_name = 'time_tracking_main/index.html'
    login_url = 'login'

    # context_object_name = 'time_intervals'
    #
    def get_queryset(self):
        return TimeInterval.objects.all()


class DailySummaryView(LoginRequiredMixin, ListView):
    """
    Основное представление для работы с ежедневными сводками.
    """
    template_name = 'time_tracking_main/daily_summary.html'
    # template_name = 'time_tracking_main/time_interval_new.html'

    login_url = 'login'
    context_object_name = 'daily_summaries'
    paginate_by = 5

    def get_queryset(self):
        return DailySummary.objects.filter(user=self.request.user).order_by('-date')


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
        self.update_daily_summary(self.request.user, intervals, total_duration, selected_date)
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
    def update_daily_summary(user, intervals, total_duration, summary_date):
        daily_summary, created = DailySummary.objects.get_or_create(user=user, date=summary_date)
        daily_summary.interval_count = intervals.count()
        daily_summary.total_time = total_duration
        daily_summary.save()


class StartIntervalView(LoginRequiredMixin, CreateView):
    """
    Старт интервала
    """
    model = TimeInterval
    fields = ['start_time']
    success_url = reverse_lazy('home')
    timezone = pytz.timezone('Europe/Moscow')
    login_url = 'login'

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


class StopIntervalView(LoginRequiredMixin, CreateView):
    """
    Стоп интервала
    """
    model = TimeInterval
    fields = ['end_time']
    success_url = reverse_lazy('home')
    timezone = pytz.timezone('Europe/Moscow')
    login_url = 'login'

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
        return redirect('home')


class AddManualIntervalView(LoginRequiredMixin, CreateView):
    """
    Класс для добавления интервалов вручную.
    """
    model = TimeInterval
    fields = ['start_time', 'end_time']
    template_name = 'time_tracking_main/time_interval_new.html'
    success_url = reverse_lazy('home')
    login_url = 'login'

    # def form_valid(self, form):
    #     form.instance.user = self.request.user
    #     messages.success(self.request, "Интервал успешно добавлен вручную.")
    #     return super().form_valid(form)

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.start_time = form.cleaned_data['start_time']
        form.instance.end_time = form.cleaned_data['end_time']
        messages.success(self.request, "Интервал успешно добавлен вручную.")
        return super().form_valid(form)


#
#
# class UpdateIntervalView(LoginRequiredMixin, UpdateView):
#     """
#     Класс для обновления интервалов.
#     """
#     model = TimeInterval
#     fields = ['start_time', 'end_time']
#     template_name = 'time_tracking_main/time_interval_new.html'
#     success_url = reverse_lazy('home')
#     login_url = 'login'
#
#     def form_valid(self, form):
#         messages.success(self.request, "Интервал успешно обновлен.")
#         return super().form_valid(form)


#
class IntervalDeteil(LoginRequiredMixin, DetailView):
    """
    Класс для отображения деталей интервала.
    """
    model = TimeInterval
    template_name = 'time_tracking_main/interval_detail.html'
    context_object_name = 'interval'
    login_url = 'login'

    def get_queryset(self):
        return TimeInterval.objects.filter(user=self.request.user)


# не понял не получается сделать методом POST
class DeleteIntervalView(LoginRequiredMixin, DeleteView):
    """
    Класс для удаления интервалов
    """
    model = TimeInterval
    template_name = 'time_tracking_main/time_interval_new.html'
    success_url = reverse_lazy('home')
    login_url = 'login'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        return HttpResponseRedirect(self.success_url)

    def get_queryset(self):
        return TimeInterval.objects.filter(user=self.request.user)


class IntervalDetailNew(LoginRequiredMixin, DetailView):
    """ Класс для отображения деталей интервала с использованием HTMX.
    """
    model = TimeInterval
    template_name = 'inline_htmx/interval_row.html'
    login_url = 'login'

    def get_queryset(self):
        return TimeInterval.objects.filter(user=self.request.user)


class IntervalRowHtmxView(LoginRequiredMixin, View):
    """
    Класс для обработки HTMX-запросов и возврата строки интервала.
    """

    login_url = 'login'

    def get(self, request, pk):
        interval = get_object_or_404(TimeInterval, pk=pk, user=request.user)
        selected_date = interval.date_create.date() if hasattr(interval, 'date_create') else None
        return render(request, 'inline_htmx/interval_row.html', {'interval': interval, 'selected_date': selected_date})


# Декоратор, отключающий проверку CSRF для данного класса (используется для HTMX-запросов)
@method_decorator(csrf_exempt, name='dispatch')
# Класс-представление для удаления интервала через HTMX-запрос
class DeleteIntervalViewHTMX(LoginRequiredMixin, View):
    """
    Класс для обработки HTMX-запросов на удаление интервала.
    """

    # Метод обработки HTTP DELETE-запроса
    login_url = 'login'

    def delete(self, request, pk):
        # Получаем объект TimeInterval по первичному ключу или возвращаем 404
        interval = get_object_or_404(TimeInterval, pk=pk, user=request.user)
        # Удаляем найденный интервал
        interval.delete()
        # Возвращаем пустой HTTP-ответ (без содержимого)
        return HttpResponse()


# class UpdateIntervalView(LoginRequiredMixin, View):
#     model = TimeInterval
#     form_class = TimeIntervalFormEdit
#     template_name = 'time_tracking_main/time_interval_new.html'
#     success_url = reverse_lazy('home')
#     login_url = 'login'
#
#     def get_object(self):
#         pk = self.kwargs.get('pk')
#         return get_object_or_404(TimeInterval, pk=pk)
#
#     def get_form(self, instance=None):
#         if instance is None:
#             instance = self.get_object()
#         return self.form_class(instance=instance)
#
#     def get(self, request, *args, **kwargs):
#         obj = self.get_object()
#         selected_date = obj.date_create.date() if hasattr(obj, 'date_create') else None
#         form = self.get_form(instance=obj)
#         if request.headers.get('HX-Request'):
#             html = render_to_string(
#                 'inline_htmx/interval_edit_form.html',
#                 {'interval': obj, 'form': form, 'selected_date': selected_date},
#                 request=request
#             )
#             return HttpResponse(html)
#         return render(request, self.template_name, {'form': form, 'interval': obj, 'selected_date': selected_date})
#
#     def form_valid(self, form, obj, selected_date, request):
#         start_time = form.cleaned_data['start_time']
#         end_time = form.cleaned_data['end_time']
#         if end_time <= start_time:
#             messages.warning(request, f'Время окончания не может быть меньше или равно времени начала! {end_time}')
#             if request.headers.get('HX-Request'):
#                 html = render_to_string(
#                     'inline_htmx/interval_edit_form.html',
#                     {'interval': obj, 'form': form, 'selected_date': selected_date},
#                     request=request
#                 )
#                 return HttpResponse(html, status=400)
#             return render(request, self.template_name,
#                           {'form': form, 'interval': obj, 'selected_date': selected_date})
#         form.save()
#         if request.headers.get('HX-Request'):
#             html = render_to_string(
#                 'inline_htmx/interval_row.html',
#                 {'interval': obj, 'selected_date': selected_date},
#                 request=request
#             )
#             return HttpResponse(html)
#
#         if request.headers.get('HX-Request'):
#             storage = get_messages(request)
#             html = render_to_string('inline_htmx/messages.html', {'messages': storage}, request=request)
#             return HttpResponse(html, status=400, headers={'HX-Trigger': 'show-messages'})
#
#         return redirect(self.success_url)
#
#     def post(self, request, *args, **kwargs):
#         obj = self.get_object()
#         form = self.form_class(request.POST, instance=obj)
#         selected_date = obj.date_create.date() if hasattr(obj, 'date_create') else None
#         if form.is_valid():
#             return self.form_valid(form, obj, selected_date, request)
#         else:
#             if request.headers.get('HX-Request'):
#                 html = render_to_string(
#                     'inline_htmx/interval_edit_form.html',
#                     {'interval': obj, 'form': form, 'selected_date': selected_date},
#                     request=request
#                 )
#                 return HttpResponse(html, status=400)
#             return render(request, self.template_name, {'form': form, 'interval': obj, 'selected_date': selected_date})
#
# --- Новый класс UpdateIntervalView на View (минималистичный, только HTMX) ---
class UpdateIntervalView(LoginRequiredMixin, View):
    # Обработка POST-запроса для обновления интервала
    def post(self, request, pk):
        interval = get_object_or_404(TimeInterval, pk=pk, user=request.user)
        form = TimeIntervalFormEdit(request.POST, instance=interval)
        if form.is_valid():
            start_time = form.cleaned_data.get('start_time')
            end_time = form.cleaned_data.get('end_time')
            if end_time is not None and start_time is not None and end_time <= start_time:
                messages.warning(request, 'Время окончания не может быть меньше или равно времени начала!')
                if request.headers.get('HX-Request'):
                    html = render_to_string(
                        'inline_htmx/interval_edit_form.html',
                        {
                            'interval': interval,
                            'form': form,
                            'selected_date': interval.date_create.date() if hasattr(interval, 'date_create') else None
                        },
                        request=request
                    )
                    return HttpResponse(html, status=400)
                return render(request, 'time_tracking_main/time_interval_new.html', {'form': form, 'interval': interval})
            form.save()
            if request.headers.get('HX-Request'):
                html = render_to_string(
                    'inline_htmx/interval_row.html',
                    {
                        'interval': interval,
                        'selected_date': interval.date_create.date() if hasattr(interval, 'date_create') else None
                    },
                    request=request
                )
                return HttpResponse(html)
            return redirect('home')
        else:
            if request.headers.get('HX-Request'):
                messages.warning(request, 'Ошибка валидации формы!')
                html = render_to_string(
                    'inline_htmx/interval_edit_form.html',
                    {
                        'interval': interval,
                        'form': form,
                        'selected_date': interval.date_create.date() if hasattr(interval, 'date_create') else None
                    },
                    request=request
                )
                return HttpResponse(html, status=400)
            return render(request, 'time_tracking_main/time_interval_new.html', {'form': form, 'interval': interval})

    # Обработка GET-запроса для отображения формы редактирования
    def get(self, request, pk):
        interval = get_object_or_404(TimeInterval, pk=pk, user=request.user)
        form = TimeIntervalFormEdit(instance=interval)
        if request.headers.get('HX-Request'):
            html = render_to_string(
                'inline_htmx/interval_edit_form.html',
                {
                    'interval': interval,
                    'form': form,
                    'selected_date': interval.date_create.date() if hasattr(interval, 'date_create') else None
                },
                request=request
            )
            return HttpResponse(html)
        return render(request, 'time_tracking_main/time_interval_new.html', {'form': form, 'interval': interval})

# --- Старый класс UpdateIntervalView (закомментирован) ---
'''
class UpdateIntervalView(LoginRequiredMixin, View):
    # Модель, с которой работает представление
    model = TimeInterval
    # Форма для редактирования интервала
    form_class = TimeIntervalFormEdit
    # Шаблон для отображения формы редактирования
    # template_name = 'time_tracking_main/time_interval_new.html'
    # URL для перенаправления после успешного обновления
    success_url = reverse_lazy('home')
    # URL для страницы логина, если пользователь не авторизован
    # login_url = 'login'

    # Получение объекта интервала по первичному ключу из URL
    def get_object(self):
        pk = self.kwargs.get('pk')
        return get_object_or_404(TimeInterval, pk=pk)

    # Получение формы для редактирования, с передачей экземпляра интервала
    def get_form(self, instance=None):
        if instance is None:
            instance = self.get_object()
        return self.form_class(instance=instance)

    # Обработка GET-запроса: отображение формы редактирования
    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        # Получение выбранной даты, если она есть у объекта
        selected_date = obj.date_create.date() if hasattr(obj, 'date_create') else None
        form = self.get_form(instance=obj)
        # Если запрос от HTMX, возвращаем только HTML формы
        if request.headers.get('HX-Request'):
            html = render_to_string(
                'inline_htmx/interval_edit_form.html',
                {'interval': obj, 'form': form, 'selected_date': selected_date},
                request=request
            )
            return HttpResponse(html)
        # Обычный рендеринг страницы с формой
        return render(request, self.template_name, {'form': form, 'interval': obj, 'selected_date': selected_date})

    # Проверка и сохранение формы при валидных данных
    def form_valid(self, form, obj, selected_date, request):
        start_time = form.cleaned_data['start_time']
        end_time = form.cleaned_data['end_time']
        # Проверка: время окончания не может быть меньше или равно времени начала
        if end_time <= start_time:
            messages.warning(request, f'Время окончания не может быть меньше или равно времени начала! {end_time}')
            if request.headers.get('HX-Request'):
                storage = get_messages(request)
                html = render_to_string('includes/messages.html', {'messages': storage}, request=request)
                form_html = render_to_string(
                    'inline_htmx/interval_edit_form.html',
                    {'interval': obj, 'form': form, 'selected_date': selected_date},
                    request=request
                )
                return HttpResponse(html + form_html, status=400)
            return render(request, self.template_name, {'form': form, 'interval': obj, 'selected_date': selected_date})
        # # Сохраняем изменения, если всё корректно
        form.save()
        return redirect(self.success_url)

    # Обработка POST-запроса: получение и валидация формы
    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        form = self.form_class(request.POST, instance=obj)
        selected_date = obj.date_create.date() if hasattr(obj, 'date_create') else None
        # Если форма валидна, вызываем обработчик успешной валидации
        if form.is_valid():
            return self.form_valid(form, obj, selected_date, request)
        else:
            # Если запрос от HTMX, возвращаем сообщения и форму с ошибкой
            if request.headers.get('HX-Request'):
                storage = get_messages(request)
                html = render_to_string('includes/messages.html', {'messages': storage}, request=request)
                form_html = render_to_string(
                    'inline_htmx/interval_edit_form.html',
                    {'interval': obj, 'form': form, 'selected_date': selected_date},
                    request=request
                )
                return HttpResponse(html + form_html, status=400)
            # Обычный рендеринг страницы с ошибкой
            return render(request, self.template_name, {'form': form, 'interval': obj, 'selected_date': selected_date})
'''
