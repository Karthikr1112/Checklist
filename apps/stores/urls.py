from django.urls import path

from . import views

app_name = "stores"

urlpatterns = [
    path("", views.store_list, name="store_list"),
    path("new/", views.store_create, name="store_create"),
    path("<uuid:pk>/edit/", views.store_update, name="store_update"),
]
