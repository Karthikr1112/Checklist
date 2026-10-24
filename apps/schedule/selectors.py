from __future__ import annotations

from django.db.models import Q

from apps.accounts.models import Role
from apps.stores.selectors import stores_visible_to

from .models import VisitPlan


def plans_visible_to(user):
    qs = VisitPlan.objects.select_related("store", "cluster_manager", "created_by", "template", "visit")
    if user.is_admin_role:
        return qs

    # Department heads see all plans created for their team members or created by themselves
    if getattr(user, "is_marketing_head", False):
        return qs.filter(Q(cluster_manager__role=Role.MARKETING_TEAM) | Q(created_by=user) | Q(cluster_manager=user))
    if getattr(user, "is_vm_manager", False):
        return qs.filter(Q(cluster_manager__role=Role.VM_TEAM) | Q(created_by=user) | Q(cluster_manager=user))
    if getattr(user, "is_grocery_home_head", False):
        return qs.filter(Q(cluster_manager__role=Role.GROCERY_HOME) | Q(created_by=user) | Q(cluster_manager=user))

    if user.role == Role.CLUSTER_MANAGER:
        # Their own plans plus every team's plans at their assigned stores.
        return qs.filter(Q(cluster_manager=user) | Q(store__in=stores_visible_to(user)))
    if user.role in (Role.INVENTORY_TEAM, Role.MARKETING_TEAM, Role.VM_TEAM, Role.GROCERY_HOME):
        return qs.filter(cluster_manager=user)
    if user.role == Role.STORE_MANAGER:
        return qs.filter(Q(cluster_manager=user) | Q(store__in=stores_visible_to(user)))
    return qs.filter(Q(cluster_manager=user) | Q(store__in=stores_visible_to(user)))
