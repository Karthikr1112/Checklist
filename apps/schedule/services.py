from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.checklists.models import ChecklistTemplate
from apps.visits.services import start_visit

from .models import PlanStatus, VisitPlan


def templates_for_user(user) -> list[ChecklistTemplate]:
    """Return the checklist template(s) mapped to this user's role and sub-role."""
    if not user:
        return []
    qs = ChecklistTemplate.objects.filter(is_active=True)
    if user.is_inventory_team:
        return list(qs.filter(audience=ChecklistTemplate.Audience.INVENTORY_TEAM))
    if user.is_marketing_team:
        if user.marketing_role:
            matches = list(qs.filter(audience=ChecklistTemplate.Audience.MARKETING_TEAM, name__icontains=user.marketing_role))
            if matches:
                return matches
        return list(qs.filter(audience=ChecklistTemplate.Audience.MARKETING_TEAM))
    if user.is_vm_team:
        if user.vm_role:
            matches = list(qs.filter(audience=ChecklistTemplate.Audience.VM_TEAM, name__icontains=user.vm_role))
            if matches:
                return matches
        return list(qs.filter(audience=ChecklistTemplate.Audience.VM_TEAM))
    if user.is_grocery_home:
        if user.gh_role:
            matches = list(qs.filter(audience=ChecklistTemplate.Audience.GROCERY_HOME, name__icontains=user.gh_role))
            if matches:
                return matches
        return list(qs.filter(audience=ChecklistTemplate.Audience.GROCERY_HOME))
    if user.is_store_manager:
        return list(qs.filter(audience=ChecklistTemplate.Audience.STORE_MANAGER))
    return list(qs.filter(audience=ChecklistTemplate.Audience.CLUSTER_MANAGER))


def resolve_template_for_user(user) -> ChecklistTemplate | None:
    templates = templates_for_user(user)
    return templates[0] if templates else None


@transaction.atomic
def start_visit_from_plan(
    *,
    plan: VisitPlan,
    user,
    started_latitude=None,
    started_longitude=None,
    started_distance_meters=None,
) -> VisitPlan:
    """Create a Visit linked to this plan and flip status to CHECKED_IN."""
    if plan.visit_id:
        return plan
    template = plan.template or resolve_template_for_user(plan.cluster_manager)
    if template is None:
        raise ValueError("No active checklist template available.")
    visit = start_visit(
        store=plan.store,
        template=template,
        cluster_manager=plan.cluster_manager,
        visit_date=plan.planned_date,
        audit_type=plan.audit_type,
        started_latitude=started_latitude,
        started_longitude=started_longitude,
        started_distance_meters=started_distance_meters,
    )
    plan.visit = visit
    plan.status = PlanStatus.CHECKED_IN
    plan.save(update_fields=["visit", "status", "updated_at"])
    return plan


def mark_past_plans_missed():
    """Sweep PLANNED rows in the past with no linked visit → MISSED."""
    today = timezone.localdate()
    return VisitPlan.objects.filter(
        status=PlanStatus.PLANNED, planned_date__lt=today, visit__isnull=True
    ).update(status=PlanStatus.MISSED)
