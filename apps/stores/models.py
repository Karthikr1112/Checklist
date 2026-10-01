from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class Store(BaseModel):
    code = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=150)
    city = models.CharField(max_length=80)
    region = models.CharField(max_length=80, blank=True)
    is_active = models.BooleanField(default=True)

    cluster_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cluster_stores",
        limit_choices_to={"role": "CLUSTER_MANAGER"},
    )
    store_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_stores",
        limit_choices_to={"role": "STORE_MANAGER"},
    )
    inventory_team = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_stores",
        limit_choices_to={"role": "INVENTORY_TEAM"},
    )
    marketing_team = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marketing_stores",
        limit_choices_to={"role": "MARKETING_TEAM"},
    )

    class Meta:
        ordering = ("code",)
        indexes = [models.Index(fields=("city",)), models.Index(fields=("region",))]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"
