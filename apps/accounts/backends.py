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
from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache
from django.utils import timezone

from .models import ApprovalStatus, User, UserSource

logger = logging.getLogger(__name__)


def _coerce_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _extract_profile(data: dict, fallback_email: str) -> dict:
    """Best-effort field extraction from the StyleHR response matching custom_login."""
    if not isinstance(data, dict):
        data = {}

    # 1. Try to extract the firm abbreviation (prefix)
    prefix = ""
    if "store" in data and isinstance(data["store"], dict):
        firm = data["store"].get("firm")
        if isinstance(firm, dict):
            prefix = firm.get("abbreviation") or firm.get("prefix") or ""

    if not prefix:
        for key in ["prefix", "firm_abbreviation", "abbreviation", "firm_prefix"]:
            if key in data and data[key]:
                prefix = str(data[key]).strip()
                break

    if not prefix:
        for parent_key in ["user", "employee", "data", "profile", "firm", "store"]:
            if parent_key in data and isinstance(data[parent_key], dict):
                p_dict = data[parent_key]
                for key in ["prefix", "firm_abbreviation", "abbreviation", "firm_prefix"]:
                    if key in p_dict and p_dict[key]:
                        prefix = str(p_dict[key]).strip()
                        break
                if prefix:
                    break

    # 2. Extract employee code
    code = data.get("employee_code") or ""
    if not code:
        for parent_key in ["user", "employee", "data", "profile"]:
            if parent_key in data and isinstance(data[parent_key], dict):
                code = data[parent_key].get("employee_code") or data[parent_key].get("code") or ""
                if code:
                    break

    # Build employee ID
    emp_id = None
    if code:
        emp_id = str(code).strip()

    # Fallback for emp_id if still not found
    if not emp_id:
        for key in ["employee_id", "emp_id", "employee_code", "emp_code", "code"]:
            if key in data and data[key]:
                emp_id = str(data[key]).strip()
                break

    if not emp_id and "@" not in fallback_email:
        emp_id = fallback_email

    # If prefix is present, format employee code with prefix (e.g. RR-9701 or 97-9701)
    if emp_id and prefix:
        prefix = str(prefix).strip()
        if not (emp_id.lower().startswith(f"{prefix.lower()}-") or emp_id.lower() == prefix.lower()):
            emp_id = f"{prefix}-{emp_id}"

    # 3. Extract Email
    retrieved_email = None
    for key in ["email", "email_address", "official_email", "personal_email"]:
        if key in data and data[key]:
            retrieved_email = str(data[key]).strip().lower()
            break
    if not retrieved_email:
        for parent_key in ["user", "employee", "data", "profile"]:
            if parent_key in data and isinstance(data[parent_key], dict):
                parent_data = data[parent_key]
                for key in ["email", "email_address", "official_email", "personal_email"]:
                    if key in parent_data and parent_data[key]:
                        retrieved_email = str(parent_data[key]).strip().lower()
                        break
                if retrieved_email:
                    break

    email = retrieved_email if retrieved_email else (fallback_email.lower() if "@" in fallback_email else "")

    # 4. Extract full name
    full_name = ""
    login_username = data.get("username") or ""
    if login_username and "@" not in str(login_username) and not any(char.isdigit() for char in str(login_username)):
        full_name = str(login_username).strip()

    if not full_name:
        for key in ["name", "full_name", "employee_name", "emp_name", "display_name", "displayName", "fullName"]:
            if key in data and data[key]:
                val = str(data[key]).strip()
                if not val.upper().startswith("RR-") or not full_name:
                    full_name = val
                    if not val.upper().startswith("RR-"):
                        break
    if not full_name:
        for parent_key in ["user", "employee", "data", "profile"]:
            if parent_key in data and isinstance(data[parent_key], dict):
                parent_data = data[parent_key]
                for key in ["name", "full_name", "employee_name", "emp_name", "display_name", "displayName", "fullName"]:
                    if key in parent_data and parent_data[key]:
                        val = str(parent_data[key]).strip()
                        if not val.upper().startswith("RR-") or not full_name:
                            full_name = val
                            if not val.upper().startswith("RR-"):
                                break
                if full_name and not full_name.upper().startswith("RR-"):
                    break

    if (not full_name or full_name.upper().startswith("RR-")) and email:
        prefix_part = email.split("@")[0].split("+")[0]
        cleaned = "".join(c if c.isalpha() else " " for c in prefix_part).strip()
        name_from_email = " ".join(word.capitalize() for word in cleaned.split())
        if name_from_email:
            full_name = name_from_email

    phone = _coerce_str(
        data.get("phone") or data.get("mobile") or data.get("Mobile")
    )
    return {
        "email": email or fallback_email.lower(),
        "full_name": full_name or email or fallback_email,
        "employee_id": str(emp_id or "").strip(),
        "phone": phone,
    }


def _cache_credentials(username: str, password: str, profile: dict) -> None:
    """Store securely hashed credentials and profile in Redis for offline/API-outage fallback."""
    try:
        ttl = getattr(settings, "STYLEHR_CACHE_TTL", 7 * 86400)
        cache_data = {
            "password_hash": make_password(password),
            "profile": profile,
            "cached_at": timezone.now().isoformat(),
        }
        keys_to_set = set()
        if username:
            keys_to_set.add(f"stylehr_cred:{username.strip().lower()}")
        if profile.get("employee_id"):
            emp_id = profile["employee_id"].strip().lower()
            keys_to_set.add(f"stylehr_cred:{emp_id}")
            if "-" in emp_id:
                keys_to_set.add(f"stylehr_cred:{emp_id.split('-', 1)[1]}")
        if profile.get("email"):
            keys_to_set.add(f"stylehr_cred:{profile['email'].strip().lower()}")

        for k in keys_to_set:
            cache.set(k, cache_data, timeout=ttl)
        logger.info("Cached StyleHR credentials in Redis for %s (TTL: %ds)", username, ttl)
    except Exception as exc:
        logger.warning("Failed to cache StyleHR credentials in Redis: %s", exc)


def _get_cached_credentials(username: str) -> dict | None:
    """Look up cached StyleHR credentials from Redis by username / employee code / email."""
    try:
        typed = (username or "").strip().lower()
        if not typed:
            return None
        # 1. Direct key match (e.g. stylehr_cred:rr-3571 or stylehr_cred:3571)
        data = cache.get(f"stylehr_cred:{typed}")
        if data:
            return data
        # 2. Check if a local StyleHR user has an employee_id ending with typed numeric code
        user_match = User.objects.filter(employee_id__iendswith=f"-{typed}", source=UserSource.STYLEHR).first()
        if user_match and user_match.employee_id:
            data = cache.get(f"stylehr_cred:{user_match.employee_id.lower()}")
            if data:
                return data
        return None
    except Exception as exc:
        logger.warning("Redis cache lookup failed: %s", exc)
        return None


class EmployeeIdBackend(ModelBackend):
    """App sign-in against local passwords: a local account's name (e.g. "karthik", "Allen Samuel"),
    or an Employee ID (e.g. RR-21747, or just 21747) + password."""

    def authenticate(self, request, username: str | None = None, password: str | None = None, **kwargs):
        username = (username or "").strip()
        if not username or not password or "@" in username:
            return None
        # Local accounts by name; only when exactly one local account has that name.
        matches = list(User.objects.filter(source=UserSource.LOCAL, full_name__iexact=username)[:2])
        if len(matches) != 1:
            matches = list(User.objects.filter(employee_id__iexact=username)[:2])
        if not matches:
            # Typing only the number finds "<PREFIX>-<number>", but only if exactly one user has it.
            matches = list(User.objects.filter(employee_id__iendswith=f"-{username}")[:2])
        if len(matches) != 1:
            return None
        user = matches[0]
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None


class StyleHRBackend(ModelBackend):
    """Authenticate against the StyleHR API and mirror the user locally."""

    def _authenticate_from_cache(self, username: str, password: str) -> User | None:
        """Authenticate using credentials cached in Redis when StyleHR API is down."""
        cached = _get_cached_credentials(username)
        if not cached:
            logger.info("No cached StyleHR credentials found in Redis for %s", username)
            return None

        password_hash = cached.get("password_hash")
        if not password_hash or not check_password(password, password_hash):
            logger.warning("Cached StyleHR credentials password mismatch for %s", username)
            return None

        profile = cached.get("profile") or {}
        email = profile.get("email")
        if not email:
            return None

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "full_name": profile.get("full_name", email),
                "phone": profile.get("phone", ""),
                "employee_id": profile.get("employee_id", ""),
                "source": UserSource.STYLEHR,
                "approval_status": ApprovalStatus.PENDING,
                "is_active": True,
            },
        )
        if created:
            user.set_unusable_password()
            user.save(update_fields=["password"])

        logger.warning(
            "StyleHR API unreachable/down; successfully authenticated user %s via cached Redis credentials",
            email,
        )
        return user if self.user_can_authenticate(user) else None

    def authenticate(self, request, username: str | None = None, password: str | None = None, **kwargs):
        if not username or not password:
            return None
        # Locally created accounts sign in locally; never send their password to StyleHR.
        typed = username.strip()
        local_lookup = User.objects.filter(source=UserSource.LOCAL)
        if (
            local_lookup.filter(full_name__iexact=typed).exists()
            or local_lookup.filter(email__iexact=typed).exists()
            or local_lookup.filter(employee_id__iexact=typed).exclude(employee_id="").exists()
        ):
            return None
        url = getattr(settings, "STYLEHR_API_URL", "").strip()
        if not url:
            return self._authenticate_from_cache(username, password)

        api_failed = False
        resp = None
        try:
            resp = requests.post(
                url,
                json={"email": username, "password": password},
                timeout=getattr(settings, "STYLEHR_API_TIMEOUT", 8),
            )
            if resp.status_code >= 500:
                logger.warning("StyleHR API returned HTTP %s (server error)", resp.status_code)
                api_failed = True
        except requests.RequestException as exc:
            logger.warning("StyleHR API unreachable: %s", exc)
            api_failed = True

        if api_failed:
            logger.info("StyleHR API unavailable; attempting fallback to Redis cache for %s", username)
            return self._authenticate_from_cache(username, password)

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

        # Cache credentials in Redis for future API outages
        _cache_credentials(username, password, profile)

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
            if profile["employee_id"] and (not user.employee_id or user.employee_id.isdigit() or user.employee_id != profile["employee_id"]):
                user.employee_id = profile["employee_id"]
                updates.append("employee_id")
            if profile["phone"] and not user.phone:
                user.phone = profile["phone"]
                updates.append("phone")
            if profile["full_name"] and (not user.full_name or user.full_name == user.email or user.full_name.upper().startswith("RR-")):
                user.full_name = profile["full_name"]
                updates.append("full_name")
            if updates:
                user.save(update_fields=updates)

        return user if self.user_can_authenticate(user) else None
