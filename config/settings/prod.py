from .base import *  # noqa

DEBUG = True

# In production, default to MySQL unless USE_SQLITE is explicitly True
if not env.bool("USE_SQLITE", default=False):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": env("DB_NAME", default="checklist_db"),
            "USER": env("DB_USER", default="checklist_user"),
            "PASSWORD": env("DB_PASSWORD", default=""),
            "HOST": env("DB_HOST", default="127.0.0.1"),
            "PORT": env("DB_PORT", default="3306"),
            "OPTIONS": {
                "charset": "utf8mb4",
                "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }

SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"

# IMPORTANT: Tell Django it's served under /fin
FORCE_SCRIPT_NAME = "/cl"

# Cookie paths
SESSION_COOKIE_PATH = '/cl/'
CSRF_COOKIE_PATH = '/cl/'

# Unique cookie names
SESSION_COOKIE_NAME = 'cl_sessionid'
CSRF_COOKIE_NAME = 'cl_csrftoken'

CSRF_TRUSTED_ORIGINS = [
    "https://jeyarama.com",
    "https://www.jeyarama.com",
]
