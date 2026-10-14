from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.checklists.models import ChecklistTemplate
from apps.visits.services import start_visit

from .models import PlanStatus, VisitPlan


@transaction.atomic
def start_visit_from_plan(*, plan: VisitPlan, user) -> VisitPlan:
    """Create a Visit linked to this plan and flip status to CHECKED_IN."""
    if plan.visit_id:
        return plan
    templates = ChecklistTemplate.objects.filter(is_active=True)
    if user is not None and not user.is_admin_role:
        if user.is_inventory_team:
            templates = templates.filter(audience=ChecklistTemplate.Audience.INVENTORY_TEAM)
        elif user.is_marketing_team:
            templates = templates.filter(audience=ChecklistTemplate.Audience.MARKETING_TEAM)
        elif user.is_vm_team:
            templates = templates.filter(audience=ChecklistTemplate.Audience.VM_TEAM)
            if user.vm_role:
                templates = templates.filter(name__icontains=user.vm_role)
        elif user.is_grocery_home:
            templates = templates.filter(audience=ChecklistTemplate.Audience.GROCERY_HOME)
            if user.gh_role:
                templates = templates.filter(name__icontains=user.gh_role)
        else:
            templates = templates.filter(audience=ChecklistTemplate.Audience.CLUSTER_MANAGER)
    template = templates.order_by("-version").first()
    if template is None:
        raise ValueError("No active checklist template available.")
    visit = start_visit(
        store=plan.store,
        template=template,
        cluster_manager=plan.cluster_manager,
        visit_date=plan.planned_date,
        audit_type=plan.audit_type,
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
