"""
Production settings for ComprasNexos.
"""
import json

from decouple import config

from .base import *  # noqa: F401, F403

DEBUG = False

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    cast=lambda v: [s.strip() for s in v.split(",")],
)

CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    cast=lambda v: [s.strip() for s in v.split(",")],
)

ANYMAIL = {
    "AMAZON_SES_CLIENT_PARAMS": config(
        "ANYMAIL_AMAZON_SES_CLIENT_PARAMS",
        default="{}",
        cast=json.loads,
    )
}
EMAIL_BACKEND = "anymail.backends.amazon_ses.EmailBackend"

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
