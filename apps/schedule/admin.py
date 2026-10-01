from django.contrib import admin

from .models import VisitPlan


@admin.register(VisitPlan)
class VisitPlanAdmin(admin.ModelAdmin):
    list_display = ("planned_date", "start_time", "end_time", "store", "cluster_manager", "audit_type", "status")
    list_filter = ("status", "audit_type", "planned_date")
    search_fields = ("store__code", "store__name", "cluster_manager__email")
    autocomplete_fields = ("store", "cluster_manager", "visit")
    date_hierarchy = "planned_date"
