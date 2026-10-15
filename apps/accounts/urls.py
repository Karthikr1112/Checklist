from django.contrib.auth.views import LogoutView
from django.contrib.auth.views import LoginView
from django.urls import path

from . import views
from .forms import EmailAuthenticationForm

app_name = "accounts"

urlpatterns = [
    path(
        "login/",
        LoginView.as_view(
            template_name="registration/login.html",
            authentication_form=EmailAuthenticationForm,
        ),
        name="login",
    ),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("profile/", views.profile, name="profile"),
    path("pending-approval/", views.pending_approval, name="pending_approval"),
    path("users/", views.user_list, name="user_list"),
    path("users/new/", views.user_create, name="user_create"),
    path("users/<uuid:pk>/edit/", views.user_edit, name="user_edit"),
    path("users/<uuid:pk>/approve/", views.user_approve, name="user_approve"),
    path("users/<uuid:pk>/reject/", views.user_reject, name="user_reject"),
    path("audit-log/", views.audit_log, name="audit_log"),
]
