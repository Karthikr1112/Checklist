from django.urls import path

from . import views

app_name = "visits"

urlpatterns = [
    path("", views.visit_list, name="visit_list"),
    path("start/", views.visit_start, name="visit_start"),
    path("<uuid:pk>/", views.visit_detail, name="visit_detail"),
    path("<uuid:pk>/fill/", views.visit_fill, name="visit_fill"),
    path("<uuid:pk>/submit/", views.visit_submit, name="visit_submit"),
    path("<uuid:pk>/approve/", views.visit_approve, name="visit_approve"),
    path("response/<uuid:response_pk>/save/", views.response_save, name="response_save"),
    path("response/<uuid:response_pk>/photo/", views.response_photo_upload, name="response_photo_upload"),
]
