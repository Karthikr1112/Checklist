"""Authentication backends.

Tries StyleHR HR system first; if that fails we fall back to Django's
ModelBackend (configured in settings).
"""
from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings
from django.contrib.auth.backends import ModelBackend

from .models import ApprovalStatus, User, UserSource

logger = logging.getLogger(__name__)


def _coerce_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _extract_profile(payload: dict, fallback_email: str) -> dict:
    """Best-effort field extraction from the StyleHR response."""
    email = _coerce_str(
        payload.get("email")
        or payload.get("Email")
        or payload.get("employee_email")
        or fallback_email
    ).lower()
    full_name = _coerce_str(
        payload.get("name")
        or payload.get("full_name")
        or payload.get("employee_name")
        or payload.get("EmployeeName")
        or fallback_email
    )
    employee_id = _coerce_str(
        payload.get("employee_id")
        or payload.get("emp_id")
        or payload.get("EmployeeID")
        or payload.get("employee_code")
        or payload.get("id")
    )
    phone = _coerce_str(
        payload.get("phone") or payload.get("mobile") or payload.get("Mobile")
    )
    return {
        "email": email,
        "full_name": full_name or email,
        "employee_id": employee_id,
        "phone": phone,
    }


class StyleHRBackend(ModelBackend):
    """Authenticate against the StyleHR API and mirror the user locally."""

    def authenticate(self, request, username: str | None = None, password: str | None = None, **kwargs):
        if not username or not password:
            return None
        url = getattr(settings, "STYLEHR_API_URL", "").strip()
        if not url:
            return None

        try:
            resp = requests.post(
                url,
                json={"email": username, "password": password},
                timeout=getattr(settings, "STYLEHR_API_TIMEOUT", 8),
            )
        except requests.RequestException as exc:
            logger.warning("StyleHR API unreachable: %s", exc)
            return None

        if resp.status_code != 200:
            return None

        # The API returns the literal string "Invalid username/password" on failure.
        body_text = (resp.text or "").strip()
        if "invalid" in body_text.lower() and "password" in body_text.lower():
            return None

        try:
            data = resp.json()
        except ValueError:
            return None
        if not isinstance(data, dict):
            return None
        if data.get("error") or data.get("status") in ("error", "fail", "failed"):
            return None

        profile = _extract_profile(data, fallback_email=username)
        if not profile["email"]:
            return None

        user, created = User.objects.get_or_create(
            email=profile["email"],
            defaults={
                "full_name": profile["full_name"],
                "phone": profile["phone"],
                "employee_id": profile["employee_id"],
                "source": UserSource.STYLEHR,
                "approval_status": ApprovalStatus.PENDING,
                "is_active": True,
            },
        )
        if created:
            user.set_unusable_password()
            user.save(update_fields=["password"])
        else:
            updates: list[str] = []
            if profile["employee_id"] and not user.employee_id:
                user.employee_id = profile["employee_id"]
                updates.append("employee_id")
            if profile["phone"] and not user.phone:
                user.phone = profile["phone"]
                updates.append("phone")
            if profile["full_name"] and user.full_name in ("", user.email):
                user.full_name = profile["full_name"]
                updates.append("full_name")
            if updates:
                user.save(update_fields=updates)

        return user if self.user_can_authenticate(user) else None
