from __future__ import annotations

import re
import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .managers import UserManager

# StyleHR employee code, e.g. "RR-21747" (firm prefix + employee code).
EMPLOYEE_CODE_RE = re.compile(r"^[A-Za-z0-9]{1,6}-\d+$")


class Role(models.TextChoices):
    ADMIN = "ADMIN", _("Admin / HQ")
    CLUSTER_MANAGER = "CLUSTER_MANAGER", _("Cluster Manager")
    STORE_MANAGER = "STORE_MANAGER", _("Store Manager")
    INVENTORY_TEAM = "INVENTORY_TEAM", _("Inventory Team")
    MARKETING_TEAM = "MARKETING_TEAM", _("Marketing Team")
    VM_TEAM = "VM_TEAM", _("VM Team")
    GROCERY_HOME = "GROCERY_HOME", _("Grocery & Home")
    OWNER = "OWNER", _("Action Owner")


class MarketingRole(models.TextChoices):
    HEAD = "Marketing Head", _("Marketing Head")
    ASSISTANT_MANAGER = "Assistant Manager", _("Assistant Manager")
    COORDINATOR = "Marketing Coordinator", _("Marketing Coordinator")
    EXECUTIVE = "Marketing Executive", _("Marketing Executive")


class VMRole(models.TextChoices):
    MANAGER = "VM Manager", _("VM Manager")
    EXECUTIVE = "VM Executive", _("VM Executive")


class GHRole(models.TextChoices):
    CATEGORY_HEAD_GROCERY = "Category Head - Grocery", _("Category Head - Grocery")
    CATEGORY_HEAD_HOME = "Category Head - Home", _("Category Head - Home")
    BUSINESS_HEAD = "Business Head, Grocery & Home", _("Business Head, Grocery & Home")


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
    vm_role = models.CharField(
        max_length=40,
        choices=VMRole.choices,
        blank=True,
        default="",
        db_index=True,
        help_text=_("Assigned checklist role for VM (Visual Merchandising) Team members."),
    )
    gh_role = models.CharField(
        max_length=40,
        choices=GHRole.choices,
        blank=True,
        default="",
        db_index=True,
        help_text=_("Assigned checklist role for Grocery & Home members."),
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
    def is_vm_team(self) -> bool:
        return self.role == Role.VM_TEAM

    @property
    def is_vm_manager(self) -> bool:
        return self.role == Role.VM_TEAM and self.vm_role == VMRole.MANAGER

    @property
    def is_grocery_home(self) -> bool:
        return self.role == Role.GROCERY_HOME

    @property
    def is_business_head(self) -> bool:
        """Business Head, Grocery & Home: head of the Grocery & Home department."""
        return self.role == Role.GROCERY_HOME and self.gh_role == GHRole.BUSINESS_HEAD

    @property
    def sub_role(self) -> str:
        """The team-specific role shown next to a person's name (Marketing / VM / Grocery & Home)."""
        return self.marketing_role or self.vm_role or self.gh_role

    @property
    def is_approved(self) -> bool:
        return self.approval_status == ApprovalStatus.APPROVED or self.is_superuser

    @property
    def employee_name(self) -> str:
        """Real name for display; blank while full_name still holds an employee code or email."""
        name = (self.full_name or "").strip()
        if not name or name == self.email or name == self.employee_id or EMPLOYEE_CODE_RE.match(name):
            return ""
        return name

    @property
    def employee_label(self) -> str:
        """Employee ID and name only (no email), e.g. "RR-10317 — Thilak Naidu"."""
        parts = [p for p in (self.employee_id, self.employee_name) if p]
        return " — ".join(parts) or self.full_name

    def get_short_name(self) -> str:
        return self.full_name.split(" ")[0] if self.full_name else self.email
