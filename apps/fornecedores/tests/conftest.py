"""
Fixtures para os testes do app fornecedores.
"""
import pytest

from apps.accounts.models import UnidadeOrganizacional, User
from apps.fornecedores.models import Fornecedor
from apps.requisicoes.models import CategoriaCompra


@pytest.fixture
def test_unit(db):
    return UnidadeOrganizacional.objects.create(
        nome="Unidade Teste",
        descricao="Unidade para testes",
        ativo=True,
    )


@pytest.fixture
def comprador_user(db, test_unit):
    return User.objects.create_user(
        username="comprador",
        email="comprador@test.com",
        password="testpass123",
        role=User.Role.COMPRADOR,
        default_unit=test_unit,
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
def admin_user(db):
    return User.objects.create_user(
        username="admin",
        email="admin@test.com",
        password="testpass123",
        role=User.Role.ADMIN,
        is_superuser=True,
        is_staff=True,
    )


@pytest.fixture
def categoria(db):
    return CategoriaCompra.objects.create(nome="Informática", ativo=True)


@pytest.fixture
def fornecedor(db, categoria):
    return Fornecedor.objects.create(
        cnpj="11222333000181",
        razao_social="Empresa Teste Ltda",
        email="teste@empresa.com",
        categoria=categoria,
        ativo=True,
    )
