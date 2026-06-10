"""
Integration tests for authentication flow.
Covers: AUTH-01 (login), AUTH-02 (password reset), AUTH-03 (session).
"""
import pytest
from django.core import mail
from django.test import override_settings
from django.urls import reverse

from apps.accounts.models import User


@pytest.mark.django_db
def test_login_success(client, admin_user):
    response = client.post(
        reverse("accounts:login"),
        {"username": "admin@test.com", "password": "testpass123"},
        follow=False,
    )
    assert response.status_code == 302
    assert response["Location"] == "/"


@pytest.mark.django_db
def test_login_wrong_password(client, admin_user):
    response = client.post(
        reverse("accounts:login"),
        {"username": "admin@test.com", "password": "wrongpassword"},
        follow=True,
    )
    assert response.status_code == 200
    assert "E-mail ou senha incorretos" in response.content.decode("utf-8")


@pytest.mark.django_db
def test_login_inactive_user(client, db):
    user = User.objects.create_user(
        username="inactive",
        email="inactive@test.com",
        password="pass123",
        is_active=False,
    )
    response = client.post(
        reverse("accounts:login"),
        {"username": "inactive@test.com", "password": "pass123"},
        follow=True,
    )
    assert response.status_code == 200
    assert "Esta conta está inativa" in response.content.decode("utf-8")


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_password_reset_sends_email(client, admin_user):
    response = client.post(
        reverse("accounts:password-reset"),
        {"email": "admin@test.com"},
    )
    assert response.status_code == 302
    assert len(mail.outbox) == 1
    assert "admin@test.com" in mail.outbox[0].to


@pytest.mark.django_db
def test_session_persists(client, admin_user):
    client.login(username="admin@test.com", password="testpass123")
    response = client.get("/")
    assert response.status_code == 200
