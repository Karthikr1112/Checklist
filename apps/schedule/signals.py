from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.visits.models import Visit, VisitStatus

from .models import PlanStatus, VisitPlan


@receiver(post_save, sender=Visit)
def _sync_plan_status(sender, instance: Visit, **kwargs):  # noqa: ARG001
    """When the linked Visit advances, mirror status onto its plan."""
    plan = VisitPlan.objects.filter(visit=instance).first()
    if plan is None:
        return
    if instance.status in {VisitStatus.SUBMITTED, VisitStatus.APPROVED, VisitStatus.CLOSED}:
        if plan.status != PlanStatus.COMPLETED:
            plan.status = PlanStatus.COMPLETED
            plan.save(update_fields=["status", "updated_at"])
