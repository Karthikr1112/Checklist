from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel
from apps.stores.models import Store
from apps.visits.models import AuditType, Visit


class PlanStatus(models.TextChoices):
    PLANNED = "PLANNED", _("Planned")
    CHECKED_IN = "CHECKED_IN", _("Checked In")
    COMPLETED = "COMPLETED", _("Completed")
    MISSED = "MISSED", _("Missed")
    CANCELLED = "CANCELLED", _("Cancelled")


class VisitPlan(BaseModel):
    """A Cluster Manager's planned store visit on a specific date + time slot."""

    cluster_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="visit_plans",
    )
    store = models.ForeignKey(Store, on_delete=models.PROTECT, related_name="visit_plans")
    planned_date = models.DateField(db_index=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    audit_type = models.CharField(
        max_length=16, choices=AuditType.choices, default=AuditType.FULL
    )
    status = models.CharField(
        max_length=16, choices=PlanStatus.choices, default=PlanStatus.PLANNED, db_index=True
    )
    notes = models.TextField(blank=True)
    edit_reason = models.TextField(
        blank=True,
        default="",
        help_text=_("Reason provided when this plan was last edited."),
    )

    visit = models.OneToOneField(
        Visit,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="plan",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_plans",
    )

    class Meta:
        ordering = ("planned_date", "start_time")
        constraints = [
            models.UniqueConstraint(
                fields=("cluster_manager", "planned_date", "start_time"),
                name="uniq_cm_date_starttime",
            ),
        ]
        indexes = [
            models.Index(fields=("planned_date", "cluster_manager")),
            models.Index(fields=("store", "planned_date")),
        ]

    def __str__(self) -> str:  # pragma: no cover
        store_code = getattr(getattr(self, "store", None), "code", "?")
        return f"{self.cluster_manager_id} @ {store_code} on {self.planned_date} {self.start_time}"
