"""Reusable abstract models for the whole project."""
from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """Adds self-managed `created_at` / `updated_at` fields."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    """Public-safe UUID primary key (no integer enumeration)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    def alive(self) -> "SoftDeleteQuerySet":
        return self.filter(deleted_at__isnull=True)

    def dead(self) -> "SoftDeleteQuerySet":
        return self.filter(deleted_at__isnull=False)

    def delete(self):  # type: ignore[override]
        return super().update(deleted_at=timezone.now())


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    def get_queryset(self) -> SoftDeleteQuerySet:  # type: ignore[override]
        return SoftDeleteQuerySet(self.model, using=self._db).alive()


class SoftDeleteModel(models.Model):
    """Audit-friendly soft delete."""

    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents: bool = False):  # type: ignore[override]
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    def hard_delete(self, using=None, keep_parents: bool = False):
        return super().delete(using=using, keep_parents=keep_parents)


class BaseModel(UUIDModel, TimeStampedModel, SoftDeleteModel):
    """Standard base for every domain entity."""

    class Meta:
        abstract = True


class AuditLog(models.Model):
    """Who did what, to which record, and when. Labels are stored as text so an entry
    still reads correctly after the user or record it mentions has been deleted."""

    class Action(models.TextChoices):
        LOGIN = "LOGIN", "Logged in"
        LOGIN_FAILED = "LOGIN_FAILED", "Login failed"
        LOGOUT = "LOGOUT", "Logged out"
        USER_CREATED = "USER_CREATED", "User created"
        USER_UPDATED = "USER_UPDATED", "User updated"
        USER_APPROVED = "USER_APPROVED", "User approved"
        USER_REJECTED = "USER_REJECTED", "User rejected"
        VISIT_STARTED = "VISIT_STARTED", "Visit started"
        VISIT_UPDATED = "VISIT_UPDATED", "Visit edited"
        VISIT_SUBMITTED = "VISIT_SUBMITTED", "Visit submitted"
        VISIT_APPROVED = "VISIT_APPROVED", "Visit approved"
        VISIT_DELETED = "VISIT_DELETED", "Visit deleted"
        ANSWER_CHANGED = "ANSWER_CHANGED", "Answer changed after submit"
        ACTION_CREATED = "ACTION_CREATED", "Action created"
        ACTION_UPDATED = "ACTION_UPDATED", "Action status changed"
        PLAN_CREATED = "PLAN_CREATED", "Plan created"
        PLAN_UPDATED = "PLAN_UPDATED", "Plan edited"
        PLAN_RESCHEDULED = "PLAN_RESCHEDULED", "Plan rescheduled"
        PLAN_DELETED = "PLAN_DELETED", "Plan deleted"
        CHECKLIST_CHANGED = "CHECKLIST_CHANGED", "Checklist changed"
        STORE_CHANGED = "STORE_CHANGED", "Store changed"
        SYSTEM_CLEANUP = "SYSTEM_CLEANUP", "System Cleanup"

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    actor = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_entries"
    )
    actor_label = models.CharField(max_length=200, blank=True)
    action = models.CharField(max_length=32, choices=Action.choices, db_index=True)
    object_type = models.CharField(max_length=40, blank=True)
    object_id = models.CharField(max_length=64, blank=True, db_index=True)
    object_label = models.CharField(max_length=255, blank=True)
    details = models.TextField(blank=True)
    changes = models.JSONField(default=dict, blank=True, help_text="Field: [before, after]")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("actor", "created_at"))]

    def __str__(self) -> str:
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.actor_label} {self.get_action_display()} {self.object_label}"
