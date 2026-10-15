"""Record audit-log entries. Logging must never break the action being logged."""
from __future__ import annotations

import logging

from .models import AuditLog

logger = logging.getLogger(__name__)

Action = AuditLog.Action


def _client_ip(request) -> str | None:
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    ip = forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR", "")
    return ip or None


def user_label(user) -> str:
    if user is None or not getattr(user, "is_authenticated", False):
        return ""
    return getattr(user, "employee_label", "") or getattr(user, "full_name", "") or str(user)


def diff(before: dict, after: dict) -> dict:
    """{field: [old, new]} for the fields whose value changed."""
    return {k: [before.get(k), after.get(k)] for k in after if before.get(k) != after.get(k)}


def log_event(
    request,
    action: str,
    obj=None,
    *,
    label: str = "",
    details: str = "",
    changes: dict | None = None,
    actor=None,
    actor_label: str = "",
) -> None:
    try:
        if actor is None and request is not None and getattr(request.user, "is_authenticated", False):
            actor = request.user
        AuditLog.objects.create(
            actor=actor if getattr(actor, "pk", None) else None,
            actor_label=(actor_label or user_label(actor))[:200],
            action=action,
            object_type=type(obj).__name__ if obj is not None else "",
            object_id=str(getattr(obj, "pk", "") or "")[:64],
            object_label=(label or (str(obj) if obj is not None else ""))[:255],
            details=details,
            changes={k: [str(v[0]) if v[0] is not None else "", str(v[1]) if v[1] is not None else ""] for k, v in (changes or {}).items()},
            ip_address=_client_ip(request),
            user_agent=(request.META.get("HTTP_USER_AGENT", "") if request is not None else "")[:255],
        )
    except Exception:  # pragma: no cover - never let auditing break the request
        logger.exception("Could not write audit log entry for %s", action)
