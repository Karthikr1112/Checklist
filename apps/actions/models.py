from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel
from apps.visits.models import VisitResponse


class ActionStatus(models.TextChoices):
    OPEN = "OPEN", _("Open")
    IN_PROGRESS = "IN_PROGRESS", _("In Progress")
    CLOSED = "CLOSED", _("Closed")
    NOT_REQUIRED = "NOT_REQUIRED", _("Not Required")


class ActionItem(BaseModel):
    response = models.ForeignKey(
        VisitResponse, on_delete=models.CASCADE, related_name="action_items"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_actions"
    )
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=16, choices=ActionStatus.choices, default=ActionStatus.OPEN, db_index=True
    )
    closure_note = models.TextField(blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("owner", "status")),
            models.Index(fields=("status", "due_date")),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.get_status_display()})"
