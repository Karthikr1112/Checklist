"""Read queries for Visits."""
from __future__ import annotations

from django.db.models import Q, QuerySet

from apps.accounts.models import Role, User
from apps.checklists.models import ChecklistTemplate
from apps.stores.selectors import stores_visible_to

from .models import Visit


def visits_visible_to(user: User) -> QuerySet[Visit]:
    qs = Visit.objects.select_related("store", "cluster_manager", "template")
    if user.is_admin_role:
        return qs
    if user.is_marketing_team:
        if getattr(user, "is_marketing_head", False):
            return qs.filter(
                Q(cluster_manager=user)
                | Q(template__audience=ChecklistTemplate.Audience.MARKETING_TEAM)
                | Q(cluster_manager__role=Role.MARKETING_TEAM)
            )
        return qs.filter(cluster_manager=user)
    if user.is_cluster_manager or user.is_inventory_team:
        return qs.filter(cluster_manager=user)
    if user.is_store_manager:
        return qs.filter(store__in=stores_visible_to(user))
    return qs.none()
