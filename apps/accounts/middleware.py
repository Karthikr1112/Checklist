"""Gate users whose accounts are not yet approved."""
from __future__ import annotations

from django.shortcuts import redirect
from django.urls import resolve, reverse, Resolver404

from .models import ApprovalStatus


_ALLOWED_URL_NAMES = {
    "accounts:pending_approval",
    "accounts:logout",
    "accounts:login",
}


class ApprovalRequiredMiddleware:
    """Redirect non-approved, non-superuser users to a pending page."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and not user.is_superuser:
            if getattr(user, "approval_status", ApprovalStatus.APPROVED) != ApprovalStatus.APPROVED:
                # Use path_info so this works under a sub-path deploy (e.g. /cl)
                path = request.path_info
                if not (
                    path.startswith("/static/")
                    or path.startswith("/media/")
                    or path.startswith("/admin/")
                ):
                    try:
                        match = resolve(path)
                        current_name = f"{match.namespace}:{match.url_name}" if match.namespace else match.url_name
                    except Resolver404:
                        current_name = None
                    if current_name not in _ALLOWED_URL_NAMES:
                        return redirect(reverse("accounts:pending_approval"))
        return self.get_response(request)
