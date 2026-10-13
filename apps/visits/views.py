from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.models import Role
from apps.core.permissions import role_required

from .forms import PhotoUploadForm, StartVisitForm, VisitResponseForm
from .models import ResponsePhoto, Visit, VisitResponse, VisitStatus
from .selectors import visits_visible_to
from .services import approve_visit, save_response, start_visit, submit_visit


def _ensure_can_edit(user, visit: Visit) -> bool:
    if user.is_admin_role:
        return True
    return visit.cluster_manager_id == user.id


@login_required
def visit_list(request):
    visits = visits_visible_to(request.user)[:200]
    return render(request, "visits/visit_list.html", {"visits": visits})


@role_required(Role.ADMIN, Role.CLUSTER_MANAGER, Role.INVENTORY_TEAM, Role.MARKETING_TEAM)
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
