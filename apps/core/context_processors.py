"""Template context shared by every page."""
from __future__ import annotations


def notifications(request) -> dict:
    """Counts for the sidebar notification badges."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}

    from apps.accounts.models import ApprovalStatus, User
    from apps.actions.models import ActionItem, ActionStatus

    new_actions = ActionItem.objects.filter(
        owner=user,
        seen_at__isnull=True,
        status__in=[ActionStatus.OPEN, ActionStatus.IN_PROGRESS],
    ).count()
    pending_users = (
        User.objects.filter(approval_status=ApprovalStatus.PENDING).count() if user.is_hq_admin else 0
    )
    return {
        "notif_new_actions": new_actions,
        "notif_pending_users": pending_users,
    }
