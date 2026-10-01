from django.apps import AppConfig


class ScheduleConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.schedule"
    label = "schedule"

    def ready(self):
        from . import signals  # noqa: F401
