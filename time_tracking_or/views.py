from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Sum
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView

from .forms import TimeCounterForm, TimeIntervalFormEdit
from .models import DailySummary, TimeCounter, TimeInterval


def recalculate_daily_summary(user, day):
    """Пересчитать суточный итог пользователя по всем счетчикам."""
    aggregate = TimeInterval.objects.filter(
        user=user,
        day=day,
        end_time__isnull=False,
    ).aggregate(total=Sum('duration'), interval_count=Count('id'))

    total = aggregate['total'] or timedelta()
    interval_count = aggregate['interval_count'] or 0

    if interval_count == 0 and total == timedelta():
        DailySummary.objects.filter(user=user, date=day).delete()
        return

    DailySummary.objects.update_or_create(
        user=user,
        date=day,
        defaults={
            'total_time': total,
            'interval_count': interval_count,
        },
    )


class TimeCounterListView(ListView):
    template_name = 'time_tracking_main/counter_dashboard.html'
    context_object_name = 'counters'
    paginate_by = 6

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            context = {
                'login_url': reverse('login'),
                'register_url': reverse('register'),
            }
            return render(request, 'time_tracking_main/welcome.html', context)
        return super().dispatch(request, *args, **kwargs)

    def get_selected_date(self):
        date_str = self.request.GET.get('date')
        if not date_str:
            return timezone.localdate()
        try:
            return timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return timezone.localdate()

    def get_queryset(self):
        return TimeCounter.objects.filter(user=self.request.user).order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected_date = self.get_selected_date()
        user_counters = TimeCounter.objects.filter(user=self.request.user).order_by('name')
        intervals_qs = TimeInterval.objects.filter(
            counter__user=self.request.user,
            day=selected_date,
        )

        totals = {
            item['counter_id']: {
                'total': item['total'] or timedelta(),
                'interval_count': item['interval_count'],
            }
            for item in intervals_qs.filter(end_time__isnull=False)
            .values('counter_id')
            .annotate(total=Sum('duration'), interval_count=Count('id'))
        }

        active_map = {
            interval.counter_id: interval
            for interval in intervals_qs.filter(end_time__isnull=True).select_related('counter')
        }

        counter_stats = {}
        overall_total = timedelta()
        chart_labels = []
        chart_values = []
        chart_colors = []
        active_counter_id = None
        active_interval = None

        for counter in user_counters:
            total_info = totals.get(counter.id, {'total': timedelta(), 'interval_count': 0})
            total_duration = total_info['total']
            overall_total += total_duration
            counter_stats[counter.id] = {
                'total_duration': total_duration,
                'interval_count': total_info['interval_count'],
                'active_interval': active_map.get(counter.id),
            }
            if active_map.get(counter.id) and active_counter_id is None:
                active_counter_id = counter.id
                active_interval = active_map.get(counter.id)
            if total_duration > timedelta():
                chart_labels.append(counter.name)
                chart_values.append(round(total_duration.total_seconds() / 3600, 2))
                chart_colors.append(counter.color)

        context.update(
            {
                'selected_date': selected_date,
                'counter_stats': counter_stats,
                'overall_total': overall_total,
                'chart_labels': chart_labels,
                'chart_values': chart_values,
                'chart_colors': chart_colors,
                'create_form': TimeCounterForm(),
                'active_counter_id': active_counter_id,
                'chart_max_value': max(chart_values) if chart_values else 0,
                'chart_total': sum(chart_values) if chart_values else 0,
                'counter_total': user_counters.count(),
                'active_counter': active_interval.counter if active_interval else None,
                'active_interval': active_interval,
                'paused_counters': self.request.session.get('paused_counters', []),
            }
        )
        return context

    def get_template_names(self):
        if self.request.headers.get('HX-Request'):
            return ['time_tracking_main/_counter_dashboard_content.html']
        return [self.template_name]


class TimeCounterCreateView(LoginRequiredMixin, CreateView):
    model = TimeCounter
    form_class = TimeCounterForm
    template_name = 'time_tracking_main/counter_form.html'
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Счетчик создан.')
        return super().form_valid(form)


class TimeCounterUpdateView(LoginRequiredMixin, UpdateView):
    model = TimeCounter
    form_class = TimeCounterForm
    template_name = 'time_tracking_main/counter_form.html'
    success_url = reverse_lazy('home')

    def get_queryset(self):
        return TimeCounter.objects.filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Счетчик обновлен.')
        return super().form_valid(form)


class TimeCounterDeleteView(LoginRequiredMixin, DeleteView):
    model = TimeCounter
    template_name = 'time_tracking_main/counter_confirm_delete.html'
    success_url = reverse_lazy('home')

    def get_queryset(self):
        return TimeCounter.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Счетчик удален.')
        return super().delete(request, *args, **kwargs)


class CounterHistoryView(LoginRequiredMixin, ListView):
    template_name = 'time_tracking_main/counter_history.html'
    context_object_name = 'intervals'
    paginate_by = 10

    def dispatch(self, request, *args, **kwargs):
        self.counter = get_object_or_404(TimeCounter, pk=self.kwargs['pk'], user=request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_date_filters(self):
        start_str = self.request.GET.get('start')
        end_str = self.request.GET.get('end')
        start = end = None
        if start_str:
            try:
                start = timezone.datetime.strptime(start_str, '%Y-%m-%d').date()
            except ValueError:
                start = None
        if end_str:
            try:
                end = timezone.datetime.strptime(end_str, '%Y-%m-%d').date()
            except ValueError:
                end = None
        return start, end

    def get_queryset(self):
        qs = TimeInterval.objects.filter(counter=self.counter).order_by('-day', '-date_create')
        start, end = self.get_date_filters()
        if start:
            qs = qs.filter(day__gte=start)
        if end:
            qs = qs.filter(day__lte=end)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        start, end = self.get_date_filters()
        intervals = self.get_queryset().filter(end_time__isnull=False)
        aggregate = intervals.aggregate(total=Sum('duration'), count=Count('id'))
        context.update(
            {
                'counter': self.counter,
                'filter_start': start,
                'filter_end': end,
                'total_duration': aggregate['total'] or timedelta(),
                'interval_count': aggregate['count'] or 0,
            }
        )
        return context


class CounterIntervalUpdateView(LoginRequiredMixin, UpdateView):
    model = TimeInterval
    form_class = TimeIntervalFormEdit
    template_name = 'time_tracking_main/interval_form.html'

    def get_success_url(self):
        return reverse('counter_history', kwargs={'pk': self.object.counter_id})

    def get_queryset(self):
        return TimeInterval.objects.filter(counter__user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['interval'] = self.object
        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('HX-Request'):
            mode = self.request.GET.get('mode')
            template = 'time_tracking_main/partials/history_interval_edit_row.html'
            if mode == 'display':
                template = 'time_tracking_main/partials/history_interval_row.html'
            context['interval'] = self.object
            return render(
                self.request,
                template,
                context,
                **response_kwargs
            )
        return super().render_to_response(context, **response_kwargs)

    def form_valid(self, form):
        original_day = self.get_object().day
        response = super().form_valid(form)
        recalculate_daily_summary(self.request.user, self.object.day)
        if original_day != self.object.day:
            recalculate_daily_summary(self.request.user, original_day)
        if self.request.headers.get('HX-Request'):
            html = render_to_string(
                'time_tracking_main/partials/history_interval_row.html',
                {'interval': self.object},
                request=self.request
            )
            return HttpResponse(html)
        return response

    def form_invalid(self, form):
        if self.request.headers.get('HX-Request'):
            context = self.get_context_data(form=form)
            return render(
                self.request,
                'time_tracking_main/partials/history_interval_edit_row.html',
                context,
                status=400
            )
        return super().form_invalid(form)


class CounterIntervalDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        interval = get_object_or_404(TimeInterval, pk=pk, counter__user=request.user)
        counter_id = interval.counter_id
        day = interval.day
        interval.delete()
        recalculate_daily_summary(request.user, day)
        messages.success(request, 'Интервал удален.')
        return redirect('counter_history', pk=counter_id)


class CounterManualIntervalCreateView(LoginRequiredMixin, CreateView):
    model = TimeInterval
    form_class = TimeIntervalFormEdit
    template_name = 'time_tracking_main/interval_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.counter = get_object_or_404(TimeCounter, pk=self.kwargs['pk'], user=request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial['day'] = timezone.localdate()
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['counter'] = self.counter
        return context

    def form_valid(self, form):
        form.instance.counter = self.counter
        form.instance.user = self.request.user
        messages.success(self.request, 'Интервал добавлен вручную.')
        response = super().form_valid(form)
        recalculate_daily_summary(self.request.user, form.instance.day)
        return response

    def get_success_url(self):
        return reverse('counter_history', kwargs={'pk': self.counter.pk})


class CounterBaseActionView(LoginRequiredMixin, View):
    action_message = ''

    def post(self, request, pk):
        counter = get_object_or_404(TimeCounter, pk=pk, user=request.user)
        return self.handle(request, counter)

    def handle(self, request, counter):  # pragma: no cover - override required
        raise NotImplementedError

    def get_redirect(self, request):
        next_url = request.POST.get('next') or request.GET.get('next')
        return redirect(next_url or 'home')

    def hx_response(self, request):
        view = TimeCounterListView()
        view.request = request
        view.kwargs = {}
        view.object_list = view.get_queryset()
        context = view.get_context_data()
        return render(request, 'time_tracking_main/_counter_dashboard_content.html', context)


class CounterStartView(CounterBaseActionView):
    def handle(self, request, counter):
        active_interval = TimeInterval.objects.filter(counter__user=request.user, end_time__isnull=True).exclude(counter=counter).first()
        if active_interval:
            messages.warning(request, 'Невозможно делать два дела одновременно. Завершите текущий счетчик.')
            if request.headers.get('HX-Request'):
                return self.hx_response(request)
            return self.get_redirect(request)
        if counter.is_running:
            messages.info(request, 'Счетчик уже запущен.')
            if request.headers.get('HX-Request'):
                return self.hx_response(request)
            return self.get_redirect(request)
        local_time = timezone.localtime()
        TimeInterval.objects.create(
            counter=counter,
            user=request.user,
            day=timezone.localdate(),
            start_time=local_time.time(),
        )
        paused = request.session.get('paused_counters', [])
        if counter.id in paused:
            paused.remove(counter.id)
            request.session['paused_counters'] = paused
        if request.headers.get('HX-Request'):
            return self.hx_response(request)
        return self.get_redirect(request)


class CounterPauseView(CounterBaseActionView):
    action_message = 'Счетчик поставлен на паузу.'

    def handle(self, request, counter):
        interval = counter.intervals.filter(end_time__isnull=True).order_by('-date_create').first()
        if not interval:
            messages.info(request, 'Нет активного интервала для паузы.')
            if request.headers.get('HX-Request'):
                return self.hx_response(request)
            return self.get_redirect(request)
        local_time = timezone.localtime()
        interval.end_time = local_time.time()
        interval.day = timezone.localdate()
        interval.save(update_fields=['end_time', 'day', 'duration'])
        recalculate_daily_summary(request.user, interval.day)
        paused = request.session.get('paused_counters', [])
        if counter.id not in paused:
            paused.append(counter.id)
            request.session['paused_counters'] = paused
        if request.headers.get('HX-Request'):
            return self.hx_response(request)
        return self.get_redirect(request)


class CounterStopView(CounterBaseActionView):
    def handle(self, request, counter):
        interval = counter.intervals.filter(end_time__isnull=True).order_by('-date_create').first()
        if not interval:
            messages.info(request, 'Нет активного интервала для остановки.')
            if request.headers.get('HX-Request'):
                return self.hx_response(request)
            return self.get_redirect(request)
        local_time = timezone.localtime()
        interval.end_time = local_time.time()
        interval.day = timezone.localdate()
        interval.save(update_fields=['end_time', 'day', 'duration'])
        recalculate_daily_summary(request.user, interval.day)
        paused = request.session.get('paused_counters', [])
        if counter.id in paused:
            paused.remove(counter.id)
            request.session['paused_counters'] = paused
        if request.headers.get('HX-Request'):
            return self.hx_response(request)
        return self.get_redirect(request)


class CounterSummaryView(LoginRequiredMixin, TemplateView):
    template_name = 'time_tracking_main/counter_summary.html'

    PERIODS = {
        'week': 'Неделя',
        'month': 'Месяц',
        'custom': 'Произвольный период',
    }

    def get_period_range(self):
        period = self.request.GET.get('period', 'week')
        today = timezone.localdate()
        if period == 'month':
            start = today.replace(day=1)
        elif period == 'custom':
            start_str = self.request.GET.get('start')
            end_str = self.request.GET.get('end')
            try:
                start = timezone.datetime.strptime(start_str, '%Y-%m-%d').date() if start_str else today
            except ValueError:
                start = today
            try:
                end = timezone.datetime.strptime(end_str, '%Y-%m-%d').date() if end_str else today
            except ValueError:
                end = today
            if start > end:
                start, end = end, start
            return period, start, end
        else:
            start = today - timedelta(days=6)
        return period, start, today

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        period, start, end = self.get_period_range()
        intervals = TimeInterval.objects.filter(
            user=self.request.user,
            day__range=(start, end),
            end_time__isnull=False,
        )
        per_counter = intervals.values('counter__name', 'counter__color').annotate(
            total=Sum('duration'),
            interval_count=Count('id'),
        ).order_by('-total')
        per_day = intervals.values('day').annotate(total=Sum('duration')).order_by('day')

        summary_total = sum((item['total'] or timedelta() for item in per_counter), timedelta())

        context.update(
            {
                'period_key': period,
                'periods': self.PERIODS,
                'start': start,
                'end': end,
                'per_counter': per_counter,
                'per_day': per_day,
                'summary_total': summary_total,
            }
        )
        return context


@method_decorator(csrf_exempt, name='dispatch')
class DeleteIntervalViewHTMX(CounterIntervalDeleteView):
    """Совместимость с существующим HTMX маршрутом."""

    def post(self, request, pk):
        interval = get_object_or_404(TimeInterval, pk=pk, counter__user=request.user)
        counter_id = interval.counter_id
        day = interval.day
        interval.delete()
        recalculate_daily_summary(request.user, day)
        if request.headers.get('HX-Request'):
            return HttpResponse(status=204)
        messages.success(request, 'Интервал удален.')
        return redirect('counter_history', pk=counter_id)


class IntervalDetailView(LoginRequiredMixin, DetailView):
    model = TimeInterval
    template_name = 'time_tracking_main/interval_detail.html'
    context_object_name = 'interval'

    def get_queryset(self):
        return TimeInterval.objects.filter(counter__user=self.request.user)
