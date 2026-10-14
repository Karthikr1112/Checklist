from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django import forms
from django.db import transaction

from apps.stores.models import Store

from .models import Role, User


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Email or Employee ID",
        widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username"}),
    )


class UserCreateForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, min_length=8)

    class Meta:
        model = User
        fields = ("email", "full_name", "employee_id", "phone", "role", "marketing_role", "vm_role", "gh_role")
        labels = {
            "full_name": "Employee Name",
            "employee_id": "Employee ID",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault("class", "form-select")
            elif not isinstance(field.widget, (forms.CheckboxInput, forms.RadioSelect)):
                field.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        marketing_role = cleaned_data.get("marketing_role")
        if role != Role.MARKETING_TEAM:
            cleaned_data["marketing_role"] = ""
        elif not marketing_role:
            self.add_error("marketing_role", "Please select a Marketing Role for Marketing Team users.")
        vm_role = cleaned_data.get("vm_role")
        if role != Role.VM_TEAM:
            cleaned_data["vm_role"] = ""
        elif not vm_role:
            self.add_error("vm_role", "Please select a VM Role for VM Team users.")
        gh_role = cleaned_data.get("gh_role")
        if role != Role.GROCERY_HOME:
            cleaned_data["gh_role"] = ""
        elif not gh_role:
            self.add_error("gh_role", "Please select a Grocery & Home Role for Grocery & Home users.")
        return cleaned_data

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


# Maps role → Store FK that owns the assignment.
ROLE_TO_STORE_FIELD = {
    Role.CLUSTER_MANAGER: "cluster_manager",
    Role.STORE_MANAGER: "store_manager",
    Role.INVENTORY_TEAM: "inventory_team",
    Role.MARKETING_TEAM: "marketing_team",
}


class UserEditForm(forms.ModelForm):
    stores = forms.ModelMultipleChoiceField(
        queryset=Store.objects.filter(is_active=True).order_by("code"),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": 12, "id": "id_stores"}),
        help_text="Stores assigned to this user (multiple users can share the same stores).",
    )

    class Meta:
        model = User
        fields = ("email", "full_name", "employee_id", "phone", "role", "marketing_role", "vm_role", "gh_role", "all_stores_access", "is_active")
        labels = {
            "full_name": "Employee Name",
            "employee_id": "Employee ID",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == "stores":
                continue
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault("class", "form-select")
            elif not isinstance(field.widget, (forms.CheckboxInput, forms.RadioSelect)):
                field.widget.attrs.setdefault("class", "form-control")

        if self.instance and self.instance.pk:
            self.fields["stores"].initial = self.instance.assigned_stores.all()

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        marketing_role = cleaned_data.get("marketing_role")
        if role != Role.MARKETING_TEAM:
            cleaned_data["marketing_role"] = ""
        elif not marketing_role:
            self.add_error("marketing_role", "Please select a Marketing Role for Marketing Team users.")
        vm_role = cleaned_data.get("vm_role")
        if role != Role.VM_TEAM:
            cleaned_data["vm_role"] = ""
        elif not vm_role:
            self.add_error("vm_role", "Please select a VM Role for VM Team users.")
        gh_role = cleaned_data.get("gh_role")
        if role != Role.GROCERY_HOME:
            cleaned_data["gh_role"] = ""
        elif not gh_role:
            self.add_error("gh_role", "Please select a Grocery & Home Role for Grocery & Home users.")
        return cleaned_data

    @transaction.atomic
    def save(self, commit: bool = True) -> User:
        user = super().save(commit=commit)
        selected = self.cleaned_data.get("stores") or Store.objects.none()
        user.assigned_stores.set(selected)
        return user
