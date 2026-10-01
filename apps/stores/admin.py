from django.contrib import admin

from .models import Store


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "city", "region", "cluster_manager", "store_manager", "inventory_team", "is_active")
    list_filter = ("is_active", "region", "city")
    search_fields = ("code", "name", "city")
    autocomplete_fields = ("cluster_manager", "store_manager", "inventory_team")
