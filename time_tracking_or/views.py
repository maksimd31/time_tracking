"""Views that power counter dashboards, history pages, and HTMX endpoints."""

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
from .models import DailySummary, ProjectRating, TimeCounter, TimeInterval


def recalculate_daily_summary(user, day):
    """Recompute cached day summary for a specific user and date."""
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
    """Dashboard with counters, diagrams, and HTMX support."""
    template_name = 'time_tracking_main/counter_dashboard.html'
    context_object_name = 'counters'
    paginate_by = 6

    def dispatch(self, request, *args, **kwargs):
        """Redirect anonymous users to the welcome screen."""
        if not request.user.is_authenticated:
            context = {
                'login_url': reverse('login'),
                'register_url': reverse('register'),
            }
            return render(request, 'time_tracking_main/welcome.html', context)
        return super().dispatch(request, *args, **kwargs)

    def get_selected_date(self):
        """Return the currently selected day, guarded against bad input."""
        date_str = self.request.GET.get('date')
        if not date_str:
            return timezone.localdate()
        try:
            return timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return timezone.localdate()

    def get_queryset(self):
        """Limit counters to the current user."""
        return TimeCounter.objects.filter(user=self.request.user).order_by('name')

    def get_context_data(self, **kwargs):
        """Collect aggregated stats, chart data, and HTMX helper context."""
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

        # Добавляем контекст рейтинга проекта
        rating_context = get_project_rating_context(self.request.user)
        
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
                **rating_context,  # Добавляем контекст рейтинга
            }
        )
        return context

    def get_template_names(self):
        """Return partial template when HTMX requests the dashboard."""
        if self.request.headers.get('HX-Request'):
            return ['time_tracking_main/_counter_dashboard_content.html']
        return [self.template_name]


class TimeCounterCreateView(LoginRequiredMixin, CreateView):
    """Form-based creation of a new counter."""
    model = TimeCounter
    form_class = TimeCounterForm
    template_name = 'time_tracking_main/counter_form.html'
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        """Attach the current user and show a success message."""
        form.instance.user = self.request.user
        messages.success(self.request, 'Счетчик создан.')
        return super().form_valid(form)


class TimeCounterUpdateView(LoginRequiredMixin, UpdateView):
    """Allow a user to rename or recolor an existing counter."""
    model = TimeCounter
    form_class = TimeCounterForm
    template_name = 'time_tracking_main/counter_form.html'
    success_url = reverse_lazy('home')

    def get_queryset(self):
        """Restrict updates to counters owned by the requester."""
        return TimeCounter.objects.filter(user=self.request.user)

    def form_valid(self, form):
        """Display a toast and persist changes."""
        messages.success(self.request, 'Счетчик обновлен.')
        return super().form_valid(form)


class TimeCounterDeleteView(LoginRequiredMixin, DeleteView):
    """Deletion confirmation and removal for a counter."""
    model = TimeCounter
    template_name = 'time_tracking_main/counter_confirm_delete.html'
    success_url = reverse_lazy('home')

    def get_queryset(self):
        """Ensure users can delete only their own counters."""
        return TimeCounter.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        """Show a success message after the counter is removed."""
        messages.success(self.request, 'Счетчик удален.')
        return super().delete(request, *args, **kwargs)


class CounterHistoryView(LoginRequiredMixin, ListView):
    """Detailed list of intervals with filtering, pagination, and stats."""
    template_name = 'time_tracking_main/counter_history.html'
    context_object_name = 'intervals'
    paginate_by = 10

    def dispatch(self, request, *args, **kwargs):
        """Cache the requested counter and assert ownership."""
        self.counter = get_object_or_404(TimeCounter, pk=self.kwargs['pk'], user=request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_date_filters(self):
        """Parse date query parameters into `date` objects."""
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
        """Return intervals ordered by day and creation time."""
        qs = TimeInterval.objects.filter(counter=self.counter).order_by('-day', '-date_create')
        start, end = self.get_date_filters()
        if start:
            qs = qs.filter(day__gte=start)
        if end:
            qs = qs.filter(day__lte=end)
        return qs

    def get_context_data(self, **kwargs):
        """Augment context with aggregated statistics for the listing."""
        context = super().get_context_data(**kwargs)
        start, end = self.get_date_filters()
        intervals = self.get_queryset().filter(end_time__isnull=False)
        aggregate = intervals.aggregate(total=Sum('duration'), count=Count('id'))
        active_interval = self.counter.intervals.filter(end_time__isnull=True).order_by('-date_create').first()
        active_total = 0
        if active_interval and active_interval.start_time:
            day_total = (
                self.counter.intervals
                .filter(day=active_interval.day, end_time__isnull=False)
                .aggregate(total=Sum('duration'))['total']
                or timedelta()
            )
            active_total = int(day_total.total_seconds())
        context.update(
            {
                'counter': self.counter,
                'filter_start': start,
                'filter_end': end,
                'total_duration': aggregate['total'] or timedelta(),
                'interval_count': aggregate['count'] or 0,
                'active_interval': active_interval,
                'active_total': active_total,
            }
        )
        return context


class CounterIntervalUpdateView(LoginRequiredMixin, UpdateView):
    """HTMX-enabled inline editor for individual intervals."""
    model = TimeInterval
    form_class = TimeIntervalFormEdit
    template_name = 'time_tracking_main/interval_form.html'

    def get_success_url(self):
        """Fallback redirect to the counter history page."""
        return reverse('counter_history', kwargs={'pk': self.object.counter_id})

    def get_queryset(self):
        """Ensure users can edit only intervals belonging to their counters."""
        return TimeInterval.objects.filter(counter__user=self.request.user)

    def get_context_data(self, **kwargs):
        """Expose the interval instance alongside the bound form."""
        context = super().get_context_data(**kwargs)
        context['interval'] = self.object
        return context

    def render_to_response(self, context, **response_kwargs):
        """Return partial rows for HTMX or fallback to standard rendering."""
        if self.request.headers.get('HX-Request'):
            mode = self.request.GET.get('mode')
            template = 'time_tracking_main/partials/history_interval_edit_row.html'
            if mode == 'display':
                template = 'time_tracking_main/partials/history_interval_row.html'
            context['interval'] = self.object
            number = (
                self.request.GET.get('num')
                or self.request.POST.get('num')
            )
            if number:
                context['number'] = number
            # Пробрасываем фильтры, чтобы шаблон мог восстановить скрытые инпуты
            start = self.request.GET.get('start') or self.request.POST.get('start')
            end = self.request.GET.get('end') or self.request.POST.get('end')
            if start:
                try:
                    context['filter_start'] = timezone.datetime.strptime(start, '%Y-%m-%d').date()
                except ValueError:
                    context['filter_start'] = None
            if end:
                try:
                    context['filter_end'] = timezone.datetime.strptime(end, '%Y-%m-%d').date()
                except ValueError:
                    context['filter_end'] = None
            return render(
                self.request,
                template,
                context,
                **response_kwargs
            )
        return super().render_to_response(context, **response_kwargs)

    def form_valid(self, form):
        """Persist changes, refresh summaries, and return updated markup."""
        original_day = self.get_object().day
        response = super().form_valid(form)
        recalculate_daily_summary(self.request.user, self.object.day)
        if original_day != self.object.day:
            recalculate_daily_summary(self.request.user, original_day)
        if self.request.headers.get('HX-Request'):
            number = self.request.POST.get('num')
            start = self.request.POST.get('start')
            end = self.request.POST.get('end')

            # Пересчет агрегатов с учетом фильтров
            qs = TimeInterval.objects.filter(counter_id=self.object.counter_id)
            if start:
                try:
                    sd = timezone.datetime.strptime(start, '%Y-%m-%d').date()
                    qs = qs.filter(day__gte=sd)
                except ValueError:
                    pass
            if end:
                try:
                    ed = timezone.datetime.strptime(end, '%Y-%m-%d').date()
                    qs = qs.filter(day__lte=ed)
                except ValueError:
                    pass
            finished = qs.filter(end_time__isnull=False)
            aggregate = finished.aggregate(total=Sum('duration'), count=Count('id'))
            stats_ctx = {
                'interval_count': aggregate.get('count') or 0,
                'total_duration': aggregate.get('total') or timedelta(),
            }

            # Рендер строки
            row_ctx = {'interval': self.object}
            if number:
                row_ctx['number'] = number
            if start:
                # Нужно передать фильтры обратно для будущих действий
                try:
                    row_ctx['filter_start'] = timezone.datetime.strptime(start, '%Y-%m-%d').date()
                except ValueError:
                    pass
            if end:
                try:
                    row_ctx['filter_end'] = timezone.datetime.strptime(end, '%Y-%m-%d').date()
                except ValueError:
                    pass
            row_html = render_to_string(
                'time_tracking_main/partials/history_interval_row.html',
                row_ctx,
                request=self.request,
            )
            stats_html_inner = render_to_string(
                'time_tracking_main/partials/history_stats.html',
                stats_ctx,
                request=self.request,
            )
            # Возвращаем строку + OOB обновление статистики
            full_html = (
                row_html
                + "<div id='history-stats' hx-swap-oob='true'>"
                + stats_html_inner
                + "</div>"
            )
            return HttpResponse(full_html)
        return response

    def form_invalid(self, form):
        """Re-render the editable row with errors for HTMX consumers."""
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
    """Regular form-based deletion with redirect and messaging."""
    def post(self, request, pk):
        """Delete an interval and recalculate summaries."""
        interval = get_object_or_404(TimeInterval, pk=pk, counter__user=request.user)
        counter_id = interval.counter_id
        day = interval.day
        interval.delete()
        recalculate_daily_summary(request.user, day)
        messages.success(request, 'Интервал удален.')
        return redirect('counter_history', pk=counter_id)


class CounterManualIntervalCreateView(LoginRequiredMixin, CreateView):
    """Manual interval creation form for adding historical data."""
    model = TimeInterval
    form_class = TimeIntervalFormEdit
    template_name = 'time_tracking_main/interval_form.html'

    def dispatch(self, request, *args, **kwargs):
        """Fetch the counter upfront and enforce ownership."""
        self.counter = get_object_or_404(TimeCounter, pk=self.kwargs['pk'], user=request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        """Default the day to today for convenience."""
        initial = super().get_initial()
        initial['day'] = timezone.localdate()
        return initial

    def get_context_data(self, **kwargs):
        """Add the counter to the template context."""
        context = super().get_context_data(**kwargs)
        context['counter'] = self.counter
        return context

    def form_valid(self, form):
        """Attach user/counter links, then update daily summary."""
        form.instance.counter = self.counter
        form.instance.user = self.request.user
        messages.success(self.request, 'Интервал добавлен вручную.')
        response = super().form_valid(form)
        recalculate_daily_summary(self.request.user, form.instance.day)
        return response

    def get_success_url(self):
        """Redirect back to the history page after creation."""
        return reverse('counter_history', kwargs={'pk': self.counter.pk})


class CounterBaseActionView(LoginRequiredMixin, View):
    """Base class for start/pause/stop counter actions."""
    action_message = ''

    def post(self, request, pk):
        """Resolve the counter and delegate to subclass handlers."""
        counter = get_object_or_404(TimeCounter, pk=pk, user=request.user)
        return self.handle(request, counter)

    def handle(self, request, counter):  # pragma: no cover - override required
        """Subclasses must implement specific business logic."""
        raise NotImplementedError

    def get_redirect(self, request):
        """Return a redirect to `next` or the dashboard."""
        next_url = request.POST.get('next') or request.GET.get('next')
        return redirect(next_url or 'home')

    def hx_response(self, request, counter=None):
        """Return HTMX fragments for dashboard or history contexts."""
        # Если это действия со страницы истории (есть флаг history и counter передан)
        if (request.POST.get('history') or request.GET.get('history')) and counter:
            qs = TimeInterval.objects.filter(counter=counter).order_by('-day', '-date_create')
            from django.core.paginator import Paginator
            paginator = Paginator(qs, 10)
            page_number = 1
            try:
                if request.POST.get('page'):
                    page_number = int(request.POST.get('page'))
            except ValueError:
                page_number = 1
            page_obj = paginator.get_page(page_number)
            finished = qs.filter(end_time__isnull=False)
            aggregate = finished.aggregate(total=Sum('duration'), count=Count('id'))
            active_interval = qs.filter(end_time__isnull=True).first()
            active_total = 0
            if active_interval and active_interval.start_time:
                day_total = qs.filter(day=active_interval.day, end_time__isnull=False).aggregate(
                    total=Sum('duration')
                )['total'] or timedelta()
                active_total = int(day_total.total_seconds())
            ctx = {
                'counter': counter,
                'intervals': page_obj.object_list,
                'page_obj': page_obj,
                'paginator': paginator,
                'is_paginated': page_obj.has_other_pages(),
                'interval_count': aggregate.get('count') or 0,
                'total_duration': aggregate.get('total') or timedelta(),
                'active_interval': active_interval,
                'active_total': active_total,
            }
            controls_html = render_to_string(
                'time_tracking_main/partials/history_counter_controls.html',
                ctx,
                request=request,
            )
            stats_html = render_to_string(
                'time_tracking_main/partials/history_stats.html',
                ctx,
                request=request,
            )
            # Формируем полный контейнер таблицы, чтобы избежать проблем с заменой <tbody> (дублирование в некоторых браузерах)
            start_index = page_obj.start_index()
            rows_html = []
            for offset, interval in enumerate(page_obj.object_list):
                rows_html.append(
                    render_to_string(
                        'time_tracking_main/partials/history_interval_row.html',
                        {
                            'interval': interval,
                            'number': start_index + offset,  # начинается с 1
                        },
                        request=request,
                    )
                )
            table_container = (
                "<div id='history-intervals' hx-swap-oob='true'>"
                "<table class='table table-modern align-middle history-table'>"
                "<thead><tr>"
                "<th scope='col' style='width:72px;'>№</th>"
                "<th scope='col'>Дата</th>"
                "<th scope='col'>Старт</th>"
                "<th scope='col'>Стоп</th>"
                "<th scope='col'>Длительность</th>"
                "<th scope='col' class='text-end'>Действия</th>"
                "</tr></thead>"
                "<tbody id='history-intervals-body'>"
                + ''.join(rows_html)
                + "</tbody></table>"
                "</div>"
            )
            stats_oob = (
                "<div id='history-stats' hx-swap-oob='true'>" + stats_html + "</div>"
            )
            return HttpResponse(controls_html + stats_oob + table_container)

        # Иначе возвращаем дашборд (главная панель)
        view = TimeCounterListView()
        view.request = request
        view.kwargs = {}
        view.object_list = view.get_queryset()
        context = view.get_context_data()
        return render(request, 'time_tracking_main/_counter_dashboard_content.html', context)


class CounterStartView(CounterBaseActionView):
    """Start (or resume) timer for the selected counter."""
    def handle(self, request, counter):
        """Validate exclusivity and create a new active interval."""
        active_interval = TimeInterval.objects.filter(counter__user=request.user, end_time__isnull=True).exclude(counter=counter).first()
        if active_interval:
            messages.warning(request, 'Невозможно делать два дела одновременно. Завершите текущий счетчик.')
            if request.headers.get('HX-Request'):
                return self.hx_response(request, counter=counter)
            return self.get_redirect(request)
        if counter.is_running:
            messages.info(request, 'Счетчик уже запущен.')
            if request.headers.get('HX-Request'):
                return self.hx_response(request, counter=counter)
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
            return self.hx_response(request, counter=counter)
        return self.get_redirect(request)


class CounterPauseView(CounterBaseActionView):
    """Pause a running counter without closing the day summary."""
    action_message = 'Счетчик поставлен на паузу.'

    def handle(self, request, counter):
        """Finalize the current interval but keep session marked as paused."""
        interval = counter.intervals.filter(end_time__isnull=True).order_by('-date_create').first()
        if not interval:
            messages.info(request, 'Нет активного интервала для паузы.')
            if request.headers.get('HX-Request'):
                return self.hx_response(request, counter=counter)
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
            return self.hx_response(request, counter=counter)
        return self.get_redirect(request)


class CounterStopView(CounterBaseActionView):
    """Stop the currently running interval and clear paused state."""
    def handle(self, request, counter):
        """Close the open interval and refresh day summaries."""
        interval = counter.intervals.filter(end_time__isnull=True).order_by('-date_create').first()
        if not interval:
            messages.info(request, 'Нет активного интервала для остановки.')
            if request.headers.get('HX-Request'):
                return self.hx_response(request, counter=counter)
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
            return self.hx_response(request, counter=counter)
        return self.get_redirect(request)


class CounterSummaryView(LoginRequiredMixin, TemplateView):
    """Aggregated summary across periods (week/month/custom)."""
    template_name = 'time_tracking_main/counter_summary.html'

    PERIODS = {
        'week': 'Неделя',
        'month': 'Месяц',
        'custom': 'Произвольный период',
    }

    def dispatch(self, request, *args, **kwargs):
        """Allow access but mark guest sessions for overlay."""
        self.guest_mode = bool(request.session.get('is_guest'))
        return super().dispatch(request, *args, **kwargs)

    def get_period_range(self):
        """Resolve selected period into a concrete (start, end) tuple."""
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
        """Populate template context with per-counter/day aggregates."""
        context = super().get_context_data(**kwargs)
        period, start, end = self.get_period_range()
        context.update(
            {
                'period_key': period,
                'periods': self.PERIODS,
                'start': start,
                'end': end,
                'guest_mode': getattr(self, 'guest_mode', False),
            }
        )

        if getattr(self, 'guest_mode', False):
            context.setdefault('per_counter', [])
            context.setdefault('per_day', [])
            context.setdefault('summary_total', timedelta())
            return context

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
                'per_counter': per_counter,
                'per_day': per_day,
                'summary_total': summary_total,
            }
        )
        return context


@method_decorator(csrf_exempt, name='dispatch')
class DeleteIntervalViewHTMX(CounterIntervalDeleteView):
    """HTMX-friendly delete endpoint returning empty 204 response."""

    def post(self, request, pk):
        """Delete an interval and respond with 204 for HTMX."""
        return self._handle_delete(request, pk)

    # HTMX hx-delete шлёт DELETE; раньше обрабатывался только POST.
    def delete(self, request, pk):  # type: ignore[override]
        return self._handle_delete(request, pk)

    def _handle_delete(self, request, pk):
        interval = get_object_or_404(
            TimeInterval,
            pk=pk,
            counter__user=request.user,
        )
        counter_id = interval.counter_id
        day = interval.day
        interval.delete()
        recalculate_daily_summary(request.user, day)
        # Подсчёт обновленной статистики (учёт фильтров даты)
        start = request.POST.get('start') or request.GET.get('start')
        end = request.POST.get('end') or request.GET.get('end')

        def parse_date(value):  # локальный парсер без повторного импорта
            if not value:
                return None
            try:
                return timezone.datetime.strptime(value, '%Y-%m-%d').date()
            except ValueError:
                return None

        start_d = parse_date(start)
        end_d = parse_date(end)

        qs = TimeInterval.objects.filter(counter_id=counter_id)
        if start_d:
            qs = qs.filter(day__gte=start_d)
        if end_d:
            qs = qs.filter(day__lte=end_d)
        finished = qs.filter(end_time__isnull=False)
        aggregate = finished.aggregate(
            total=Sum('duration'),
            count=Count('id'),
        )
        ctx = {
            'interval_count': aggregate.get('count') or 0,
            'total_duration': aggregate.get('total') or timedelta(),
        }
        if request.headers.get('HX-Request'):
            stats_inner = render_to_string(
                'time_tracking_main/partials/history_stats.html',
                ctx,
                request=request,
            )
            # OOB обновление статистики + удаление строки
            html = (
                "<!--deleted--><div id='history-stats' "
                "hx-swap-oob='true'>" + stats_inner + "</div>"
            )
            return HttpResponse(html)
        messages.success(request, 'Интервал удален.')
        return redirect('counter_history', pk=counter_id)


class IntervalDetailView(LoginRequiredMixin, DetailView):
    """Basic detail view for an interval (used for debugging/admin)."""
    model = TimeInterval
    template_name = 'time_tracking_main/interval_detail.html'
    context_object_name = 'interval'

    def get_queryset(self):
        """Restrict detail view to intervals of the requesting user."""
        return TimeInterval.objects.filter(counter__user=self.request.user)


# === СИСТЕМА ОЦЕНОК ПРОЕКТА ===

@method_decorator(csrf_exempt, name='dispatch')
class ProjectRatingView(LoginRequiredMixin, View):
    """Handle like/dislike rating for the project."""
    
    def post(self, request):
        """Submit or update project rating."""
        rating_type = request.POST.get('rating')
        comment = request.POST.get('comment', '')
        
        if rating_type not in ['like', 'dislike']:
            return HttpResponse('Неверный тип оценки', status=400)
        
        # Получаем или создаем оценку пользователя
        project_rating, created = ProjectRating.objects.get_or_create(
            user=request.user,
            defaults={'rating': rating_type, 'comment': comment}
        )
        
        # Обновляем существующую оценку
        if not created:
            project_rating.rating = rating_type
            project_rating.comment = comment
            project_rating.save()
        
        # Возвращаем обновленную статистику
        stats = self.get_rating_stats()
        
        if request.headers.get('HX-Request'):
            return render(request, 'time_tracking_main/partials/project_rating_stats.html', {
                'stats': stats,
                'user_rating': project_rating,
            })
        
        messages.success(request, 'Спасибо за вашу оценку!')
        return redirect('home')
    
    def get_rating_stats(self):
        """Get current project rating statistics."""
        from django.db.models import Count, Q
        stats = ProjectRating.objects.aggregate(
            total_likes=Count('id', filter=Q(rating='like')),
            total_dislikes=Count('id', filter=Q(rating='dislike')),
            total_ratings=Count('id')
        )
        return stats


@method_decorator(csrf_exempt, name='dispatch')
class SendFeedbackView(LoginRequiredMixin, View):
    """Send user feedback to email via Celery."""
    
    def post(self, request):
        """Queue feedback email for background processing."""
        comment = request.POST.get('comment', '').strip()
        
        if not comment:
            return HttpResponse('Комментарий не может быть пустым', status=400)
        
        try:
            # Получаем или создаем рейтинг пользователя
            project_rating, created = ProjectRating.objects.get_or_create(
                user=request.user,
                defaults={'rating': 'like', 'comment': comment}
            )
            
            # Обновляем комментарий если рейтинг уже существует
            if not created:
                project_rating.comment = comment
                project_rating.save()
            
            # Запускаем задачу отправки email в фоне
            from .tasks import send_feedback_email_task
            task = send_feedback_email_task.delay(request.user.id, comment)
            
            # Сразу отмечаем что email отправлен и сохраняем время
            project_rating.email_sent = True
            project_rating.email_sent_at = timezone.now()
            project_rating.celery_task_id = task.id
            project_rating.save()
            
            # Показываем сообщение об успешной отправке
            current_time = timezone.now().strftime('%d.%m.%Y %H:%M')
            message = f'Ваши пожелания отправлены разработчику ({current_time})'
            status = 200
                
        except Exception as e:
            message = f'Произошла ошибка при отправке: {str(e)}'
            status = 500
        
        if request.headers.get('HX-Request'):
            return render(request, 'time_tracking_main/partials/feedback_status.html', {
                'message': message,
                'success': status == 200,
            })
        
        if status == 200:
            messages.success(request, message)
        else:
            messages.error(request, message)
        return redirect('home')


@method_decorator(csrf_exempt, name='dispatch')
class CheckTaskStatusView(LoginRequiredMixin, View):
    """Check Celery task status."""
    
    def get(self, request, task_id):
        """Check task status and return result."""
        from celery.result import AsyncResult
        
        try:
            result = AsyncResult(task_id)
            
            response_data = {
                'task_id': task_id,
                'status': result.status,
                'ready': result.ready(),
            }
            
            if result.ready():
                if result.successful():
                    response_data.update({
                        'success': True,
                        'message': 'Ваши пожелания успешно отправлены разработчику! 📧',
                        'result': result.result
                    })
                else:
                    response_data.update({
                        'success': False,
                        'message': 'Ошибка при отправке пожеланий. Попробуйте позже.',
                        'error': str(result.result) if result.result else 'Неизвестная ошибка'
                    })
            else:
                response_data.update({
                    'success': None,
                    'message': 'Ваши пожелания обрабатываются...',
                })
            
            if request.headers.get('HX-Request'):
                return render(request, 'time_tracking_main/partials/task_status.html', response_data)
            
            from django.http import JsonResponse
            return JsonResponse(response_data)
            
        except Exception as e:
            error_data = {
                'task_id': task_id,
                'success': False,
                'message': 'Ошибка при проверке статуса отправки.',
                'error': str(e)
            }
            
            if request.headers.get('HX-Request'):
                return render(request, 'time_tracking_main/partials/task_status.html', error_data)
            
            from django.http import JsonResponse
            return JsonResponse(error_data, status=500)


def get_project_rating_context(user):
    """Get project rating context for templates."""
    user_rating = None
    if user.is_authenticated:
        try:
            user_rating = ProjectRating.objects.get(user=user)
        except ProjectRating.DoesNotExist:
            user_rating = None
    
    # Статистика оценок
    from django.db.models import Q, Count
    stats = ProjectRating.objects.aggregate(
        total_likes=Count('id', filter=Q(rating='like')),
        total_dislikes=Count('id', filter=Q(rating='dislike')),
        total_ratings=Count('id')
    )
    
    return {
        'user_rating': user_rating,
        'rating_stats': stats,
    }
