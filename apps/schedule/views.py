from __future__ import annotations

import json
from datetime import date, datetime, time

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.dateparse import parse_date, parse_time
from django.views.decorators.http import require_http_methods

from apps.accounts.models import Role, User
from apps.core.audit import Action, diff, log_event

from .forms import VisitPlanForm
from .models import PlanStatus, VisitPlan
from .selectors import plans_visible_to
from .services import start_visit_from_plan


def _plan_label(plan: VisitPlan) -> str:
    return f"{plan.store.code} · {plan.store.name} ({plan.planned_date:%d %b %Y})"


def _plan_snapshot(plan: VisitPlan) -> dict:
    return {
        "Store": f"{plan.store.code} · {plan.store.name}",
        "Date": f"{plan.planned_date:%d %b %Y}",
        "Time": f"{plan.start_time:%H:%M}-{plan.end_time:%H:%M}",
        "Assigned to": plan.cluster_manager.employee_label,
        "Audit type": plan.get_audit_type_display(),
        "Status": plan.get_status_display(),
    }


# ---------- Color palette for the calendar (status-based) ----------
STATUS_COLORS = {
    PlanStatus.PLANNED:    {"bg": "#e0e7ff", "border": "#6366f1", "fg": "#3730a3"},
    PlanStatus.CHECKED_IN: {"bg": "#fef3c7", "border": "#f59e0b", "fg": "#92400e"},
    PlanStatus.COMPLETED:  {"bg": "#d1fae5", "border": "#10b981", "fg": "#065f46"},
    PlanStatus.MISSED:     {"bg": "#fee2e2", "border": "#ef4444", "fg": "#991b1b"},
    PlanStatus.CANCELLED:  {"bg": "#f1f5f9", "border": "#94a3b8", "fg": "#475569"},
}


def _can_edit(user, plan: VisitPlan) -> bool:
    return user.is_admin_role or plan.cluster_manager_id == user.id


def _serialize(plan: VisitPlan, user=None) -> dict:
    color = STATUS_COLORS.get(plan.status, STATUS_COLORS[PlanStatus.PLANNED])
    return {
        "id": str(plan.id),
        "title": f"{plan.store.code} · {plan.store.name}",
        "start": f"{plan.planned_date.isoformat()}T{plan.start_time.strftime('%H:%M:%S')}",
        "end":   f"{plan.planned_date.isoformat()}T{plan.end_time.strftime('%H:%M:%S')}",
        "backgroundColor": color["bg"],
        "borderColor": color["border"],
        "textColor": color["fg"],
        "extendedProps": {
            "store_code": plan.store.code,
            "store_name": plan.store.name,
            "cluster_manager": plan.cluster_manager.employee_label,
            "cluster_manager_id": str(plan.cluster_manager_id),
            "audit_type": plan.get_audit_type_display(),
            "status": plan.status,
            "status_label": plan.get_status_display(),
            "notes": plan.notes,
            "visit_id": str(plan.visit_id) if plan.visit_id else None,
            "detail_url": reverse("schedule:plan_detail", args=[plan.id]),
            "edit_url":   reverse("schedule:plan_edit",   args=[plan.id]),
            "delete_url": reverse("schedule:plan_delete", args=[plan.id]),
            "can_edit": bool(user and _can_edit(user, plan)),
            "start_visit_url": reverse("schedule:plan_start_visit", args=[plan.id]),
            "reschedule_url": reverse("schedule:api_event_reschedule", args=[plan.id]),
            "visit_url": reverse("visits:visit_detail", args=[plan.visit_id]) if plan.visit_id else None,
        },
    }


# ============================================================
# Page views
# ============================================================
@login_required
def calendar_view(request):
    cms = User.objects.filter(
        is_active=True,
        role__in=[Role.CLUSTER_MANAGER, Role.ADMIN, Role.COO, Role.INVENTORY_TEAM, Role.MARKETING_TEAM, Role.VM_TEAM, Role.GROCERY_HOME],
    ).order_by("employee_id", "full_name")
    return render(
        request,
        "schedule/calendar.html",
        {
            "cluster_managers": cms,
            "is_admin": request.user.is_admin_role,
            "current_user_id": str(request.user.id),
            "status_colors_json": json.dumps(STATUS_COLORS),
        },
    )


@login_required
def plan_detail(request, pk):
    plan = get_object_or_404(plans_visible_to(request.user), pk=pk)
    return render(request, "schedule/plan_detail.html", {"plan": plan, "can_edit": _can_edit(request.user, plan)})


@login_required
def plan_create(request):
    initial = {}
    if request.GET.get("date"):
        initial["planned_date"] = request.GET["date"]
    if request.GET.get("start"):
        initial["start_time"] = request.GET["start"]
    if request.GET.get("end"):
        initial["end_time"] = request.GET["end"]

    if request.method == "POST":
        form = VisitPlanForm(request.POST, user=request.user)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.created_by = request.user
            if not request.user.is_admin_role:
                plan.cluster_manager = request.user
            plan.save()
            log_event(request, Action.PLAN_CREATED, plan, label=_plan_label(plan),
                      details=f"{plan.start_time:%H:%M}-{plan.end_time:%H:%M} · for {plan.cluster_manager.employee_label}")
            messages.success(request, "Visit planned.")
            return redirect("schedule:calendar")
    else:
        form = VisitPlanForm(initial=initial, user=request.user)
    return render(request, "schedule/plan_form.html", {"form": form, "title": "New Plan"})


@login_required
def plan_edit(request, pk):
    plan = get_object_or_404(VisitPlan, pk=pk)
    if not _can_edit(request.user, plan):
        return HttpResponseForbidden()
    if request.method == "POST":
        before = _plan_snapshot(plan)
        form = VisitPlanForm(request.POST, instance=plan, user=request.user)
        if form.is_valid():
            form.save()
            changes = diff(before, _plan_snapshot(plan))
            if changes:
                log_event(request, Action.PLAN_UPDATED, plan, label=_plan_label(plan),
                          details="Changed: " + ", ".join(changes), changes=changes)
            messages.success(request, "Plan updated.")
            return redirect("schedule:plan_detail", pk=plan.pk)
    else:
        form = VisitPlanForm(instance=plan, user=request.user)
    return render(request, "schedule/plan_form.html", {"form": form, "title": "Edit Plan", "plan": plan})


@login_required
@require_http_methods(["POST"])
def plan_delete(request, pk):
    plan = get_object_or_404(VisitPlan, pk=pk)
    if not _can_edit(request.user, plan):
        return HttpResponseForbidden()
    log_event(request, Action.PLAN_DELETED, plan, label=_plan_label(plan),
              details=f"for {plan.cluster_manager.employee_label} · {plan.get_status_display()}")
    plan.delete()
    messages.success(request, "Plan removed.")
    return redirect("schedule:calendar")


@login_required
@require_http_methods(["POST"])
def plan_start_visit(request, pk):
    plan = get_object_or_404(VisitPlan, pk=pk)
    if not _can_edit(request.user, plan):
        return HttpResponseForbidden()
    try:
        start_visit_from_plan(plan=plan, user=request.user)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("schedule:plan_detail", pk=plan.pk)
    visit = plan.visit
    log_event(request, Action.VISIT_STARTED, visit,
              label=f"{visit.store.code} · {visit.store.name} ({visit.visit_date:%d %b %Y})",
              details=f"{visit.template.name} · started from schedule plan")
    messages.success(request, "Visit started from plan.")
    return redirect("visits:visit_fill", pk=plan.visit_id)


# ============================================================
# JSON API (for FullCalendar)
# ============================================================
@login_required
def api_events(request):
    qs = plans_visible_to(request.user)

    start = request.GET.get("start")
    end = request.GET.get("end")
    if start:
        qs = qs.filter(planned_date__gte=parse_date(start[:10]))
    if end:
        qs = qs.filter(planned_date__lte=parse_date(end[:10]))

    cm = request.GET.get("cm")
    if cm:
        qs = qs.filter(cluster_manager_id=cm)

    status = request.GET.get("status")
    if status:
        qs = qs.filter(status=status)

    return JsonResponse([_serialize(p, request.user) for p in qs], safe=False)


@login_required
@require_http_methods(["POST"])
def api_event_reschedule(request, pk):
    plan = get_object_or_404(VisitPlan, pk=pk)
    if not _can_edit(request.user, plan):
        return HttpResponseForbidden()
    try:
        payload = json.loads(request.body or "{}")
        new_start = datetime.fromisoformat(payload["start"])
        new_end = datetime.fromisoformat(payload["end"])
    except (KeyError, ValueError, json.JSONDecodeError):
        return HttpResponseBadRequest("Invalid payload")
    before = _plan_snapshot(plan)
    plan.planned_date = new_start.date()
    plan.start_time = new_start.time().replace(microsecond=0)
    plan.end_time = new_end.time().replace(microsecond=0)
    plan.save(update_fields=["planned_date", "start_time", "end_time", "updated_at"])
    changes = diff(before, _plan_snapshot(plan))
    if changes:
        log_event(request, Action.PLAN_RESCHEDULED, plan, label=_plan_label(plan), changes=changes,
                  details="Moved on the calendar")
    return JsonResponse(_serialize(plan, request.user))
