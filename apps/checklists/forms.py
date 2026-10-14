from django import forms

from .models import Question, Section


class SectionForm(forms.ModelForm):
    class Meta:
        model = Section
        fields = ("name", "order")
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Inventory Management"}),
            "order": forms.NumberInput(attrs={"min": 0}),
        }


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ("section", "code", "text", "evidence_hint", "requires_photo", "response_type", "order")
        widgets = {
            "code": forms.TextInput(attrs={"placeholder": "e.g. CM-001"}),
            "text": forms.Textarea(attrs={"rows": 3, "placeholder": "Enter question text..."}),
            "evidence_hint": forms.Textarea(attrs={"rows": 2, "placeholder": "Measurement / evidence guidance..."}),
            "order": forms.NumberInput(attrs={"min": 0}),
        }

    def __init__(self, *args, template=None, **kwargs):
        super().__init__(*args, **kwargs)
        if template:
            self.fields["section"].queryset = Section.objects.filter(template=template)
