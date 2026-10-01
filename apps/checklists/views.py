from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .models import ChecklistTemplate


@login_required
def template_list(request):
    templates = ChecklistTemplate.objects.prefetch_related("sections__questions")
    user = request.user
    if not user.is_admin_role:
        if user.is_inventory_team:
            templates = templates.filter(audience=ChecklistTemplate.Audience.INVENTORY_TEAM)
        elif user.is_marketing_team:
            templates = templates.filter(audience=ChecklistTemplate.Audience.MARKETING_TEAM)
        else:
            templates = templates.filter(audience=ChecklistTemplate.Audience.CLUSTER_MANAGER)
    return render(request, "checklists/template_list.html", {"templates": templates})


@login_required
def template_detail(request, pk):
    qs = ChecklistTemplate.objects.prefetch_related("sections__questions")
    user = request.user
    if not user.is_admin_role:
        if user.is_inventory_team:
            qs = qs.filter(audience=ChecklistTemplate.Audience.INVENTORY_TEAM)
        elif user.is_marketing_team:
            qs = qs.filter(audience=ChecklistTemplate.Audience.MARKETING_TEAM)
        else:
            qs = qs.filter(audience=ChecklistTemplate.Audience.CLUSTER_MANAGER)
    template = get_object_or_404(qs, pk=pk)
    return render(request, "checklists/template_detail.html", {"template": template})
