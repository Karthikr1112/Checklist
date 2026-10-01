from .base import *  # noqa

DEBUG = True
INTERNAL_IPS = ["127.0.0.1"]

# Storage in dev: keep static simple, no manifest needed
STORAGES["staticfiles"]["BACKEND"] = "django.contrib.staticfiles.storage.StaticFilesStorage"  # noqa: F405

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
