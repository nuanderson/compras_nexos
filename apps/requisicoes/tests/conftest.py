"""
Fixtures compartilhadas para os testes do app requisicoes.
"""
from decimal import Decimal

import pytest

from apps.accounts.models import UnidadeOrganizacional, User
from apps.aprovacoes.models import ConfiguracaoAlcada
from apps.requisicoes.models import CategoriaCompra, Requisicao


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
def outro_solicitante(db, test_unit):
    return User.objects.create_user(
        username="solicitante2",
        email="solicitante2@test.com",
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


@pytest.fixture
def categoria(db):
    return CategoriaCompra.objects.create(nome="Material de Escritório", ativo=True)


@pytest.fixture
def config_alcada(db):
    config, _ = ConfiguracaoAlcada.objects.get_or_create(pk=1)
    config.valor_maximo_gestor = Decimal("1000.00")
    config.save()
    return config


@pytest.fixture
def requisicao_rascunho(db, solicitante_user, categoria, test_unit):
    return Requisicao.objects.create(
        descricao="Papel A4 para escritório",
        categoria=categoria,
        valor_estimado=Decimal("500.00"),
        justificativa="Estoque zerado",
        unidade=test_unit,
        status=Requisicao.Status.RASCUNHO,
        criado_por=solicitante_user,
    )


@pytest.fixture
def requisicao_pendente_gestor(db, solicitante_user, categoria, test_unit):
    return Requisicao.objects.create(
        descricao="Canetas esferográficas",
        categoria=categoria,
        valor_estimado=Decimal("500.00"),
        justificativa="Reposição de estoque",
        unidade=test_unit,
        status=Requisicao.Status.PENDENTE_GESTOR,
        criado_por=solicitante_user,
    )


@pytest.fixture
def requisicao_pendente_diretor(db, solicitante_user, categoria, test_unit):
    return Requisicao.objects.create(
        descricao="Equipamento TI",
        categoria=categoria,
        valor_estimado=Decimal("5000.00"),
        justificativa="Renovação",
        unidade=test_unit,
        status=Requisicao.Status.PENDENTE_DIRETOR,
        criado_por=solicitante_user,
    )
