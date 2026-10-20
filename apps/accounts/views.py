import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_http_methods

from apps.core.audit import Action, diff, log_event
from apps.core.models import AuditLog
from apps.core.permissions import role_required

from .forms import UserCreateForm, UserEditForm
from .models import ApprovalStatus, Role, User


@login_required
def profile(request):
    return render(request, "accounts/profile.html", {"user_obj": request.user})


@login_required
def pending_approval(request):
    """Landing page for users awaiting admin approval."""
    return render(request, "accounts/pending_approval.html", {"user_obj": request.user})


@role_required(Role.ADMIN)
def user_list(request):
    users = User.objects.order_by("approval_status", "full_name")
    pending_count = User.objects.filter(approval_status__iexact=ApprovalStatus.PENDING).count()
    return render(
        request,
        "accounts/user_list.html",
        {"users": users, "pending_count": pending_count, "role_choices": Role.choices},
    )


def _user_snapshot(user: User) -> dict:
    """The user fields worth auditing, as readable values."""
    return {
        "Email": user.email,
        "Employee Name": user.full_name,
        "Employee ID": user.employee_id,
        "Phone": user.phone,
        "Role": user.get_role_display(),
        "Marketing Role": user.marketing_role,
        "VM Role": user.vm_role,
        "Grocery & Home Role": user.gh_role,
        "All stores access": "Yes" if user.all_stores_access else "No",
        "Active": "Yes" if user.is_active else "No",
        "Stores": ", ".join(user.assigned_stores.order_by("code").values_list("code", flat=True)) if user.pk else "",
    }


@role_required(Role.ADMIN)
def user_create(request):
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            log_event(request, Action.USER_CREATED, user, label=user.employee_label,
                      details=f"{user.get_role_display()} · {user.email}")
            messages.success(request, f"User {user.email} created.")
            return redirect("accounts:user_edit", pk=user.pk)
    else:
        form = UserCreateForm()
    return render(request, "accounts/user_form.html", {"form": form, "title": "Add User"})


@role_required(Role.ADMIN)
def user_edit(request, pk):
    target = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        before = _user_snapshot(target)
        form = UserEditForm(request.POST, instance=target)
        if form.is_valid():
            form.save()
            changes = diff(before, _user_snapshot(target))
            if changes:
                log_event(request, Action.USER_UPDATED, target, label=target.employee_label,
                          details="Changed: " + ", ".join(changes), changes=changes)
            messages.success(request, f"{target.full_name or target.email} updated.")
            return redirect("accounts:user_list")
    else:
        form = UserEditForm(instance=target)
    return render(
        request,
        "accounts/user_edit.html",
        {"form": form, "target": target, "title": f"Edit {target.full_name or target.email}"},
    )


@role_required(Role.ADMIN)
@require_http_methods(["POST"])
def user_approve(request, pk):
    target = get_object_or_404(User, pk=pk)
    role = request.POST.get("role") or target.role
    if role not in dict(Role.choices):
        return HttpResponseBadRequest("Invalid role")
    target.role = role
    target.approval_status = ApprovalStatus.APPROVED
    target.approved_at = timezone.now()
    target.approved_by = request.user
    target.is_active = True
    target.save(update_fields=[
        "role", "approval_status", "approved_at", "approved_by", "is_active"
    ])
    log_event(request, Action.USER_APPROVED, target, label=target.employee_label,
              details=f"Approved as {target.get_role_display()}")
    messages.success(request, f"{target.full_name or target.email} approved.")
    return redirect("accounts:user_list")


@role_required(Role.ADMIN)
@require_http_methods(["POST"])
def user_reject(request, pk):
    target = get_object_or_404(User, pk=pk)
    target.approval_status = ApprovalStatus.REJECTED
    target.is_active = False
    target.save(update_fields=["approval_status", "is_active"])
    log_event(request, Action.USER_REJECTED, target, label=target.employee_label)
    messages.success(request, f"{target.full_name or target.email} rejected.")
    return redirect("accounts:user_list")


AUDIT_FILTER_KEYS = ("q", "user", "action", "date_from", "date_to")


@role_required(Role.ADMIN)
def audit_log(request):
    """Admin-only: who did what, when."""
    entries = AuditLog.objects.select_related("actor")
    params = request.GET
    q = params.get("q", "").strip()
    if q:
        entries = entries.filter(
            Q(actor_label__icontains=q) | Q(object_label__icontains=q) | Q(details__icontains=q)
        )
    if params.get("user"):
        try:
            entries = entries.filter(actor_id=uuid.UUID(params["user"]))
        except ValueError:
            pass
    if params.get("action") in AuditLog.Action.values:
        entries = entries.filter(action=params["action"])
    try:
        date_from = parse_date(params.get("date_from", "") or "")
        date_to = parse_date(params.get("date_to", "") or "")
    except ValueError:
        date_from = date_to = None
    if date_from:
        entries = entries.filter(created_at__date__gte=date_from)
    if date_to:
        entries = entries.filter(created_at__date__lte=date_to)

    page_obj = Paginator(entries, 50).get_page(params.get("page"))
    filters = {k: params.get(k, "") for k in AUDIT_FILTER_KEYS}
    querystring = params.copy()
    querystring.pop("page", None)
    people = sorted(
        User.objects.filter(pk__in=AuditLog.objects.exclude(actor=None).values("actor_id")),
        key=lambda u: u.employee_label.lower(),
    )
    return render(
        request,
        "accounts/audit_log.html",
        {
            "page_obj": page_obj,
            "filters": filters,
            "filters_active": any(filters.values()),
            "filter_qs": querystring.urlencode(),
            "people_options": people,
            "action_options": AuditLog.Action.choices,
        },
    )
