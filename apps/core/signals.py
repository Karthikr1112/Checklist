"""Login / logout / failed-login entries for the audit log."""
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from .audit import Action, log_event


@receiver(user_logged_in)
def _on_login(sender, request, user, **kwargs):
    source = getattr(user, "get_source_display", lambda: "")()
    log_event(request, Action.LOGIN, actor=user, label=user.employee_label, details=f"Signed in ({source})")


@receiver(user_logged_out)
def _on_logout(sender, request, user, **kwargs):
    if user is not None:
        log_event(request, Action.LOGOUT, actor=user, label=user.employee_label)


@receiver(user_login_failed)
def _on_login_failed(sender, credentials, request=None, **kwargs):
    typed = str(credentials.get("username", ""))[:100]  # Django already strips the password out
    log_event(request, Action.LOGIN_FAILED, actor_label=typed, label=typed, details="Wrong ID / name or password")
