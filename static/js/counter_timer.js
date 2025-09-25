(function() {
    function pad(num) {
        return num.toString().padStart(2, '0');
    }

    function formatDuration(totalSeconds) {
        const hours = Math.floor(totalSeconds / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        const seconds = totalSeconds % 60;
        return `${hours} ч ${pad(minutes)} мин ${pad(seconds)} секунд`;
    }

    function animateTick(element) {
        if (!element) return;
        element.classList.remove('tick-animate');
        element.classList.add('tick-animate');
        setTimeout(() => element.classList.remove('tick-animate'), 600);
    }

    function startTimer(element) {
        const startIso = element.dataset.start;
        if (!startIso) return;
        const startTime = new Date(startIso);
        if (Number.isNaN(startTime.getTime())) return;
        const offsetSeconds = parseFloat(element.dataset.offset || '0');

        function tick() {
            const now = new Date();
            const diffSeconds = Math.max(0, Math.floor((now - startTime) / 1000) + offsetSeconds);
            element.textContent = formatDuration(diffSeconds);
            animateTick(element);
        }

        tick();
        return setInterval(tick, 1000);
    }

    function initTimers(root) {
        const scope = root || document;
        const timers = scope.querySelectorAll('[data-interval-timer]');
        timers.forEach(el => {
            if (el.dataset.timerInitialized) return;
            if (!el.dataset.start) return;
            const intervalId = startTimer(el);
            if (intervalId) {
                el.dataset.intervalId = intervalId;
                el.dataset.timerInitialized = 'true';
            }
        });
    }

    function startAggregateTimer(element) {
        if (element.dataset.totalTimerInitialized) {
            return;
        }
        const baseSeconds = parseInt(element.dataset.totalBase || '0', 10);
        const startIso = element.dataset.totalStart;
        const startTime = startIso ? new Date(startIso) : null;

        const tick = () => {
            let totalSeconds = Number.isNaN(baseSeconds) ? 0 : baseSeconds;
            if (startTime && !Number.isNaN(startTime.getTime())) {
                const now = new Date();
                totalSeconds += Math.max(0, Math.floor((now - startTime) / 1000));
            }
            element.textContent = formatDuration(totalSeconds);
            animateTick(element);
        };

        tick();

        if (startTime && !Number.isNaN(startTime.getTime())) {
            const intervalId = setInterval(tick, 1000);
            element.dataset.totalIntervalId = intervalId;
        }
        element.dataset.totalTimerInitialized = 'true';
    }

    function initTotals(root) {
        const scope = root || document;
        const totals = scope.querySelectorAll('[data-total-duration]');
        totals.forEach(startAggregateTimer);
    }

    function animateTotals(root) {
        const scope = root || document;
        scope.querySelectorAll('[data-total-duration]').forEach((el) => {
            el.classList.add('badge-highlight');
            setTimeout(() => el.classList.remove('badge-highlight'), 1200);
        });
    }

    function initAlerts(root) {
        const scope = root || document;
        const alerts = scope.querySelectorAll('.alert');
        alerts.forEach((alert) => {
            if (alert.dataset.alertInit) return;
            alert.dataset.alertInit = 'true';

            const removeAlert = () => {
                alert.classList.remove('show');
                setTimeout(() => {
                    if (alert.parentElement) {
                        alert.remove();
                    }
                }, 200);
            };

            const closeBtn = alert.querySelector('[data-bs-dismiss="alert"]');
            if (closeBtn) {
                closeBtn.addEventListener('click', (event) => {
                    event.preventDefault();
                    removeAlert();
                });
            }

            const autoTimeout = parseInt(alert.dataset.dismissTimeout || '5000', 10);
            if (autoTimeout > 0) {
                setTimeout(removeAlert, autoTimeout);
            }
        });
    }

    function initDropdowns(root) {
        const scope = root || document;
        const toggles = scope.querySelectorAll('[data-bs-toggle="dropdown"]');
        toggles.forEach((toggle) => {
            if (toggle.dataset.dropdownInit) return;
            toggle.dataset.dropdownInit = 'true';

            if (window.bootstrap && bootstrap.Dropdown) {
                bootstrap.Dropdown.getOrCreateInstance(toggle);
                return;
            }

            const menu = toggle.nextElementSibling;
            if (!menu) return;

            const closeMenu = (event) => {
                if (!menu.classList.contains('show')) return;
                if (!toggle.contains(event.target) && !menu.contains(event.target)) {
                    menu.classList.remove('show');
                }
            };

            toggle.addEventListener('click', (event) => {
                event.preventDefault();
                menu.classList.toggle('show');
            });

            document.addEventListener('click', closeMenu);
        });
    }

    function setLoadingState(form, isLoading) {
        if (!form) return;
        const button = form.querySelector('button');
        if (!button) return;
        if (isLoading) {
            button.dataset.wasDisabled = button.disabled ? 'true' : 'false';
            button.classList.add('is-loading');
            button.disabled = true;
        } else {
            button.classList.remove('is-loading');
            if (button.dataset.wasDisabled !== 'true') {
                button.disabled = false;
            }
            delete button.dataset.wasDisabled;
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        initTimers(document);
        initTotals(document);
        animateTotals(document);
        initAlerts(document);
        initDropdowns(document);
    });
    document.body.addEventListener('htmx:beforeRequest', (event) => {
        const form = event.detail && event.detail.elt;
        if (!form || !form.classList || !form.classList.contains('counter-action-form')) {
            return;
        }
        setLoadingState(form, true);
    });
    document.body.addEventListener('htmx:afterRequest', (event) => {
        const form = event.detail && event.detail.elt;
        if (!form || !form.classList || !form.classList.contains('counter-action-form')) {
            return;
        }
        // If form still exists (request may have failed), restore button state.
        if (document.body.contains(form)) {
            setLoadingState(form, false);
        }
    });
    document.body.addEventListener('htmx:responseError', (event) => {
        const form = event.detail && event.detail.elt;
        if (!form || !form.classList || !form.classList.contains('counter-action-form')) {
            return;
        }
        setLoadingState(form, false);
    });
    document.body.addEventListener('htmx:afterSwap', (event) => {
        initTimers(event.target);
        initTotals(event.target);
        animateTotals(event.target);
        initAlerts(event.target);
        initDropdowns(event.target);
    });
})();
