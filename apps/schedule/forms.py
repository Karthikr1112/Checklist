from django import forms

from apps.accounts.models import Role, User
from apps.stores.models import Store
from apps.stores.selectors import stores_visible_to
from apps.visits.models import AuditType

from .models import PlanStatus, VisitPlan


class VisitPlanForm(forms.ModelForm):
    class Meta:
        model = VisitPlan
        fields = (
            "cluster_manager",
            "store",
            "planned_date",
            "start_time",
            "end_time",
            "audit_type",
            "status",
            "notes",
        )
        widgets = {
            "planned_date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["audit_type"].choices = AuditType.choices
        self.fields["status"].choices = PlanStatus.choices
        self.fields["cluster_manager"].queryset = User.objects.filter(
            is_active=True,
            role__in=[Role.CLUSTER_MANAGER, Role.ADMIN, Role.COO, Role.INVENTORY_TEAM, Role.MARKETING_TEAM, Role.VM_TEAM, Role.GROCERY_HOME],
        )
        self.fields["cluster_manager"].label_from_instance = lambda u: u.employee_label
        self.fields["store"].queryset = Store.objects.filter(is_active=True)
        if user is not None and not user.is_admin_role:
            # Non-admins can only plan for themselves
            self.fields["cluster_manager"].queryset = User.objects.filter(pk=user.pk)
            self.fields["cluster_manager"].initial = user
            self.fields["cluster_manager"].widget = forms.HiddenInput()
            self.fields["store"].queryset = stores_visible_to(user)

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_time")
        end = cleaned.get("end_time")
        if start and end and end <= start:
            raise forms.ValidationError("End time must be after start time.")
        return cleaned
