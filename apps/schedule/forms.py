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
            "edit_reason",
        )
        widgets = {
            "planned_date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
            "edit_reason": forms.Textarea(attrs={"rows": 2, "placeholder": "Explain why this scheduled plan is being edited..."}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["audit_type"].choices = AuditType.choices
        self.fields["status"].choices = PlanStatus.choices
        self.fields["cluster_manager"].queryset = User.objects.filter(
            is_active=True,
            role__in=[Role.CLUSTER_MANAGER, Role.ADMIN, Role.COO, Role.PROFESSIONAL_USER, Role.INVENTORY_TEAM, Role.MARKETING_TEAM, Role.VM_TEAM, Role.GROCERY_HOME],
        )
        self.fields["cluster_manager"].label_from_instance = lambda u: u.employee_label
        self.fields["store"].queryset = Store.objects.filter(is_active=True)
        if user is not None and not user.is_admin_role:
            # Non-admins can only plan for themselves
            self.fields["cluster_manager"].queryset = User.objects.filter(pk=user.pk)
            self.fields["cluster_manager"].initial = user
            self.fields["cluster_manager"].widget = forms.HiddenInput()
            self.fields["store"].queryset = stores_visible_to(user)

        is_edit = bool(self.instance and not self.instance._state.adding)
        if is_edit:
            self.fields["edit_reason"].required = True
            self.fields["edit_reason"].label = "Reason for Edit"
            self.fields["edit_reason"].widget.attrs.update({
                "placeholder": "Explain why this scheduled plan is being edited (mandatory)...",
                "required": "required",
            })
            self.fields["edit_reason"].help_text = "Mandatory: explain why you are editing this scheduled plan."
        else:
            if "edit_reason" in self.fields:
                del self.fields["edit_reason"]

    def clean_edit_reason(self):
        reason = self.cleaned_data.get("edit_reason", "").strip()
        is_edit = bool(self.instance and not self.instance._state.adding)
        if is_edit and not reason:
            raise forms.ValidationError("Please provide a reason why you are editing this scheduled plan.")
        return reason

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_time")
        end = cleaned.get("end_time")
        if start and end and end <= start:
            raise forms.ValidationError("End time must be after start time.")
        return cleaned
