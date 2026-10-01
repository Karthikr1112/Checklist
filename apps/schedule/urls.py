from django.urls import path

from . import views

app_name = "schedule"

urlpatterns = [
    path("", views.calendar_view, name="calendar"),
    path("new/", views.plan_create, name="plan_create"),
    path("<uuid:pk>/", views.plan_detail, name="plan_detail"),
    path("<uuid:pk>/edit/", views.plan_edit, name="plan_edit"),
    path("<uuid:pk>/delete/", views.plan_delete, name="plan_delete"),
    path("<uuid:pk>/start-visit/", views.plan_start_visit, name="plan_start_visit"),

    path("api/events/", views.api_events, name="api_events"),
    path("api/events/<uuid:pk>/reschedule/", views.api_event_reschedule, name="api_event_reschedule"),
]
