"""
Development settings for ComprasNexos.
"""
from .base import *  # noqa: F401, F403

DEBUG = True

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405

MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]  # noqa: F405

INTERNAL_IPS = ["127.0.0.1"]

# Use simple static files storage in dev — no manifest required.
# Base settings use CompressedManifestStaticFilesStorage (production-only).
# This avoids "Missing staticfiles manifest entry" errors during tests.
STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
}
