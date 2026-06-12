"""
Testes para DashboardView enriquecida com KPIs reais (T-05-01, T-05-02, T-05-05, REL-01, D-09).

Estes testes devem passar GREEN apos a Task 3 enriquecer DashboardView.get_context_data().
As chaves de KPI usadas sao as canonicas: req_abertas, cotacoes_andamento, gasto_mes, fornecedores_ativos.
NAO usar 'requisicoes_abertas' nem 'cotacoes_em_andamento' (nomes obsoletos do RESEARCH.md Pattern 1).
"""
from decimal import Decimal

import pytest

from apps.accounts.models import UnidadeOrganizacional, User
from apps.requisicoes.models import CategoriaCompra, Requisicao


@pytest.fixture
def test_unit(db):
    return UnidadeOrganizacional.objects.create(
        nome="Unidade Dashboard Teste",
        descricao="Para testes do dashboard",
        ativo=True,
    )


@pytest.fixture
def comprador_user(db, test_unit):
    return User.objects.create_user(
        username="comprador_dash",
        email="comprador_dash@test.com",
        password="testpass123",
        role=User.Role.COMPRADOR,
        default_unit=test_unit,
    )


@pytest.fixture
def solicitante_user(db, test_unit):
    return User.objects.create_user(
        username="solicitante_dash",
        email="solicitante_dash@test.com",
        password="testpass123",
        role=User.Role.SOLICITANTE,
        default_unit=test_unit,
    )


@pytest.fixture
def categoria(db):
    return CategoriaCompra.objects.create(nome="TI Dashboard", ativo=True)


class TestDashboardViewKpis:
    """
    Testes para DashboardView.get_context_data() injetando KPIs reais (T-05-01, T-05-02).

    Verifica que o template recebe o dict 'kpis' com as 4 chaves canonicas.
    """

    def test_kpis_presentes_no_contexto(self, client, comprador_user):
        """
        DashboardView deve injetar 'kpis' no contexto com as 4 chaves canonicas (T-05-01).
        """
        client.force_login(comprador_user)
        response = client.get("/")
        assert response.status_code == 200
        assert "kpis" in response.context, "Chave 'kpis' deve estar no contexto do template"

        kpis = response.context["kpis"]
        assert "req_abertas" in kpis, "Chave 'req_abertas' deve estar em kpis (contrato T-05-01)"
        assert "cotacoes_andamento" in kpis, "Chave 'cotacoes_andamento' deve estar em kpis"
        assert "gasto_mes" in kpis, "Chave 'gasto_mes' deve estar em kpis"
        assert "fornecedores_ativos" in kpis, "Chave 'fornecedores_ativos' deve estar em kpis"

    def test_req_abertas_conta_pendente_gestor_e_diretor(
        self, client, comprador_user, test_unit, categoria
    ):
        """
        req_abertas deve contar apenas PENDENTE_GESTOR + PENDENTE_DIRETOR (T-05-02).
        RASCUNHO nao deve ser incluido.
        """
        # Criar 1 PENDENTE_GESTOR
        Requisicao.objects.create(
            descricao="Req 1",
            status=Requisicao.Status.PENDENTE_GESTOR,
            valor_estimado=Decimal("1000.00"),
            justificativa="teste",
            categoria=categoria,
            unidade=test_unit,
            criado_por=comprador_user,
        )
        # Criar 1 PENDENTE_DIRETOR
        Requisicao.objects.create(
            descricao="Req 2",
            status=Requisicao.Status.PENDENTE_DIRETOR,
            valor_estimado=Decimal("2000.00"),
            justificativa="teste",
            categoria=categoria,
            unidade=test_unit,
            criado_por=comprador_user,
        )
        # Criar 1 RASCUNHO — nao deve ser contado
        Requisicao.objects.create(
            descricao="Req rascunho",
            status=Requisicao.Status.RASCUNHO,
            valor_estimado=Decimal("500.00"),
            justificativa="teste",
            categoria=categoria,
            unidade=test_unit,
            criado_por=comprador_user,
        )

        client.force_login(comprador_user)
        response = client.get("/")
        kpis = response.context["kpis"]
        assert kpis["req_abertas"] == 2, (
            f"req_abertas deve ser 2 (PENDENTE_GESTOR + PENDENTE_DIRETOR), obtido {kpis['req_abertas']}"
        )

    def test_kpis_nao_usam_nomes_obsoletos(self, client, comprador_user):
        """
        Garantia negativa: kpis NAO deve ter as chaves obsoletas do RESEARCH.md (T-05-01).
        """
        client.force_login(comprador_user)
        response = client.get("/")
        kpis = response.context["kpis"]
        assert "requisicoes_abertas" not in kpis, (
            "Chave 'requisicoes_abertas' e obsoleta — usar 'req_abertas'"
        )
        assert "cotacoes_em_andamento" not in kpis, (
            "Chave 'cotacoes_em_andamento' e obsoleta — usar 'cotacoes_andamento'"
        )

    def test_solicitante_ve_kpis_filtrados_por_unidade(
        self, client, solicitante_user, comprador_user, test_unit, categoria
    ):
        """
        Solicitante deve ver apenas KPIs da sua unidade (T-05-05, D-02).
        """
        outra_unidade = UnidadeOrganizacional.objects.create(
            nome="Outra Unidade Dash", descricao="outra", ativo=True
        )

        # Req na unidade do solicitante
        Requisicao.objects.create(
            descricao="Req minha unidade",
            status=Requisicao.Status.PENDENTE_GESTOR,
            valor_estimado=Decimal("1000.00"),
            justificativa="teste",
            categoria=categoria,
            unidade=test_unit,
            criado_por=solicitante_user,
        )
        # Req em outra unidade — NAO deve aparecer
        Requisicao.objects.create(
            descricao="Req outra unidade",
            status=Requisicao.Status.PENDENTE_GESTOR,
            valor_estimado=Decimal("2000.00"),
            justificativa="teste",
            categoria=categoria,
            unidade=outra_unidade,
            criado_por=comprador_user,
        )

        client.force_login(solicitante_user)
        response = client.get("/")
        kpis = response.context["kpis"]
        assert kpis["req_abertas"] == 1, (
            f"Solicitante deve ver 1 req (sua unidade), obtido {kpis['req_abertas']}"
        )

    def test_gasto_mes_e_decimal(self, client, comprador_user):
        """
        gasto_mes deve ser do tipo Decimal (nao int, nao float).
        """
        client.force_login(comprador_user)
        response = client.get("/")
        kpis = response.context["kpis"]
        assert isinstance(kpis["gasto_mes"], Decimal), (
            f"gasto_mes deve ser Decimal, obtido {type(kpis['gasto_mes'])}"
        )
