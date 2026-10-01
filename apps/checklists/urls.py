from django.urls import path

from . import views

app_name = "checklists"

urlpatterns = [
    path("", views.template_list, name="template_list"),
    path("<uuid:pk>/", views.template_detail, name="template_detail"),
]
