from django.contrib import admin

from apps.accounts.models import User
from apps.stores.models import Store

from .models import VisitPlan
from .services import resolve_template_for_user


@admin.register(VisitPlan)
class VisitPlanAdmin(admin.ModelAdmin):
    list_display = (
        "planned_date",
        "start_time",
        "end_time",
        "store",
        "cluster_manager",
        "created_by",
        "template",
        "audit_type",
        "status",
    )
    list_filter = (
        "status",
        "audit_type",
        "planned_date",
        "template",
        "cluster_manager__role",
        "cluster_manager__gh_role",
        "cluster_manager__vm_role",
        "cluster_manager__marketing_role",
    )
    search_fields = (
        "store__code",
        "store__name",
        "cluster_manager__email",
        "cluster_manager__full_name",
        "cluster_manager__employee_id",
        "created_by__email",
        "created_by__full_name",
        "created_by__employee_id",
        "template__name",
    )
    date_hierarchy = "planned_date"

    fieldsets = (
        (
            "Schedule Assignment",
            {
                "fields": ("cluster_manager", "created_by", "store"),
                "description": "Select the user who will fill the checklist, who scheduled it (e.g. Department Head / Manager / Admin), and the store.",
            },
        ),
        (
            "Time & Type",
            {
                "fields": ("planned_date", "start_time", "end_time", "audit_type", "status"),
            },
        ),
        (
            "Notes & Details",
            {
                "fields": ("notes", "edit_reason", "visit"),
                "classes": ("collapse",),
            },
        ),
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name in ("cluster_manager", "created_by"):
            kwargs["queryset"] = User.objects.filter(is_active=True).order_by("full_name")
        elif db_field.name == "store":
            kwargs["queryset"] = Store.objects.filter(is_active=True).order_by("code")
        formfield = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if formfield:
            formfield.widget.attrs.update({"style": "min-width: 380px; padding: 6px 10px; font-size: 13.5px;"})
        return formfield

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        if obj.cluster_manager_id:
            obj.template = resolve_template_for_user(obj.cluster_manager)
        super().save_model(request, obj, form, change)
