from django.contrib import admin

from .models import ResponsePhoto, Visit, VisitResponse


class VisitResponseInline(admin.TabularInline):
    model = VisitResponse
    extra = 0
    fields = ("question", "response", "observation", "score")
    readonly_fields = ("question", "score")
    can_delete = False


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ("store", "visit_date", "cluster_manager", "status", "compliance_pct")
    list_filter = ("status", "audit_type", "visit_date")
    date_hierarchy = "visit_date"
    search_fields = ("store__code", "store__name")
    autocomplete_fields = ("store", "cluster_manager", "approved_by")
    readonly_fields = (
        "total_questions", "answered_count", "yes_count", "no_count",
        "na_count", "compliance_pct", "submitted_at", "approved_at",
    )
    inlines = [VisitResponseInline]


@admin.register(ResponsePhoto)
class ResponsePhotoAdmin(admin.ModelAdmin):
    list_display = ("response", "uploaded_by", "created_at")
