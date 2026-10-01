from django.urls import path

from . import views

app_name = "actions"

urlpatterns = [
    path("", views.all_actions, name="all_actions"),
    path("mine/", views.my_actions, name="my_actions"),
    path("response/<uuid:response_pk>/new/", views.action_create, name="action_create"),
    path("<uuid:pk>/close/", views.action_close, name="action_close"),
]
