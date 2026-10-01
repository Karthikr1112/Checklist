"""Aggregations for the dashboard."""
from __future__ import annotations

from django.db.models import Avg, Count, Q

from apps.accounts.models import User
from apps.actions.models import ActionItem, ActionStatus
from apps.visits.models import Visit, VisitStatus
from apps.visits.selectors import visits_visible_to


def dashboard_summary(user: User) -> dict:
    visits = visits_visible_to(user)
    total_visits = visits.count()

    status_breakdown = visits.values("status").order_by().annotate(count=Count("id"))
    avg_compliance = visits.aggregate(avg=Avg("compliance_pct"))["avg"] or 0

    actions_qs = ActionItem.objects.filter(response__visit__in=visits)
    open_actions = actions_qs.filter(status__in=[ActionStatus.OPEN, ActionStatus.IN_PROGRESS]).count()
    closed_actions = actions_qs.filter(status=ActionStatus.CLOSED).count()

    recent_visits = visits.order_by("-visit_date")[:10]

    return {
        "total_visits": total_visits,
        "status_breakdown": list(status_breakdown),
        "avg_compliance": round(float(avg_compliance), 2),
        "open_actions": open_actions,
        "closed_actions": closed_actions,
        "recent_visits": recent_visits,
        "submitted_pending": visits.filter(status=VisitStatus.SUBMITTED).count(),
    }
