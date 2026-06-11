"""
Fixtures para os testes do app cotacoes.
Replica as fixtures de apps/fornecedores/tests/conftest.py e adiciona
fixtures especificas da Fase 4 (rfq, cotacao_fornecedor, requisicao_aprovada).
"""
from decimal import Decimal

import pytest

from apps.accounts.models import UnidadeOrganizacional, User
from apps.fornecedores.models import Fornecedor
from apps.requisicoes.models import CategoriaCompra, Requisicao


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


@pytest.fixture
def requisicao_aprovada(db, test_unit, categoria, comprador_user):
    """Cria uma Requisicao com status=APROVADO para uso nos testes de RFQ."""
    return Requisicao.objects.create(
        descricao="Compra de notebooks",
        status=Requisicao.Status.APROVADO,
        valor_estimado=Decimal("5000.00"),
        justificativa="teste",
        categoria=categoria,
        unidade=test_unit,
        criado_por=comprador_user,
    )


@pytest.fixture
def rfq(db, requisicao_aprovada, comprador_user):
    """Cria um RFQ vinculado a uma requisicao aprovada."""
    from apps.cotacoes.models import RFQ
    return RFQ.objects.create(
        requisicao=requisicao_aprovada,
        criado_por=comprador_user,
    )


@pytest.fixture
def cotacao_fornecedor(db, rfq, fornecedor):
    """Cria uma CotacaoFornecedor para o RFQ de teste."""
    from apps.cotacoes.models import CotacaoFornecedor
    return CotacaoFornecedor.objects.create(
        rfq=rfq,
        fornecedor=fornecedor,
        preco_unitario=Decimal("100.00"),
        prazo_entrega="30 dias",
        condicoes_pagamento="a vista",
    )
