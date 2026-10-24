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
    if user.is_vm_team:
        if getattr(user, "is_vm_manager", False):
            return qs.filter(
                Q(cluster_manager=user)
                | Q(template__audience=ChecklistTemplate.Audience.VM_TEAM)
                | Q(cluster_manager__role=Role.VM_TEAM)
            )
        return qs.filter(cluster_manager=user)
    if user.is_grocery_home:
        if getattr(user, "is_business_head", False):
            # Head of Grocery & Home: every Grocery & Home audit, plus their own.
            return qs.filter(
                Q(cluster_manager=user)
                | Q(template__audience=ChecklistTemplate.Audience.GROCERY_HOME)
                | Q(cluster_manager__role=Role.GROCERY_HOME)
            )
        return qs.filter(cluster_manager=user)
    if user.is_cluster_manager:
        # Their own audits plus every team's audits at their assigned stores.
        return qs.filter(Q(cluster_manager=user) | Q(store__in=stores_visible_to(user)))
    if user.is_inventory_team:
        return qs.filter(cluster_manager=user)
    if user.is_store_manager:
        # Their own audits plus every team's audits at their assigned stores.
        return qs.filter(Q(cluster_manager=user) | Q(store__in=stores_visible_to(user)))
    return qs.none()
