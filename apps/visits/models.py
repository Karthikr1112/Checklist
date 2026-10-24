from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.checklists.models import ChecklistTemplate, Question
from apps.core.models import BaseModel
from apps.stores.models import Store


class AuditType(models.TextChoices):
    FULL = "FULL", _("Full Visit")
    SURPRISE = "SURPRISE", _("Surprise Audit")
    REVISIT = "REVISIT", _("Revisit Required")
    MONTHLY = "MONTHLY", _("Monthly Review")


class VisitStatus(models.TextChoices):
    DRAFT = "DRAFT", _("Draft")
    IN_PROGRESS = "IN_PROGRESS", _("In Progress")
    SUBMITTED = "SUBMITTED", _("Submitted")
    FOLLOW_UP = "FOLLOW_UP", _("Follow-up")
    CLOSED = "CLOSED", _("Closed")
    APPROVED = "APPROVED", _("Approved")


class Response(models.TextChoices):
    YES = "YES", _("Yes")
    NO = "NO", _("No")
    NA = "NA", _("Not Applicable")


class Visit(BaseModel):
    store = models.ForeignKey(Store, on_delete=models.PROTECT, related_name="visits")
    template = models.ForeignKey(ChecklistTemplate, on_delete=models.PROTECT, related_name="visits")
    cluster_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="conducted_visits"
    )
    visit_date = models.DateField()
    audit_type = models.CharField(max_length=16, choices=AuditType.choices, default=AuditType.FULL)
    status = models.CharField(
        max_length=16, choices=VisitStatus.choices, default=VisitStatus.DRAFT, db_index=True
    )

    # Snapshot fields, recomputed by signals
    total_questions = models.PositiveSmallIntegerField(default=0)
    answered_count = models.PositiveSmallIntegerField(default=0)
    yes_count = models.PositiveSmallIntegerField(default=0)
    no_count = models.PositiveSmallIntegerField(default=0)
    na_count = models.PositiveSmallIntegerField(default=0)
    compliance_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    summary = models.TextField(blank=True, help_text="Overall visit summary (VM Team checklists).")

    # Geolocation verification on start
    started_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, help_text="GPS Latitude when visit was started.")
    started_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, help_text="GPS Longitude when visit was started.")
    started_distance_meters = models.PositiveIntegerField(null=True, blank=True, help_text="Distance in meters from store when visit was started.")

    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_visits",
    )

    class Meta:
        ordering = ("-visit_date", "-created_at")
        indexes = [
            models.Index(fields=("store", "visit_date")),
            models.Index(fields=("cluster_manager", "visit_date")),
        ]

    def __str__(self) -> str:
        return f"Visit {self.store.code} on {self.visit_date}"

    @property
    def open_actions_count(self) -> int:
        from apps.actions.models import ActionItem, ActionStatus

        return ActionItem.objects.filter(
            response__visit=self, status__in=[ActionStatus.OPEN, ActionStatus.IN_PROGRESS]
        ).count()

    @property
    def is_marketing_checklist(self) -> bool:
        return (
            self.template.audience == ChecklistTemplate.Audience.MARKETING_TEAM
            or getattr(self.cluster_manager, "role", "") == "MARKETING_TEAM"
            or bool(getattr(self.cluster_manager, "marketing_role", ""))
        )

    @property
    def is_vm_checklist(self) -> bool:
        return (
            self.template.audience == ChecklistTemplate.Audience.VM_TEAM
            or getattr(self.cluster_manager, "role", "") == "VM_TEAM"
        )

    @property
    def is_grocery_home_checklist(self) -> bool:
        return (
            self.template.audience == ChecklistTemplate.Audience.GROCERY_HOME
            or getattr(self.cluster_manager, "role", "") == "GROCERY_HOME"
        )

    @property
    def is_store_manager_checklist(self) -> bool:
        return (
            self.template.audience == ChecklistTemplate.Audience.STORE_MANAGER
            or getattr(self.cluster_manager, "role", "") == "STORE_MANAGER"
        )

    def can_be_approved_by(self, user) -> bool:
        if not user or not user.is_authenticated or not getattr(user, "is_approved", True):
            return False
        if getattr(user, "is_admin_role", False):
            return True
        if getattr(user, "is_marketing_head", False) and self.is_marketing_checklist:
            return True
        if getattr(user, "is_vm_manager", False) and self.is_vm_checklist:
            return True
        if getattr(user, "is_business_head", False) and self.is_grocery_home_checklist:
            return True
        if getattr(user, "is_cluster_manager", False) and self.is_store_manager_checklist:
            from apps.stores.selectors import stores_visible_to
            return self.store in stores_visible_to(user)
        return False


class VisitResponse(BaseModel):
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name="responses")
    question = models.ForeignKey(Question, on_delete=models.PROTECT, related_name="responses")
    response = models.CharField(max_length=4, choices=Response.choices, blank=True)
    evidence_data = models.JSONField(default=dict, blank=True, help_text="Numeric/measurement values")
    observation = models.TextField(blank=True)
    score = models.DecimalField(max_digits=4, decimal_places=2, default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("visit", "question"), name="uniq_response_per_question"),
        ]
        ordering = ("question__section__order", "question__order")

    def __str__(self) -> str:
        return f"{self.question.code} → {self.response or '-'}"


def response_photo_path(instance: "ResponsePhoto", filename: str) -> str:
    visit_id = instance.response.visit_id
    return f"visits/{visit_id}/{instance.response.question.code}/{filename}"


class ResponsePhoto(BaseModel):
    response = models.ForeignKey(VisitResponse, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to=response_photo_path)
    caption = models.CharField(max_length=200, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="uploaded_photos"
    )

    class Meta:
        ordering = ("created_at",)
