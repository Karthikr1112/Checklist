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
