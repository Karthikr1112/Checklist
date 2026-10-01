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
        fields = ("email", "full_name", "phone", "role", "marketing_role")

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
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": 12}),
        help_text="Stores this user is responsible for (based on their role).",
    )

    class Meta:
        model = User
        fields = ("email", "full_name", "phone", "role", "marketing_role", "is_active")

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
            field = ROLE_TO_STORE_FIELD.get(self.instance.role)
            if field:
                self.fields["stores"].initial = Store.objects.filter(**{field: self.instance})

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        marketing_role = cleaned_data.get("marketing_role")
        if role != Role.MARKETING_TEAM:
            cleaned_data["marketing_role"] = ""
        elif not marketing_role:
            self.add_error("marketing_role", "Please select a Marketing Role for Marketing Team users.")
        return cleaned_data

    @transaction.atomic
    def save(self, commit: bool = True) -> User:
        user = super().save(commit=commit)
        field = ROLE_TO_STORE_FIELD.get(user.role)
        if field is None:
            # Role with no store ownership: clear any prior assignments on all three FKs.
            for f in ROLE_TO_STORE_FIELD.values():
                Store.objects.filter(**{f: user}).update(**{f: None})
            return user

        selected = self.cleaned_data.get("stores") or Store.objects.none()
        selected_ids = list(selected.values_list("pk", flat=True))

        # Clear assignments on the *other* FK columns where this user was set.
        for other in ROLE_TO_STORE_FIELD.values():
            if other != field:
                Store.objects.filter(**{other: user}).update(**{other: None})

        # Unset stores the user is no longer assigned to on the active FK.
        Store.objects.filter(**{field: user}).exclude(pk__in=selected_ids).update(**{field: None})
        # Assign newly-selected stores.
        if selected_ids:
            Store.objects.filter(pk__in=selected_ids).update(**{field: user})
        return user
