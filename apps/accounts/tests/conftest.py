"""
Shared pytest fixtures for accounts app tests.
"""
import pytest
from apps.accounts.models import UnidadeOrganizacional, User


@pytest.fixture
def test_unit(db):
    return UnidadeOrganizacional.objects.create(
        nome="Unidade Teste",
        descricao="Unidade para testes",
        ativo=True,
    )


@pytest.fixture
def admin_user(db, test_unit):
    return User.objects.create_user(
        username="admintest",
        email="admin@test.com",
        password="testpass123",
        role=User.Role.ADMIN,
        default_unit=test_unit,
        is_staff=True,
        is_superuser=True,
    )


@pytest.fixture
def solicitante_user(db, test_unit):
    return User.objects.create_user(
        username="solicitante",
        email="solicitante@test.com",
        password="testpass123",
        role=User.Role.SOLICITANTE,
        default_unit=test_unit,
    )


@pytest.fixture
def gestor_user(db, test_unit):
    return User.objects.create_user(
        username="gestor",
        email="gestor@test.com",
        password="testpass123",
        role=User.Role.GESTOR,
        default_unit=test_unit,
    )
