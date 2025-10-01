"""Middleware providing guest auto-login based on client IP."""

from __future__ import annotations

import hashlib
from typing import Optional

from django.contrib.auth import get_user_model, login
from django.db import transaction
from django.http import HttpRequest
from django.utils.deprecation import MiddlewareMixin


def _client_ip(request: HttpRequest) -> Optional[str]:
    """Extract client IP from request headers."""
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip() or None
    return request.META.get("REMOTE_ADDR")


class GuestIPAuthenticationMiddleware(MiddlewareMixin):
    """Authenticate anonymous visitors as guest users linked to their IP."""

    session_flag = "guest_user_id"

    def process_request(self, request: HttpRequest) -> None:  # noqa: D401
        if getattr(request, "user", None) and request.user.is_authenticated:
            return

        client_ip = _client_ip(request)
        if not client_ip:
            return

        guest_user = self._get_or_create_guest(client_ip)
        backend = "django.contrib.auth.backends.ModelBackend"
        guest_user.backend = backend
        login(request, guest_user, backend=backend)
        request.session["is_guest"] = True
        request.session["guest_ip"] = client_ip
        request.session[self.session_flag] = guest_user.id

    def _get_or_create_guest(self, client_ip: str):
        """Create (or reuse) a guest account keyed by IP hash."""
        user_model = get_user_model()
        suffix = hashlib.sha256(client_ip.encode("utf-8")).hexdigest()[:12]
        username = f"guest_{suffix}"
        with transaction.atomic():
            guest_user, created = user_model.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": "Гость",
                    "is_active": True,
                },
            )
            if created:
                guest_user.set_unusable_password()
                guest_user.save(update_fields=["password"])
        return guest_user
