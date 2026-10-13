from django import forms

from apps.checklists.models import ChecklistTemplate
from apps.stores.models import Store
from apps.stores.selectors import stores_visible_to

from .models import AuditType, Response, Visit, VisitResponse


class StartVisitForm(forms.Form):
    DEPARTMENT_CHOICES = [
        ("", "— Select Department / Category —"),
        ("CLUSTER_MANAGER", "Cluster Manager Store Visit"),
        ("INVENTORY_TEAM", "Inventory Team Daily Checklist"),
        ("MARKETING_TEAM", "Marketing Team"),
    ]

    MARKETING_ROLE_CHOICES = [
        ("", "— Select Role Checklist —"),
        ("Marketing Head", "Marketing Head"),
        ("Assistant Manager", "Assistant Manager"),
        ("Marketing Coordinator", "Marketing Coordinator"),
        ("Marketing Executive", "Marketing Executive"),
    ]

    store = forms.ModelChoiceField(
        queryset=Store.objects.filter(is_active=True),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    department = forms.ChoiceField(
        choices=DEPARTMENT_CHOICES,
        label="Checklist Department",
        widget=forms.Select(attrs={"class": "form-select", "id": "id_department"}),
    )
    marketing_role = forms.ChoiceField(
        choices=MARKETING_ROLE_CHOICES,
        required=False,
        label="Role Checklist",
        widget=forms.Select(attrs={"class": "form-select", "id": "id_marketing_role"}),
        help_text="Choose which of the 4 marketing role checklists to conduct.",
    )
    visit_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"})
    )
    audit_type = forms.ChoiceField(
        choices=AuditType.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user is not None and not user.is_admin_role:
            self.fields["store"].queryset = stores_visible_to(user)
            if user.is_inventory_team:
                self.fields["department"].choices = [
                    ("INVENTORY_TEAM", "Inventory Team Daily Checklist")
                ]
                self.fields["department"].initial = "INVENTORY_TEAM"
                self.fields["department"].widget = forms.HiddenInput()
                self.fields["marketing_role"].widget = forms.HiddenInput()
            elif user.is_marketing_team:
                self.fields["department"].choices = [
                    ("MARKETING_TEAM", "Marketing Team")
                ]
                self.fields["department"].initial = "MARKETING_TEAM"
                self.fields["department"].widget = forms.HiddenInput()
                if getattr(user, "marketing_role", ""):
                    self.fields["marketing_role"].initial = user.marketing_role
                    self.fields["marketing_role"].widget = forms.HiddenInput()
            else:
                self.fields["department"].choices = [
                    ("CLUSTER_MANAGER", "Cluster Manager Store Visit")
                ]
                self.fields["department"].initial = "CLUSTER_MANAGER"
                self.fields["department"].widget = forms.HiddenInput()
                self.fields["marketing_role"].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        dept = cleaned_data.get("department")
        m_role = cleaned_data.get("marketing_role")

        if not dept:
            self.add_error("department", "Please select a checklist department.")
            return cleaned_data

        if dept == "CLUSTER_MANAGER":
            template = ChecklistTemplate.objects.filter(
                is_active=True,
                audience=ChecklistTemplate.Audience.CLUSTER_MANAGER,
            ).order_by("-version").first()
            if not template:
                self.add_error("department", "No active template found for Cluster Manager.")
                return cleaned_data
            cleaned_data["template"] = template

        elif dept == "INVENTORY_TEAM":
            template = ChecklistTemplate.objects.filter(
                is_active=True,
                audience=ChecklistTemplate.Audience.INVENTORY_TEAM,
            ).order_by("-version").first()
            if not template:
                self.add_error("department", "No active template found for Inventory Team.")
                return cleaned_data
            cleaned_data["template"] = template

        elif dept == "MARKETING_TEAM":
            if hasattr(self, "user") and getattr(self.user, "is_marketing_team", False) and not getattr(self.user, "is_admin_role", False):
                m_role = getattr(self.user, "marketing_role", "") or m_role
                cleaned_data["marketing_role"] = m_role
            elif not m_role and hasattr(self, "user") and getattr(self.user, "marketing_role", ""):
                m_role = self.user.marketing_role
                cleaned_data["marketing_role"] = m_role

            if not m_role:
                self.add_error("marketing_role", "Please select one of the 4 Marketing Role templates.")
                return cleaned_data

            template = ChecklistTemplate.objects.filter(
                is_active=True,
                audience=ChecklistTemplate.Audience.MARKETING_TEAM,
                name__icontains=m_role.strip(),
            ).order_by("-version").first()
            if not template:
                self.add_error("marketing_role", f"No active template found for '{m_role}'.")
                return cleaned_data
            cleaned_data["template"] = template

        return cleaned_data


class VisitResponseForm(forms.ModelForm):
    response = forms.ChoiceField(
        choices=[("", "—")] + list(Response.choices),
        required=False,
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )

    class Meta:
        model = VisitResponse
        fields = ("response", "observation")
        widgets = {
            "observation": forms.Textarea(attrs={"rows": 2, "class": "form-control form-control-sm"}),
        }


class PhotoUploadForm(forms.Form):
    image = forms.ImageField()
    caption = forms.CharField(required=False, max_length=200)
