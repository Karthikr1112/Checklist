from __future__ import annotations

import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .managers import UserManager


class Role(models.TextChoices):
    ADMIN = "ADMIN", _("Admin / HQ")
    CLUSTER_MANAGER = "CLUSTER_MANAGER", _("Cluster Manager")
    STORE_MANAGER = "STORE_MANAGER", _("Store Manager")
    INVENTORY_TEAM = "INVENTORY_TEAM", _("Inventory Team")
    MARKETING_TEAM = "MARKETING_TEAM", _("Marketing Team")
    OWNER = "OWNER", _("Action Owner")


class MarketingRole(models.TextChoices):
    HEAD = "Marketing Head", _("Marketing Head")
    ASSISTANT_MANAGER = "Assistant Manager", _("Assistant Manager")
    COORDINATOR = "Marketing Coordinator", _("Marketing Coordinator")
    EXECUTIVE = "Marketing Executive", _("Marketing Executive")


class ApprovalStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending Approval")
    APPROVED = "APPROVED", _("Approved")
    REJECTED = "REJECTED", _("Rejected")


class UserSource(models.TextChoices):
    LOCAL = "LOCAL", _("Local")
    STYLEHR = "STYLEHR", _("StyleHR")


class User(AbstractBaseUser, PermissionsMixin):
    """Email-as-username user with role-based access."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_("email address"), unique=True)
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True)
    employee_id = models.CharField(max_length=40, blank=True, db_index=True)
    role = models.CharField(
        max_length=32,
        choices=Role.choices,
        default=Role.STORE_MANAGER,
        db_index=True,
    )
    marketing_role = models.CharField(
        max_length=40,
        choices=MarketingRole.choices,
        blank=True,
        default="",
        db_index=True,
        help_text=_("Assigned checklist role for Marketing Team members."),
    )
    source = models.CharField(
        max_length=16,
        choices=UserSource.choices,
        default=UserSource.LOCAL,
        db_index=True,
    )
    approval_status = models.CharField(
        max_length=16,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.APPROVED,
        db_index=True,
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_users",
    )

    all_stores_access = models.BooleanField(
        default=False,
        help_text=_("Grant access to all active stores regardless of explicit assignments."),
    )
    assigned_stores = models.ManyToManyField(
        "stores.Store",
        blank=True,
        related_name="assigned_users",
        help_text=_("Stores explicitly assigned to this user."),
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        ordering = ("full_name",)
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self) -> str:
        return f"{self.full_name} <{self.email}>"

    # Convenience role helpers ------------------------------------------------
    @property
    def is_admin_role(self) -> bool:
        return self.role == Role.ADMIN or self.is_superuser

    @property
    def is_cluster_manager(self) -> bool:
        return self.role == Role.CLUSTER_MANAGER

    @property
    def is_store_manager(self) -> bool:
        return self.role == Role.STORE_MANAGER

    @property
    def is_inventory_team(self) -> bool:
        return self.role == Role.INVENTORY_TEAM

    @property
    def is_marketing_team(self) -> bool:
        return self.role == Role.MARKETING_TEAM

    @property
    def is_marketing_head(self) -> bool:
        return self.role == Role.MARKETING_TEAM and self.marketing_role == MarketingRole.HEAD

    @property
    def is_approved(self) -> bool:
        return self.approval_status == ApprovalStatus.APPROVED or self.is_superuser

    def get_short_name(self) -> str:
        return self.full_name.split(" ")[0] if self.full_name else self.email
