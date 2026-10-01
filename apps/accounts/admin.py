from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("email",)
    list_display = ("email", "full_name", "employee_id", "role", "source", "approval_status", "is_active", "is_staff")
    list_filter = ("role", "source", "approval_status", "is_active", "is_staff")
    search_fields = ("email", "full_name", "phone", "employee_id")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("full_name", "phone", "employee_id", "role")}),
        ("Origin & Approval", {"fields": ("source", "approval_status", "approved_at", "approved_by")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "full_name", "role", "password1", "password2"),
            },
        ),
    )
    readonly_fields = ("last_login", "date_joined", "approved_at")
