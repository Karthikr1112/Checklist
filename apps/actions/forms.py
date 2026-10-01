from django import forms

from apps.accounts.models import User

from .models import ActionItem


class ActionItemForm(forms.ModelForm):
    class Meta:
        model = ActionItem
        fields = ("title", "description", "owner", "due_date", "status")
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["owner"].queryset = User.objects.filter(is_active=True)
