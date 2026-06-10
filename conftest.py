"""
Root-level pytest conftest.
Overrides settings that cause test failures in the test environment.
"""
import django
import pytest


@pytest.fixture(autouse=True)
def use_simple_static_storage(settings):
    """
    Override static files storage to avoid the 'Missing staticfiles manifest'
    error in tests. CompressedManifestStaticFilesStorage requires `collectstatic`
    to be run first, which is not appropriate for the test environment.
    """
    settings.STORAGES = {
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
    }
