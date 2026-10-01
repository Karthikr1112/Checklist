from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.visits.models import VisitResponse
from apps.visits.selectors import visits_visible_to

from .forms import ActionItemForm
from .models import ActionItem, ActionStatus


@login_required
def my_actions(request):
    items = ActionItem.objects.filter(owner=request.user).select_related("response__visit__store")
    return render(request, "actions/my_actions.html", {"items": items})


@login_required
def all_actions(request):
    visible_visits = visits_visible_to(request.user).values_list("id", flat=True)
    items = (
        ActionItem.objects.filter(response__visit_id__in=list(visible_visits))
        .select_related("owner", "response__visit__store", "response__question")
    )
    return render(request, "actions/all_actions.html", {"items": items})


@login_required
def action_create(request, response_pk):
    response = get_object_or_404(VisitResponse.objects.select_related("visit"), pk=response_pk)
    if request.method == "POST":
        form = ActionItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.response = response
            item.save()
            messages.success(request, "Action created.")
            return redirect("visits:visit_fill", pk=response.visit_id)
    else:
        form = ActionItemForm(initial={"title": f"Action for {response.question.code}"})
    return render(request, "actions/action_form.html", {"form": form, "response": response})


@login_required
def action_close(request, pk):
    item = get_object_or_404(ActionItem, pk=pk)
    if request.method == "POST":
        item.status = ActionStatus.CLOSED
        item.closure_note = request.POST.get("closure_note", "")
        item.closed_at = timezone.now()
        item.save(update_fields=["status", "closure_note", "closed_at", "updated_at"])
        messages.success(request, "Action closed.")
    return redirect("actions:my_actions")
