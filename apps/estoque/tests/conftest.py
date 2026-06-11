"""
Fixtures para os testes do app estoque.
"""
import pytest

from apps.accounts.models import UnidadeOrganizacional, User
from apps.estoque.models import ItemEstoque, UnidadeMedida


@pytest.fixture
def test_unit(db):
    return UnidadeOrganizacional.objects.create(
        nome="Unidade A",
        descricao="Unidade para testes",
        ativo=True,
    )


@pytest.fixture
def outra_unit(db):
    return UnidadeOrganizacional.objects.create(
        nome="Unidade B",
        descricao="Segunda unidade para testes",
        ativo=True,
    )


@pytest.fixture
def solicitante_user(db, test_unit):
    return User.objects.create_user(
        username="solicitante_est",
        email="solicitante_est@test.com",
        password="testpass123",
        role=User.Role.SOLICITANTE,
        default_unit=test_unit,
    )


@pytest.fixture
def comprador_user(db):
    return User.objects.create_user(
        username="comprador_est",
        email="comprador_est@test.com",
        password="testpass123",
        role=User.Role.COMPRADOR,
        default_unit=None,
    )


@pytest.fixture
def unidade_medida(db):
    # sigla distinta para não conflitar com seed migration
    return UnidadeMedida.objects.create(nome="Unidade Teste", sigla="UN_TEST")


@pytest.fixture
def item_estoque(db, test_unit, unidade_medida):
    return ItemEstoque.objects.create(
        nome="Papel A4",
        quantidade_atual=50,
        quantidade_minima=10,
        unidade_organizacional=test_unit,
        unidade_medida=unidade_medida,
    )


@pytest.fixture
def item_abaixo_minimo(db, test_unit, unidade_medida):
    return ItemEstoque.objects.create(
        nome="Caneta",
        quantidade_atual=2,
        quantidade_minima=20,
        unidade_organizacional=test_unit,
        unidade_medida=unidade_medida,
    )
