from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .selectors import dashboard_summary


@login_required
def index(request):
    summary = dashboard_summary(request.user)
    return render(request, "dashboard/index.html", summary)
