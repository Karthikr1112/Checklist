from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.core.audit import Action, diff, log_event
from apps.visits.models import VisitResponse
from apps.visits.selectors import visits_visible_to

from .forms import ActionItemForm
from .models import ActionItem, ActionStatus


def _can_view(user, item: ActionItem) -> bool:
    return (
        user.is_admin_role
        or item.owner_id == user.id
        or visits_visible_to(user).filter(pk=item.response.visit_id).exists()
    )


def _can_update(user, item: ActionItem) -> bool:
    """Owner, the person who conducted the visit, or an admin."""
    return user.is_admin_role or user.id in (item.owner_id, item.response.visit.cluster_manager_id)


def _action_label(item: ActionItem) -> str:
    return f"{item.title} · {item.response.visit.store.code}"


def _set_status(request, item: ActionItem, status: str, closure_note: str) -> None:
    before = {"Status": item.get_status_display(), "Note": item.closure_note}
    item.status = status
    item.closure_note = closure_note
    item.closed_at = timezone.now() if status in (ActionStatus.CLOSED, ActionStatus.NOT_REQUIRED) else None
    item.save(update_fields=["status", "closure_note", "closed_at", "updated_at"])
    changes = diff(before, {"Status": item.get_status_display(), "Note": item.closure_note})
    if changes:
        log_event(request, Action.ACTION_UPDATED, item, label=_action_label(item),
                  details=f"Now {item.get_status_display()} · owner {item.owner.employee_label}", changes=changes)


def _redirect_back(request, item: ActionItem):
    nxt = request.POST.get("next", "")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return redirect(nxt)
    return redirect("actions:action_detail", pk=item.pk)


@login_required
def my_actions(request):
    items = list(ActionItem.objects.filter(owner=request.user).select_related("response__visit__store"))
    active_count = sum(1 for a in items if a.status in (ActionStatus.OPEN, ActionStatus.IN_PROGRESS))
    response = render(
        request,
        "actions/my_actions.html",
        {"items": items, "today": timezone.localdate(), "active_count": active_count},
    )
    # Rows rendered with a "New" tag above; from now on they no longer count as new.
    ActionItem.objects.filter(owner=request.user, seen_at__isnull=True).update(seen_at=timezone.now())
    return response


@login_required
def all_actions(request):
    visible_visits = visits_visible_to(request.user).values_list("id", flat=True)
    items = list(
        ActionItem.objects.filter(response__visit_id__in=list(visible_visits))
        .select_related("owner", "response__visit__store", "response__question")
    )
    open_count = sum(1 for a in items if a.status in (ActionStatus.OPEN, ActionStatus.IN_PROGRESS))
    return render(
        request,
        "actions/all_actions.html",
        {"items": items, "today": timezone.localdate(), "open_count": open_count},
    )


@login_required
def action_detail(request, pk):
    item = get_object_or_404(
        ActionItem.objects.select_related(
            "owner",
            "response__question__section",
            "response__visit__store",
            "response__visit__template",
            "response__visit__cluster_manager",
        ).prefetch_related("response__photos"),
        pk=pk,
    )
    if not _can_view(request.user, item):
        raise Http404
    if item.owner_id == request.user.id and item.seen_at is None:
        item.seen_at = timezone.now()
        item.save(update_fields=["seen_at"])
    return render(
        request,
        "actions/action_detail.html",
        {
            "item": item,
            "response": item.response,
            "visit": item.response.visit,
            "can_update": _can_update(request.user, item),
            "status_choices": ActionStatus.choices,
            "is_overdue": bool(
                item.due_date
                and item.due_date < timezone.localdate()
                and item.status in (ActionStatus.OPEN, ActionStatus.IN_PROGRESS)
            ),
        },
    )


@login_required
@require_POST
def action_update(request, pk):
    item = get_object_or_404(ActionItem.objects.select_related("response__visit"), pk=pk)
    if not _can_update(request.user, item):
        return HttpResponseForbidden("You cannot update this action.")
    status = request.POST.get("status", "")
    if status not in ActionStatus.values:
        messages.error(request, "Please choose a valid status.")
        return redirect("actions:action_detail", pk=item.pk)
    _set_status(request, item, status, request.POST.get("closure_note", "").strip())
    messages.success(request, f"Action marked {item.get_status_display()}.")
    return redirect("actions:action_detail", pk=item.pk)


@login_required
def action_create(request, response_pk):
    response = get_object_or_404(VisitResponse.objects.select_related("visit"), pk=response_pk)
    if request.method == "POST":
        form = ActionItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.response = response
            if item.owner_id == request.user.id:
                item.seen_at = timezone.now()  # nothing new about an action you assigned yourself
            item.save()
            log_event(request, Action.ACTION_CREATED, item, label=_action_label(item),
                      details=f"{response.question.code} · owner {item.owner.employee_label}"
                              + (f" · due {item.due_date:%d %b %Y}" if item.due_date else ""))
            messages.success(request, "Action created.")
            return redirect("visits:visit_fill", pk=response.visit_id)
    else:
        form = ActionItemForm(initial={"title": f"Action for {response.question.code}"})
    return render(request, "actions/action_form.html", {"form": form, "response": response})


@login_required
@require_POST
def action_close(request, pk):
    item = get_object_or_404(ActionItem.objects.select_related("response__visit"), pk=pk)
    if not _can_update(request.user, item):
        return HttpResponseForbidden("You cannot close this action.")
    _set_status(request, item, ActionStatus.CLOSED, request.POST.get("closure_note", "").strip())
    messages.success(request, "Action closed.")
    return _redirect_back(request, item)
