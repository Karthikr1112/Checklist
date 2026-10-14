from __future__ import annotations

from django.db.models import Q

from apps.accounts.models import Role
from apps.stores.selectors import stores_visible_to

from .models import VisitPlan


def plans_visible_to(user):
    qs = VisitPlan.objects.select_related("store", "cluster_manager", "visit")
    if user.is_admin_role:
        return qs
    if user.role == Role.CLUSTER_MANAGER:
        # Their own plans plus every team's plans at their assigned stores.
        return qs.filter(Q(cluster_manager=user) | Q(store__in=stores_visible_to(user)))
    if user.role in (Role.INVENTORY_TEAM, Role.MARKETING_TEAM, Role.VM_TEAM, Role.GROCERY_HOME):
        return qs.filter(cluster_manager=user)
    if user.role == Role.STORE_MANAGER:
        return qs.filter(store__in=stores_visible_to(user))
    return qs.filter(Q(cluster_manager=user) | Q(store__in=stores_visible_to(user)))
