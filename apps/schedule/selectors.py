from __future__ import annotations

from django.db.models import Q

from apps.accounts.models import Role

from .models import VisitPlan


def plans_visible_to(user):
    qs = VisitPlan.objects.select_related("store", "cluster_manager", "visit")
    if user.is_admin_role:
        return qs
    if user.role == Role.CLUSTER_MANAGER:
        return qs.filter(cluster_manager=user)
    if user.role == Role.INVENTORY_TEAM:
        return qs.filter(cluster_manager=user)
    if user.role == Role.MARKETING_TEAM:
        return qs.filter(cluster_manager=user)
    if user.role == Role.STORE_MANAGER:
        return qs.filter(store__store_manager=user)
    return qs.filter(Q(cluster_manager=user) | Q(store__store_manager=user))
