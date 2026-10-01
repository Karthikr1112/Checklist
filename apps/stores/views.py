from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.models import Role
from apps.core.permissions import role_required

from .forms import StoreForm
from .models import Store
from .selectors import stores_visible_to


@login_required
def store_list(request):
    stores = stores_visible_to(request.user)
    return render(request, "stores/store_list.html", {"stores": stores})


@role_required(Role.ADMIN)
def store_create(request):
    if request.method == "POST":
        form = StoreForm(request.POST)
        if form.is_valid():
            store = form.save()
            messages.success(request, f"Store {store.code} created.")
            return redirect("stores:store_list")
    else:
        form = StoreForm()
    return render(request, "stores/store_form.html", {"form": form, "title": "Add Store"})


@role_required(Role.ADMIN)
def store_update(request, pk):
    store = get_object_or_404(Store, pk=pk)
    if request.method == "POST":
        form = StoreForm(request.POST, instance=store)
        if form.is_valid():
            form.save()
            messages.success(request, "Store updated.")
            return redirect("stores:store_list")
    else:
        form = StoreForm(instance=store)
    return render(request, "stores/store_form.html", {"form": form, "title": f"Edit {store.code}"})
