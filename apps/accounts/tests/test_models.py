"""
Unit tests for accounts models.
Covers: AUTH-05 (5 Groups), AUTH-06 (default_unit FK), UNIT-03 (default_unit availability).
"""
import pytest
from django.contrib.auth.models import Group

from apps.accounts.models import UnidadeOrganizacional, User


@pytest.mark.django_db
def test_groups_exist():
    expected = {"Solicitante", "Gestor", "Comprador", "Diretor", "Admin"}
    actual = set(Group.objects.values_list("name", flat=True))
    assert expected.issubset(actual), f"Missing groups: {expected - actual}"


@pytest.mark.django_db
def test_user_default_unit():
    unit = UnidadeOrganizacional.objects.create(nome="TI", ativo=True)
    user = User.objects.create_user(
        username="u1", email="u1@test.com", password="pass", default_unit=unit
    )
    user.refresh_from_db()
    assert user.default_unit_id == unit.pk
    assert user.default_unit.nome == "TI"


@pytest.mark.django_db
def test_user_role_choices():
    roles = [c[0] for c in User.Role.choices]
    assert set(roles) == {"solicitante", "gestor", "comprador", "diretor", "admin"}


@pytest.mark.django_db
def test_default_unit_nullable():
    user = User.objects.create_user(
        username="u2", email="u2@test.com", password="pass"
    )
    assert user.default_unit is None


@pytest.mark.django_db
def test_user_email_is_username_field():
    assert User.USERNAME_FIELD == "email"


@pytest.mark.django_db
def test_unidade_str():
    unit = UnidadeOrganizacional.objects.create(nome="Financeiro", ativo=True)
    assert str(unit) == "Financeiro"
