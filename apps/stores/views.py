from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.models import Role
from apps.core.audit import Action, log_event
from apps.core.permissions import role_required

from .forms import StoreForm
from .models import Store
from .selectors import stores_visible_to


@login_required
def store_list(request):
    stores = stores_visible_to(request.user)
    return render(request, "stores/store_list.html", {"stores": stores})


@role_required(Role.ADMIN, Role.COO, Role.PROFESSIONAL_USER)
def store_create(request):
    if request.method == "POST":
        form = StoreForm(request.POST)
        if form.is_valid():
            store = form.save()
            log_event(request, Action.STORE_CHANGED, store, label=f"{store.code} · {store.name}", details="Store created")
            messages.success(request, f"Store {store.code} created.")
            return redirect("stores:store_list")
    else:
        form = StoreForm()
    return render(request, "stores/store_form.html", {"form": form, "title": "Add Store"})


@role_required(Role.ADMIN, Role.COO, Role.PROFESSIONAL_USER)
def store_update(request, pk):
    store = get_object_or_404(Store, pk=pk)
    if request.method == "POST":
        original = Store.objects.get(pk=store.pk)  # the form updates `store` in place while validating
        form = StoreForm(request.POST, instance=store)
        if form.is_valid():
            changed = list(form.changed_data)
            form.save()
            if changed:
                log_event(request, Action.STORE_CHANGED, store, label=f"{store.code} · {store.name}",
                          details="Store edited: " + ", ".join(changed),
                          changes={f: [getattr(original, f, ""), getattr(store, f, "")] for f in changed})
            messages.success(request, "Store updated.")
            return redirect("stores:store_list")
    else:
        form = StoreForm(instance=store)
    return render(request, "stores/store_form.html", {"form": form, "title": f"Edit {store.code}"})
