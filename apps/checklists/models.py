from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class ChecklistTemplate(BaseModel):
    """A versioned set of sections + questions used by a Visit."""

    class Audience(models.TextChoices):
        CLUSTER_MANAGER = "CLUSTER_MANAGER", _("Cluster Manager")
        INVENTORY_TEAM = "INVENTORY_TEAM", _("Inventory Team")
        MARKETING_TEAM = "MARKETING_TEAM", _("Marketing Team")
        STORE_MANAGER = "STORE_MANAGER", _("Store Manager")

    name = models.CharField(max_length=120)
    version = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True, db_index=True)
    description = models.TextField(blank=True)
    audience = models.CharField(
        max_length=32,
        choices=Audience.choices,
        default=Audience.CLUSTER_MANAGER,
        db_index=True,
        help_text="Which role this checklist is intended for.",
    )

    class Meta:
        ordering = ("-is_active", "name", "-version")
        constraints = [
            models.UniqueConstraint(fields=("name", "version"), name="uniq_template_name_version"),
        ]

    def __str__(self) -> str:
        return f"{self.name} v{self.version}"

    @property
    def question_count(self) -> int:
        if hasattr(self, "_prefetched_objects_cache") and "sections" in self._prefetched_objects_cache:
            return sum(len(s.questions.all()) for s in self.sections.all())
        return Question.objects.filter(section__template=self).count()


class Section(BaseModel):
    template = models.ForeignKey(ChecklistTemplate, on_delete=models.CASCADE, related_name="sections")
    name = models.CharField(max_length=80)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("order", "name")
        constraints = [
            models.UniqueConstraint(fields=("template", "name"), name="uniq_section_per_template"),
        ]

    def __str__(self) -> str:
        return self.name


class Question(BaseModel):
    class ResponseType(models.TextChoices):
        YES_NO_NA = "YNN", _("Yes / No / NA")

    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="questions")
    code = models.CharField(max_length=20, db_index=True, help_text="e.g. CM-001")
    text = models.TextField()
    evidence_hint = models.TextField(blank=True, help_text="Measurement / evidence guidance")
    requires_photo = models.BooleanField(default=False)
    response_type = models.CharField(
        max_length=8, choices=ResponseType.choices, default=ResponseType.YES_NO_NA
    )
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("section__order", "order", "code")
        constraints = [
            models.UniqueConstraint(fields=("section", "code"), name="uniq_question_code_per_section"),
        ]

    def __str__(self) -> str:
        return f"{self.code} — {self.text[:60]}"
