"""
Tests for user management views — AUTH-04 (create/deactivate user),
AUTH-05 (role assignment), AUTH-06 (unit assignment).
"""
import pytest
from django.urls import reverse

from apps.accounts.models import UnidadeOrganizacional, User


@pytest.mark.django_db
def test_admin_can_access_user_list(client, admin_user):
    client.force_login(admin_user)
    response = client.get(reverse("accounts:user-list"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_non_admin_blocked_from_user_list(client, solicitante_user):
    client.force_login(solicitante_user)
    response = client.get(reverse("accounts:user-list"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_create_user(client, admin_user, test_unit):
    client.force_login(admin_user)
    post_data = {
        "email": "new@test.com",
        "username": "newuser",
        "first_name": "New",
        "last_name": "User",
        "role": "solicitante",
        "default_unit": test_unit.pk,
        "password1": "securepass123!",
        "password2": "securepass123!",
    }
    response = client.post(reverse("accounts:user-create"), post_data)
    assert response.status_code == 302
    assert User.objects.filter(email="new@test.com").exists()


@pytest.mark.django_db
def test_admin_deactivate_user(client, admin_user, solicitante_user):
    client.force_login(admin_user)
    response = client.post(
        reverse("accounts:user-deactivate", args=[solicitante_user.pk])
    )
    assert response.status_code == 200  # Returns partial HTML
    solicitante_user.refresh_from_db()
    assert solicitante_user.is_active is False


@pytest.mark.django_db
def test_deactivate_confirm_renders(client, admin_user, solicitante_user):
    client.force_login(admin_user)
    response = client.get(
        reverse("accounts:user-deactivate-confirm", args=[solicitante_user.pk])
    )
    assert response.status_code == 200
    assert "Confirmar desativação" in response.content.decode("utf-8")
