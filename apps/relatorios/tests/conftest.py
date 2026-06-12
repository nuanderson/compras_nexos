"""
Fixtures para os testes do app relatorios.
Replica as fixtures de apps/cotacoes/tests/conftest.py e adiciona
fixtures especificas da Fase 5 (rfq_com_vencedor, diretor_user).
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
def diretor_user(db, test_unit):
    """Usuario com role=DIRETOR para testes de acesso a relatorios."""
    return User.objects.create_user(
        username="diretor",
        email="diretor@test.com",
        password="testpass123",
        role=User.Role.DIRETOR,
        default_unit=test_unit,
    )


@pytest.fixture
def categoria(db):
    return CategoriaCompra.objects.create(nome="Informatica", ativo=True)


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
def rfq_com_vencedor(db, requisicao_aprovada, comprador_user, fornecedor):
    """
    RFQ com vencedor definido — usado para testar o KPI 'Gasto do Mes'.

    Cria um RFQ, adiciona uma CotacaoFornecedor com preco_unitario=R$1500,
    e define esta cotacao como vencedora do RFQ.
    Retorna o rfq com vencedor salvo.
    """
    from apps.cotacoes.models import CotacaoFornecedor, RFQ

    rfq = RFQ.objects.create(
        requisicao=requisicao_aprovada,
        criado_por=comprador_user,
    )
    cotacao = CotacaoFornecedor.objects.create(
        rfq=rfq,
        fornecedor=fornecedor,
        preco_unitario=Decimal("1500.00"),
        prazo_entrega="15 dias",
        condicoes_pagamento="30 dias",
    )
    rfq.vencedor = cotacao
    rfq.justificativa_selecao = "Menor preco"
    rfq.save(update_fields=["vencedor", "justificativa_selecao", "atualizado_em"])
    return rfq
