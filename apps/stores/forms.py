from django import forms

from .models import Store


class StoreForm(forms.ModelForm):
    class Meta:
        model = Store
        fields = ("code", "name", "city", "region", "cluster_manager", "store_manager", "inventory_team", "marketing_team", "is_active")
