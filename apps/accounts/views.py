from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

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
    pending_count = User.objects.filter(approval_status=ApprovalStatus.PENDING).count()
    return render(
        request,
        "accounts/user_list.html",
        {"users": users, "pending_count": pending_count, "role_choices": Role.choices},
    )


@role_required(Role.ADMIN)
def user_create(request):
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"User {user.email} created.")
            return redirect("accounts:user_edit", pk=user.pk)
    else:
        form = UserCreateForm()
    return render(request, "accounts/user_form.html", {"form": form, "title": "Add User"})


@role_required(Role.ADMIN)
def user_edit(request, pk):
    target = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        form = UserEditForm(request.POST, instance=target)
        if form.is_valid():
            form.save()
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
    messages.success(request, f"{target.full_name or target.email} approved.")
    return redirect("accounts:user_list")


@role_required(Role.ADMIN)
@require_http_methods(["POST"])
def user_reject(request, pk):
    target = get_object_or_404(User, pk=pk)
    target.approval_status = ApprovalStatus.REJECTED
    target.is_active = False
    target.save(update_fields=["approval_status", "is_active"])
    messages.success(request, f"{target.full_name or target.email} rejected.")
    return redirect("accounts:user_list")
