from __future__ import annotations

import json
from datetime import date, datetime, time
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_time
from django.views.decorators.http import require_http_methods

from apps.accounts.models import Role, User
from apps.checklists.models import ChecklistTemplate
from apps.core.audit import Action, diff, log_event

from .exports import export_plans_to_csv, export_plans_to_excel
from .forms import VisitPlanForm
from .models import PlanStatus, VisitPlan
from .selectors import plans_visible_to
from .services import resolve_template_for_user, start_visit_from_plan, templates_for_user


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
    if user.is_admin_role:
        return True
    if plan.cluster_manager_id == user.id or plan.created_by_id == user.id:
        return True
    if getattr(user, "is_marketing_head", False) and plan.cluster_manager.role == Role.MARKETING_TEAM:
        return True
    if getattr(user, "is_vm_manager", False) and plan.cluster_manager.role == Role.VM_TEAM:
        return True
    if getattr(user, "is_grocery_home_head", False) and plan.cluster_manager.role == Role.GROCERY_HOME:
        return True
    return False


def _can_start(user, plan: VisitPlan) -> bool:
    """Only the assigned user (who conducts the visit) or Admins can start a visit."""
    if not user or not user.is_authenticated:
        return False
    if user.is_admin_role:
        return True
    return plan.cluster_manager_id == user.id



def _serialize(plan: VisitPlan, user=None) -> dict:
    color = STATUS_COLORS.get(plan.status, STATUS_COLORS[PlanStatus.PLANNED])
    show_cm = bool(
        user and (
            user.is_admin_role
            or getattr(user, "is_department_head", False)
            or user.role in (Role.CLUSTER_MANAGER, Role.STORE_MANAGER)
        )
    )
    cm_suffix = f" [{plan.cluster_manager.get_short_name()}]" if show_cm else ""
    return {
        "id": str(plan.id),
        "title": f"{plan.store.code} · {plan.store.name}{cm_suffix}",
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
            "created_by": plan.created_by.employee_label if plan.created_by else None,
            "template_name": plan.template.name if plan.template else None,
            "audit_type": plan.get_audit_type_display(),
            "status": plan.status,
            "status_label": plan.get_status_display(),
            "notes": plan.notes,
            "edit_reason": plan.edit_reason,
            "visit_id": str(plan.visit_id) if plan.visit_id else None,
            "detail_url": reverse("schedule:plan_detail", args=[plan.id]),
            "edit_url":   reverse("schedule:plan_edit",   args=[plan.id]),
            "delete_url": reverse("schedule:plan_delete", args=[plan.id]),
            "can_edit": bool(user and _can_edit(user, plan)),
            "can_start": bool(user and _can_start(user, plan)),
            "start_visit_url": reverse("schedule:plan_start_visit", args=[plan.id]),
            "reschedule_url": reverse("schedule:api_event_reschedule", args=[plan.id]),
            "export_excel_url": reverse("schedule:plan_export_excel", args=[plan.id]),
            "export_csv_url": reverse("schedule:plan_export_csv", args=[plan.id]),
            "visit_url": reverse("visits:visit_detail", args=[plan.visit_id]) if plan.visit_id else None,
            "store_name": f"{plan.store.code} · {plan.store.name}",
            "store_latitude": float(plan.store.latitude) if plan.store.latitude is not None else None,
            "store_longitude": float(plan.store.longitude) if plan.store.longitude is not None else None,
            "store_geofence_radius": plan.store.geofence_radius_meters or 250,
        },
    }


# ============================================================
# Page views
# ============================================================
@login_required
def calendar_view(request):
    user = request.user
    can_filter_users = False
    filter_label = "All Users"

    if user.is_admin_role or user.role in (Role.CLUSTER_MANAGER, Role.STORE_MANAGER):
        cms = User.objects.filter(
            is_active=True,
            role__in=[
                Role.CLUSTER_MANAGER,
                Role.ADMIN,
                Role.COO,
                Role.PROFESSIONAL_USER,
                Role.INVENTORY_TEAM,
                Role.MARKETING_TEAM,
                Role.VM_TEAM,
                Role.GROCERY_HOME,
                Role.STORE_MANAGER,
            ],
        ).order_by("employee_id", "full_name")
        can_filter_users = True
        filter_label = "All Users"
    elif getattr(user, "is_marketing_head", False):
        cms = User.objects.filter(is_active=True, role=Role.MARKETING_TEAM).order_by("full_name")
        can_filter_users = True
        filter_label = "All Marketing Team"
    elif getattr(user, "is_vm_manager", False):
        cms = User.objects.filter(is_active=True, role=Role.VM_TEAM).order_by("full_name")
        can_filter_users = True
        filter_label = "All VM Team"
    elif getattr(user, "is_grocery_home_head", False):
        cms = User.objects.filter(is_active=True, role=Role.GROCERY_HOME).order_by("full_name")
        can_filter_users = True
        filter_label = "All Grocery & Home Team"
    else:
        cms = User.objects.none()
        can_filter_users = False
        filter_label = ""

    return render(
        request,
        "schedule/calendar.html",
        {
            "cluster_managers": cms,
            "can_filter_users": can_filter_users,
            "filter_label": filter_label,
            "is_admin": user.is_admin_role,
            "current_user_id": str(user.id),
            "status_colors_json": json.dumps(STATUS_COLORS),
        },
    )


@login_required
def plan_detail(request, pk):
    plan = get_object_or_404(plans_visible_to(request.user), pk=pk)
    return render(
        request,
        "schedule/plan_detail.html",
        {
            "plan": plan,
            "can_edit": _can_edit(request.user, plan),
            "can_start": _can_start(request.user, plan),
        },
    )


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
            try:
                plan = form.save(commit=False)
                plan.created_by = request.user
                if not request.user.is_admin_role:
                    plan.cluster_manager = request.user
                plan.save()
                log_event(request, Action.PLAN_CREATED, plan, label=_plan_label(plan),
                          details=f"{plan.start_time:%H:%M}-{plan.end_time:%H:%M} · for {plan.cluster_manager.employee_label}")
                messages.success(request, "Visit planned.")
                return redirect("schedule:calendar")
            except IntegrityError:
                form.add_error(
                    "start_time",
                    "A visit plan is already scheduled for this user on this date at this start time. Please choose a different start time.",
                )
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
            try:
                plan = form.save()
                changes = diff(before, _plan_snapshot(plan))
                edit_reason = form.cleaned_data.get("edit_reason", "").strip()
                details = f"Reason: {edit_reason}"
                if changes:
                    details += " · Changed: " + ", ".join(changes)
                log_event(request, Action.PLAN_UPDATED, plan, label=_plan_label(plan),
                          details=details, changes=changes)
                messages.success(request, "Plan updated.")
                return redirect("schedule:plan_detail", pk=plan.pk)
            except IntegrityError:
                form.add_error(
                    "start_time",
                    "A visit plan is already scheduled for this user on this date at this start time. Please choose a different start time.",
                )
    else:
        form = VisitPlanForm(instance=plan, user=request.user)
    return render(request, "schedule/plan_form.html", {"form": form, "title": "Edit Plan", "plan": plan})


@login_required
@require_http_methods(["POST"])
def plan_delete(request, pk):
    plan = get_object_or_404(VisitPlan, pk=pk)
    if not _can_edit(request.user, plan):
        return HttpResponseForbidden()

    delete_reason = request.POST.get("delete_reason", "").strip()
    if not delete_reason:
        messages.error(request, "A reason for deleting the scheduled plan is mandatory.")
        return redirect("schedule:calendar")

    log_event(
        request,
        Action.PLAN_DELETED,
        plan,
        label=_plan_label(plan),
        details=f"Reason: {delete_reason} · for {plan.cluster_manager.employee_label} · {plan.get_status_display()}",
    )
    plan.delete()
    messages.success(request, f"Plan for {plan.store.code} deleted.")
    return redirect("schedule:calendar")


@login_required
@require_http_methods(["POST"])
def plan_start_visit(request, pk):
    plan = get_object_or_404(VisitPlan, pk=pk)
    if not _can_start(request.user, plan):
        return HttpResponseForbidden()

    raw_lat = (request.POST.get("user_latitude") or "").strip()
    raw_lon = (request.POST.get("user_longitude") or "").strip()
    user_lat = Decimal(raw_lat) if raw_lat else None
    user_lon = Decimal(raw_lon) if raw_lon else None

    from apps.core.geo import verify_user_at_store
    is_valid, error_msg, dist = verify_user_at_store(
        store=plan.store,
        user_latitude=user_lat,
        user_longitude=user_lon,
        is_admin_bypass=request.user.is_admin_role,
    )
    if not is_valid:
        messages.error(request, error_msg)
        return redirect("schedule:plan_detail", pk=plan.pk)

    try:
        start_visit_from_plan(
            plan=plan,
            user=request.user,
            started_latitude=user_lat,
            started_longitude=user_lon,
            started_distance_meters=dist if user_lat is not None else None,
        )
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

    start = request.GET.get("date_from") or request.GET.get("start")
    end = request.GET.get("date_to") or request.GET.get("end")
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


# ============================================================
# Export Views (Excel & CSV with all details - Admin, COO, Professional User only)
# ============================================================
def _filter_plans_for_export(request):
    qs = plans_visible_to(request.user).select_related(
        "store", "cluster_manager", "created_by", "template", "visit", "visit__approved_by"
    )

    # Export only planned schedules as requested
    qs = qs.filter(status=PlanStatus.PLANNED)
    filter_desc_parts = ["Status: Planned Only"]

    cm = request.GET.get("cm")
    if cm:
        try:
            qs = qs.filter(cluster_manager_id=cm)
            cm_obj = User.objects.filter(pk=cm).first()
            if cm_obj:
                filter_desc_parts.append(f"User: {cm_obj.employee_label}")
        except Exception:
            pass

    date_from_str = request.GET.get("date_from") or request.GET.get("start")
    date_to_str = request.GET.get("date_to") or request.GET.get("end")

    has_date_filter = False
    if date_from_str:
        d_start = parse_date(date_from_str[:10])
        if d_start:
            qs = qs.filter(planned_date__gte=d_start)
            filter_desc_parts.append(f"From: {d_start:%d-%b-%Y}")
            has_date_filter = True
    if date_to_str:
        d_end = parse_date(date_to_str[:10])
        if d_end:
            qs = qs.filter(planned_date__lte=d_end)
            filter_desc_parts.append(f"To: {d_end:%d-%b-%Y}")
            has_date_filter = True

    # If no date filter is selected and 'all' is not requested, default to current month
    if not has_date_filter and not request.GET.get("all"):
        import calendar
        today = timezone.localdate()
        month_start = today.replace(day=1)
        _, num_days = calendar.monthrange(today.year, today.month)
        month_end = today.replace(day=num_days)
        qs = qs.filter(planned_date__gte=month_start, planned_date__lte=month_end)
        filter_desc_parts.append(f"Month: {today.strftime('%B %Y')} ({month_start:%d-%b-%Y} to {month_end:%d-%b-%Y})")

    desc = " | ".join(filter_desc_parts)
    return qs.order_by("planned_date", "start_time"), desc


@login_required
def plan_export_excel(request):
    if not request.user.is_admin_role:
        return HttpResponseForbidden("Only Admin, COO, and Professional users can export schedules.")
    qs, desc = _filter_plans_for_export(request)
    timestamp = timezone.localtime(timezone.now()).strftime("%Y%m%d_%H%M%S")
    return export_plans_to_excel(
        qs,
        filename=f"Planned_Schedules_{timestamp}.xlsx",
        filter_description=desc,
    )


@login_required
def plan_export_csv(request):
    if not request.user.is_admin_role:
        return HttpResponseForbidden("Only Admin, COO, and Professional users can export schedules.")
    qs, _ = _filter_plans_for_export(request)
    timestamp = timezone.localtime(timezone.now()).strftime("%Y%m%d_%H%M%S")
    return export_plans_to_csv(
        qs,
        filename=f"Planned_Schedules_{timestamp}.csv",
    )


@login_required
def single_plan_export_excel(request, pk):
    if not request.user.is_admin_role:
        return HttpResponseForbidden("Only Admin, COO, and Professional users can export schedules.")
    plan = get_object_or_404(
        plans_visible_to(request.user).select_related(
            "store", "cluster_manager", "created_by", "template", "visit", "visit__approved_by"
        ),
        pk=pk,
    )
    return export_plans_to_excel(
        [plan],
        filename=f"Schedule_{plan.store.code}_{plan.planned_date:%Y%m%d}.xlsx",
        filter_description=f"Single Plan: {plan.store.code} on {plan.planned_date:%d-%b-%Y}",
    )


@login_required
def single_plan_export_csv(request, pk):
    if not request.user.is_admin_role:
        return HttpResponseForbidden("Only Admin, COO, and Professional users can export schedules.")
    plan = get_object_or_404(
        plans_visible_to(request.user).select_related(
            "store", "cluster_manager", "created_by", "template", "visit", "visit__approved_by"
        ),
        pk=pk,
    )
    return export_plans_to_csv(
        [plan],
        filename=f"Schedule_{plan.store.code}_{plan.planned_date:%Y%m%d}.csv",
    )

