"""Cross-cutting helpers reused by other apps."""
from __future__ import annotations

from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def role_required(*roles: str):
    """Allow only users whose `role` matches any provided role."""

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if request.user.role not in roles and not request.user.is_superuser:
                messages.error(request, "You do not have permission to view that page.")
                return redirect("dashboard:index")
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator
