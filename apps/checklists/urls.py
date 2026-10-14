from django.urls import path

from . import views

app_name = "checklists"

urlpatterns = [
    path("", views.template_list, name="template_list"),
    path("<uuid:pk>/", views.template_detail, name="template_detail"),
    path("<uuid:template_pk>/sections/add/", views.section_create, name="section_create"),
    path("sections/<uuid:pk>/delete/", views.section_delete, name="section_delete"),
    path("<uuid:template_pk>/questions/add/", views.question_create, name="question_create"),
    path("questions/<uuid:pk>/edit/", views.question_update, name="question_update"),
    path("questions/<uuid:pk>/delete/", views.question_delete, name="question_delete"),
]
