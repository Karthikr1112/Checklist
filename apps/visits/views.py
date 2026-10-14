import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from apps.accounts.models import Role, User
from apps.checklists.models import ChecklistTemplate
from apps.core.permissions import role_required

from apps.schedule.models import PlanStatus, VisitPlan

from .forms import PhotoUploadForm, StartVisitForm, VisitEditForm, VisitResponseForm
from .models import AuditType, ResponsePhoto, Visit, VisitResponse, VisitStatus
from .selectors import visits_visible_to
from .services import approve_visit, save_response, start_visit, submit_visit


def _ensure_can_edit(user, visit: Visit) -> bool:
    if user.is_admin_role:
        return True
    return visit.cluster_manager_id == user.id


def _can_manage(user, visit: Visit) -> bool:
    """Edit details / delete: admins always; the visit's owner until it's approved."""
    if user.is_admin_role:
        return True
    return visit.cluster_manager_id == user.id and visit.status != VisitStatus.APPROVED


VISIT_FILTER_KEYS = ("q", "store", "department", "conducted_by", "status", "audit_type", "date_from", "date_to")


def _filter_visits(qs, params):
    """Apply the Visits page filters. Unknown / invalid values are ignored."""
    q = params.get("q", "").strip()
    if q:
        qs = qs.filter(
            Q(store__code__icontains=q)
            | Q(store__name__icontains=q)
            | Q(cluster_manager__full_name__icontains=q)
            | Q(cluster_manager__employee_id__icontains=q)
            | Q(template__name__icontains=q)
        )
    if params.get("store"):
        qs = qs.filter(store__code=params["store"])
    if params.get("department") in ChecklistTemplate.Audience.values:
        qs = qs.filter(template__audience=params["department"])
    if params.get("conducted_by"):
        try:
            qs = qs.filter(cluster_manager_id=uuid.UUID(params["conducted_by"]))
        except ValueError:
            pass
    if params.get("status") in VisitStatus.values:
        qs = qs.filter(status=params["status"])
    if params.get("audit_type") in AuditType.values:
        qs = qs.filter(audit_type=params["audit_type"])
    date_from = parse_date(params.get("date_from", "") or "")
    if date_from:
        qs = qs.filter(visit_date__gte=date_from)
    date_to = parse_date(params.get("date_to", "") or "")
    if date_to:
        qs = qs.filter(visit_date__lte=date_to)
    return qs


@login_required
def visit_list(request):
    visible = visits_visible_to(request.user)
    try:
        filtered = _filter_visits(visible, request.GET)
    except ValueError:  # malformed date
        filtered = visible
    paginator = Paginator(filtered, 50)
    page_obj = paginator.get_page(request.GET.get("page"))

    # Dropdown options come only from visits this user can already see.
    store_options = (
        visible.order_by("store__code").values_list("store__code", "store__name").distinct()
    )
    people_ids = visible.values("cluster_manager_id")
    people_options = sorted(
        User.objects.filter(pk__in=people_ids), key=lambda u: u.employee_label.lower()
    )
    audiences = set(visible.values_list("template__audience", flat=True).distinct())
    department_options = [(v, l) for v, l in ChecklistTemplate.Audience.choices if v in audiences]

    filters = {k: request.GET.get(k, "") for k in VISIT_FILTER_KEYS}
    querystring = request.GET.copy()
    querystring.pop("page", None)
    return render(
        request,
        "visits/visit_list.html",
        {
            "visits": page_obj,
            "page_obj": page_obj,
            "filters": filters,
            "filters_active": any(filters.values()),
            "filter_qs": querystring.urlencode(),
            "store_options": store_options,
            "people_options": people_options,
            "department_options": department_options,
            "status_options": VisitStatus.choices,
            "audit_type_options": AuditType.choices,
        },
    )


@role_required(Role.ADMIN, Role.CLUSTER_MANAGER, Role.INVENTORY_TEAM, Role.MARKETING_TEAM, Role.VM_TEAM, Role.GROCERY_HOME)
def visit_start(request):
    if request.method == "POST":
        form = StartVisitForm(request.POST, user=request.user)
        if form.is_valid():
            visit = start_visit(
                store=form.cleaned_data["store"],
                template=form.cleaned_data["template"],
                cluster_manager=request.user,
                visit_date=form.cleaned_data["visit_date"],
                audit_type=form.cleaned_data["audit_type"],
            )
            messages.success(request, "Visit started.")
            return redirect("visits:visit_fill", pk=visit.pk)
    else:
        form = StartVisitForm(user=request.user)
    return render(request, "visits/visit_start.html", {"form": form})


@login_required
def visit_detail(request, pk):
    visit = get_object_or_404(visits_visible_to(request.user), pk=pk)
    responses = visit.responses.select_related("question__section").prefetch_related("photos")
    grouped: dict = {}
    for r in responses:
        grouped.setdefault(r.question.section, []).append(r)
    return render(
        request,
        "visits/visit_detail.html",
        {
            "visit": visit,
            "grouped": grouped,
            "can_approve": visit.can_be_approved_by(request.user),
        },
    )


@login_required
def visit_fill(request, pk):
    visit = get_object_or_404(visits_visible_to(request.user), pk=pk)
    if not _ensure_can_edit(request.user, visit):
        return HttpResponseForbidden("You cannot edit this visit.")

    responses = visit.responses.select_related("question__section").prefetch_related("photos")
    grouped: dict = {}
    for r in responses:
        grouped.setdefault(r.question.section, []).append(r)

    return render(
        request,
        "visits/visit_fill.html",
        {"visit": visit, "grouped": grouped, "photo_form": PhotoUploadForm()},
    )


@login_required
@require_POST
def response_save(request, response_pk):
    response = get_object_or_404(VisitResponse.objects.select_related("visit"), pk=response_pk)
    if not _ensure_can_edit(request.user, response.visit):
        return HttpResponseForbidden()

    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

    form = VisitResponseForm(request.POST, instance=response)
    if form.is_valid():
        save_response(
            response=response,
            value=form.cleaned_data["response"] or "",
            evidence={k: v for k, v in request.POST.items() if k.startswith("evidence__")},
            observation=form.cleaned_data["observation"],
        )
        if is_ajax:
            visit = response.visit
            return JsonResponse({
                "ok": True,
                "response_pk": response.pk,
                "compliance_pct": str(visit.compliance_pct),
                "answered": visit.answered_count,
                "total": visit.total_questions,
            })
        messages.success(request, f"{response.question.code} saved.")
        return redirect("visits:visit_fill", pk=response.visit_id)

    if is_ajax:
        return JsonResponse({"ok": False, "errors": form.errors}, status=400)
    messages.error(request, "Invalid response data.")
    return redirect("visits:visit_fill", pk=response.visit_id)


@login_required
def visit_edit(request, pk):
    visit = get_object_or_404(visits_visible_to(request.user), pk=pk)
    if not _can_manage(request.user, visit):
        return HttpResponseForbidden("You cannot edit this visit.")
    if request.method == "POST":
        form = VisitEditForm(request.POST, instance=visit, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Visit updated.")
            return redirect("visits:visit_detail", pk=visit.pk)
    else:
        form = VisitEditForm(instance=visit, user=request.user)
    return render(request, "visits/visit_edit.html", {"visit": visit, "form": form})


@login_required
@require_POST
def visit_delete(request, pk):
    visit = get_object_or_404(visits_visible_to(request.user), pk=pk)
    if not _can_manage(request.user, visit):
        return HttpResponseForbidden("You cannot delete this visit.")
    # A schedule plan linked to this visit goes back to Planned rather than pointing at nothing.
    VisitPlan.objects.filter(visit=visit).update(visit=None, status=PlanStatus.PLANNED)
    label = f"{visit.store.code} on {visit.visit_date:%d %b %Y}"
    visit.delete()
    messages.success(request, f"Visit for {label} deleted.")
    return redirect("visits:visit_list")


@login_required
@require_POST
def visit_summary_save(request, pk):
    visit = get_object_or_404(visits_visible_to(request.user), pk=pk)
    if not _ensure_can_edit(request.user, visit) or not visit.is_vm_checklist:
        return HttpResponseForbidden()

    visit.summary = request.POST.get("summary", "").strip()
    visit.save(update_fields=["summary", "updated_at"])
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True})
    messages.success(request, "Visit summary saved.")
    return redirect("visits:visit_fill", pk=visit.pk)


@login_required
def response_photo_upload(request, response_pk):
    response = get_object_or_404(VisitResponse.objects.select_related("visit"), pk=response_pk)
    if not _ensure_can_edit(request.user, response.visit):
        return HttpResponseForbidden()
    if request.method != "POST":
        return redirect("visits:visit_fill", pk=response.visit_id)

    form = PhotoUploadForm(request.POST, request.FILES)
    if form.is_valid():
        ResponsePhoto.objects.create(
            response=response,
            image=form.cleaned_data["image"],
            caption=form.cleaned_data["caption"],
            uploaded_by=request.user,
        )
        messages.success(request, "Photo uploaded.")
    else:
        messages.error(request, "Photo upload failed.")
    return redirect("visits:visit_fill", pk=response.visit_id)


@login_required
def visit_submit(request, pk):
    visit = get_object_or_404(visits_visible_to(request.user), pk=pk)
    if not _ensure_can_edit(request.user, visit):
        return HttpResponseForbidden()
    if request.method == "POST":
        submit_visit(visit)
        messages.success(request, "Visit submitted for review.")
    return redirect("visits:visit_detail", pk=visit.pk)


@login_required
def visit_approve(request, pk):
    visit = get_object_or_404(Visit, pk=pk)
    if not visit.can_be_approved_by(request.user):
        return HttpResponseForbidden("You do not have permission to approve this visit.")
    if request.method == "POST" and visit.status == VisitStatus.SUBMITTED:
        approve_visit(visit, request.user)
        messages.success(request, f"Visit for {visit.store.code} approved.")
    return redirect("visits:visit_detail", pk=visit.pk)
