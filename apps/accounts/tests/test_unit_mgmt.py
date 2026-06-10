"""
Tests for unit management views — UNIT-01 (create unit), UNIT-02 (assign unit to user).
"""
import pytest
from django.urls import reverse

from apps.accounts.models import UnidadeOrganizacional, User


@pytest.mark.django_db
def test_admin_can_access_unit_list(client, admin_user):
    client.force_login(admin_user)
    response = client.get(reverse("accounts:unit-list"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_admin_create_unit(client, admin_user):
    client.force_login(admin_user)
    response = client.post(
        reverse("accounts:unit-create"),
        {"nome": "Nova Unidade", "descricao": "Desc teste", "ativo": True},
    )
    assert response.status_code == 302
    assert UnidadeOrganizacional.objects.filter(nome="Nova Unidade").exists()


@pytest.mark.django_db
def test_admin_assign_unit_to_user(client, admin_user, solicitante_user, test_unit):
    client.force_login(admin_user)
    new_unit = UnidadeOrganizacional.objects.create(nome="Nova Unidade Atrib", ativo=True)
    post_data = {
        "email": solicitante_user.email,
        "username": solicitante_user.username,
        "role": solicitante_user.role,
        "default_unit": new_unit.pk,
        "is_active": True,
    }
    response = client.post(
        reverse("accounts:user-edit", args=[solicitante_user.pk]), post_data
    )
    assert response.status_code == 302
    solicitante_user.refresh_from_db()
    assert solicitante_user.default_unit_id == new_unit.pk


@pytest.mark.django_db
def test_unit_deactivate(client, admin_user, test_unit):
    client.force_login(admin_user)
    response = client.post(
        reverse("accounts:unit-deactivate", args=[test_unit.pk])
    )
    assert response.status_code == 200  # Returns partial HTML
    test_unit.refresh_from_db()
    assert test_unit.ativo is False
