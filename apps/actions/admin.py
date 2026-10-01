from django.contrib import admin

from .models import ActionItem


@admin.register(ActionItem)
class ActionItemAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "status", "due_date", "created_at")
    list_filter = ("status",)
    search_fields = ("title", "description")
    autocomplete_fields = ("owner",)
