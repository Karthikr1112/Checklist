from django.conf import settings 
from django.conf.urls.static import static 
from django.contrib import admin 
from django.urls import include, path 
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),

    path("", RedirectView.as_view(
        pattern_name="dashboard:index",
        permanent=False
    )),

    # Fallbacks for /cl/ paths when running locally in development without reverse proxy
    path("cl/", RedirectView.as_view(pattern_name="dashboard:index", permanent=False)),
    path("cl/<path:subpath>", RedirectView.as_view(url="/%(subpath)s", permanent=False)),

    path("accounts/", include("apps.accounts.urls", namespace="accounts")),
    path("dashboard/", include("apps.dashboard.urls", namespace="dashboard")),
    path("stores/", include("apps.stores.urls", namespace="stores")),
    path("visits/", include("apps.visits.urls", namespace="visits")),
    path("checklists/", include("apps.checklists.urls", namespace="checklists")),
    path("actions/", include("apps.actions.urls", namespace="actions")),
    path("schedule/", include("apps.schedule.urls", namespace="schedule")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
