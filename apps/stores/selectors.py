"""Read-only query helpers for Stores."""
from django.db.models import QuerySet

from apps.accounts.models import User

from .models import Store


def stores_visible_to(user: User) -> QuerySet[Store]:
    if not user or not user.is_authenticated:
        return Store.objects.none()

    qs = Store.objects.filter(is_active=True).select_related("cluster_manager", "store_manager")
    if user.is_admin_role or getattr(user, "all_stores_access", False):
        return qs

    if (user.is_marketing_team and getattr(user, "is_marketing_head", False)) or getattr(user, "is_vm_manager", False) or getattr(user, "is_business_head", False):
        assigned = user.assigned_stores.filter(is_active=True)
        if assigned.exists():
            return assigned
        return qs

    # Check Many-to-Many assigned stores
    assigned = user.assigned_stores.filter(is_active=True)
    if assigned.exists():
        return assigned

    # Fallback to legacy single-user FKs
    if user.is_cluster_manager:
        return qs.filter(cluster_manager=user)
    if user.is_store_manager:
        return qs.filter(store_manager=user)
    if user.is_inventory_team:
        return qs.filter(inventory_team=user)
    if user.is_marketing_team:
        return qs.filter(marketing_team=user)

    return Store.objects.none()
