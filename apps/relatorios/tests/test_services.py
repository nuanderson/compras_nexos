"""
Testes de service layer para apps/relatorios (T-05-01 a T-05-05, REL-01, REL-02, REL-03, UNIT-04).

Estes testes devem passar GREEN pois services.py esta implementado (Task 2).
As chaves de KPI usadas sao as canonicas: req_abertas, cotacoes_andamento, gasto_mes, fornecedores_ativos.
Nao usar 'requisicoes_abertas' nem 'cotacoes_em_andamento' (nomes obsoletos do RESEARCH.md Pattern 1).
"""
from datetime import date
from decimal import Decimal

import pytest

from apps.relatorios import services
from apps.requisicoes.models import CategoriaCompra, Requisicao


class TestDashboardKpis:
    """
    Testes para get_dashboard_kpis (REL-01, T-05-01..05).

    As asserções usam as chaves canonicas: req_abertas, cotacoes_andamento, gasto_mes, fornecedores_ativos.
    """

    def test_gasto_mes_soma_vencedores_mes_corrente(self, db, rfq_com_vencedor, comprador_user):
        """
        gasto_mes deve somar preco_unitario dos vencedores do mes+ano corrente (T-05-03).
        rfq_com_vencedor tem preco_unitario=1500.00 e atualizado_em = agora (mes corrente).
        """
        kpis = services.get_dashboard_kpis(comprador_user)
        assert kpis["gasto_mes"] == Decimal("1500.00"), (
            f"Esperado Decimal('1500.00'), obtido {kpis['gasto_mes']}"
        )

    def test_gasto_mes_zero_sem_vencedores(self, db, comprador_user):
        """
        gasto_mes deve retornar Decimal('0') quando nao ha vencedores no mes corrente (Pitfall 1).
        Sum() retorna None em queryset vazio; o fallback Decimal('0') deve ser aplicado.
        """
        kpis = services.get_dashboard_kpis(comprador_user)
        assert kpis["gasto_mes"] == Decimal("0"), (
            f"Esperado Decimal('0'), obtido {kpis['gasto_mes']}"
        )

    def test_retorna_chaves_canonicas(self, db, comprador_user):
        """
        get_dashboard_kpis deve retornar dict com exatamente as 4 chaves canonicas (T-05-01).
        """
        kpis = services.get_dashboard_kpis(comprador_user)
        assert "req_abertas" in kpis
        assert "cotacoes_andamento" in kpis
        assert "gasto_mes" in kpis
        assert "fornecedores_ativos" in kpis
        # Garantia negativa: nomes obsoletos do RESEARCH.md NAO devem estar presentes
        assert "requisicoes_abertas" not in kpis
        assert "cotacoes_em_andamento" not in kpis

    def test_req_abertas_conta_apenas_pendente_gestor_e_diretor(
        self, db, comprador_user, test_unit, categoria
    ):
        """
        req_abertas deve contar PENDENTE_GESTOR e PENDENTE_DIRETOR (T-05-02).
        RASCUNHO, APROVADO, REPROVADO, CANCELADO nao devem ser contados.
        """
        # Criar uma requisicao PENDENTE_GESTOR
        Requisicao.objects.create(
            descricao="Req pendente gestor",
            status=Requisicao.Status.PENDENTE_GESTOR,
            valor_estimado=Decimal("1000.00"),
            justificativa="teste",
            categoria=categoria,
            unidade=test_unit,
            criado_por=comprador_user,
        )
        # Criar uma requisicao PENDENTE_DIRETOR
        Requisicao.objects.create(
            descricao="Req pendente diretor",
            status=Requisicao.Status.PENDENTE_DIRETOR,
            valor_estimado=Decimal("2000.00"),
            justificativa="teste",
            categoria=categoria,
            unidade=test_unit,
            criado_por=comprador_user,
        )
        # Criar uma RASCUNHO — nao deve ser contada
        Requisicao.objects.create(
            descricao="Req rascunho",
            status=Requisicao.Status.RASCUNHO,
            valor_estimado=Decimal("500.00"),
            justificativa="teste",
            categoria=categoria,
            unidade=test_unit,
            criado_por=comprador_user,
        )

        kpis = services.get_dashboard_kpis(comprador_user)
        assert kpis["req_abertas"] == 2, (
            f"Esperado 2 (PENDENTE_GESTOR + PENDENTE_DIRETOR), obtido {kpis['req_abertas']}"
        )

    def test_solicitante_filtrado_por_unidade(
        self, db, solicitante_user, comprador_user, test_unit, categoria
    ):
        """
        Solicitante deve ver apenas requisicoes da sua unidade (T-05-05, D-02).
        req_abertas para solicitante filtra por user.default_unit.
        """
        from apps.accounts.models import UnidadeOrganizacional

        # Cria outra unidade (fora da unidade do solicitante)
        outra_unidade = UnidadeOrganizacional.objects.create(
            nome="Outra Unidade", descricao="Outra", ativo=True
        )

        # Requisicao na unidade do solicitante (test_unit)
        Requisicao.objects.create(
            descricao="Req na minha unidade",
            status=Requisicao.Status.PENDENTE_GESTOR,
            valor_estimado=Decimal("1000.00"),
            justificativa="teste",
            categoria=categoria,
            unidade=test_unit,
            criado_por=solicitante_user,
        )
        # Requisicao em outra unidade — NAO deve aparecer para o solicitante
        Requisicao.objects.create(
            descricao="Req em outra unidade",
            status=Requisicao.Status.PENDENTE_GESTOR,
            valor_estimado=Decimal("2000.00"),
            justificativa="teste",
            categoria=categoria,
            unidade=outra_unidade,
            criado_por=comprador_user,
        )

        kpis_solicitante = services.get_dashboard_kpis(solicitante_user)
        assert kpis_solicitante["req_abertas"] == 1, (
            f"Solicitante deve ver apenas 1 requisicao (sua unidade), obtido {kpis_solicitante['req_abertas']}"
        )

    def test_comprador_ve_global(
        self, db, comprador_user, solicitante_user, test_unit, categoria
    ):
        """
        Comprador deve ver requisicoes de todas as unidades (T-05-04, D-02).
        """
        from apps.accounts.models import UnidadeOrganizacional

        outra_unidade = UnidadeOrganizacional.objects.create(
            nome="Unidade B", descricao="B", ativo=True
        )
        # 2 requisicoes em unidades diferentes
        Requisicao.objects.create(
            descricao="Req unidade A",
            status=Requisicao.Status.PENDENTE_GESTOR,
            valor_estimado=Decimal("1000.00"),
            justificativa="teste",
            categoria=categoria,
            unidade=test_unit,
            criado_por=comprador_user,
        )
        Requisicao.objects.create(
            descricao="Req unidade B",
            status=Requisicao.Status.PENDENTE_GESTOR,
            valor_estimado=Decimal("2000.00"),
            justificativa="teste",
            categoria=categoria,
            unidade=outra_unidade,
            criado_por=comprador_user,
        )

        kpis = services.get_dashboard_kpis(comprador_user)
        assert kpis["req_abertas"] == 2, (
            f"Comprador deve ver 2 requisicoes (global), obtido {kpis['req_abertas']}"
        )


class TestGastos:
    """Testes para get_gastos_por_categoria (REL-02)."""

    def test_retorna_total_por_categoria(self, db, rfq_com_vencedor):
        """
        get_gastos_por_categoria deve retornar lista de dicts com categoria_nome e total.
        """
        hoje = date.today()
        data_inicio = hoje.replace(day=1)
        data_fim = hoje

        resultado = services.get_gastos_por_categoria(data_inicio, data_fim)

        assert isinstance(resultado, list)
        assert len(resultado) >= 1

        # Deve haver uma entrada para "Informatica" (categoria da requisicao_aprovada)
        categorias = [r["categoria_nome"] for r in resultado]
        assert "Informatica" in categorias

        # Verificar total
        item_info = next(r for r in resultado if r["categoria_nome"] == "Informatica")
        assert item_info["total"] == Decimal("1500.00")

    def test_retorna_lista_vazia_sem_vencedores(self, db):
        """Sem vencedores, get_gastos_por_categoria deve retornar lista vazia."""
        hoje = date.today()
        resultado = services.get_gastos_por_categoria(hoje.replace(day=1), hoje)
        assert resultado == []

    def test_filtra_por_unidade(self, db, rfq_com_vencedor, test_unit):
        """Filtro por unidade deve retornar apenas gastos dessa unidade."""
        from apps.accounts.models import UnidadeOrganizacional

        outra_unidade = UnidadeOrganizacional.objects.create(
            nome="Unidade Outro", descricao="outro", ativo=True
        )
        hoje = date.today()

        # Filtrar pela unidade do rfq_com_vencedor — deve encontrar resultado
        resultado_correto = services.get_gastos_por_categoria(
            hoje.replace(day=1), hoje, unidade_id=test_unit.pk
        )
        assert len(resultado_correto) >= 1

        # Filtrar por outra unidade — deve retornar lista vazia
        resultado_vazio = services.get_gastos_por_categoria(
            hoje.replace(day=1), hoje, unidade_id=outra_unidade.pk
        )
        assert resultado_vazio == []


class TestRequisicoesPainel:
    """Testes para get_requisicoes_painel (REL-03)."""

    def test_filtra_por_status(self, db, comprador_user, test_unit, categoria):
        """get_requisicoes_painel filtra por status quando fornecido."""
        Requisicao.objects.create(
            descricao="Req rascunho",
            status=Requisicao.Status.RASCUNHO,
            valor_estimado=Decimal("100.00"),
            justificativa="teste",
            categoria=categoria,
            unidade=test_unit,
            criado_por=comprador_user,
        )
        Requisicao.objects.create(
            descricao="Req pendente",
            status=Requisicao.Status.PENDENTE_GESTOR,
            valor_estimado=Decimal("200.00"),
            justificativa="teste",
            categoria=categoria,
            unidade=test_unit,
            criado_por=comprador_user,
        )

        qs = services.get_requisicoes_painel(status=Requisicao.Status.RASCUNHO)
        statuses = list(qs.values_list("status", flat=True))
        assert all(s == Requisicao.Status.RASCUNHO for s in statuses)
        assert len(statuses) == 1

    def test_filtra_por_unidade(self, db, comprador_user, test_unit, categoria):
        """get_requisicoes_painel filtra por unidade_id quando fornecido."""
        from apps.accounts.models import UnidadeOrganizacional

        outra_unidade = UnidadeOrganizacional.objects.create(
            nome="Unidade Filtro", descricao="filtro", ativo=True
        )
        Requisicao.objects.create(
            descricao="Req test_unit",
            status=Requisicao.Status.RASCUNHO,
            valor_estimado=Decimal("100.00"),
            justificativa="teste",
            categoria=categoria,
            unidade=test_unit,
            criado_por=comprador_user,
        )
        Requisicao.objects.create(
            descricao="Req outra unidade",
            status=Requisicao.Status.RASCUNHO,
            valor_estimado=Decimal("200.00"),
            justificativa="teste",
            categoria=categoria,
            unidade=outra_unidade,
            criado_por=comprador_user,
        )

        qs = services.get_requisicoes_painel(unidade_id=test_unit.pk)
        unidades = list(qs.values_list("unidade_id", flat=True))
        assert all(u == test_unit.pk for u in unidades)
        assert len(unidades) == 1

    def test_retorna_todas_sem_filtros(self, db, comprador_user, test_unit, categoria):
        """Sem filtros, get_requisicoes_painel retorna todas as requisicoes."""
        Requisicao.objects.create(
            descricao="Req 1",
            status=Requisicao.Status.RASCUNHO,
            valor_estimado=Decimal("100.00"),
            justificativa="teste",
            categoria=categoria,
            unidade=test_unit,
            criado_por=comprador_user,
        )
        Requisicao.objects.create(
            descricao="Req 2",
            status=Requisicao.Status.APROVADO,
            valor_estimado=Decimal("200.00"),
            justificativa="teste",
            categoria=categoria,
            unidade=test_unit,
            criado_por=comprador_user,
        )

        qs = services.get_requisicoes_painel()
        assert qs.count() == 2


class TestFiltroUnidade:
    """Testes de filtro de unidade no KPI de gasto_mes (UNIT-04, T-05-05)."""

    def test_filtro_unidade_altera_resultado(
        self, db, rfq_com_vencedor, comprador_user, test_unit, categoria
    ):
        """
        Filtro de unidade deve alterar o resultado do gasto_mes.
        solicitante_user com default_unit=test_unit deve ver o gasto de 1500.
        Solicitante de outra unidade deve ver gasto=0.
        """
        from apps.accounts.models import UnidadeOrganizacional

        outra_unidade = UnidadeOrganizacional.objects.create(
            nome="Unidade Isolada", descricao="isolada", ativo=True
        )

        # Solicitante na unidade do rfq_com_vencedor (test_unit) — ve o gasto
        from apps.accounts.models import User
        solicitante_test_unit = User.objects.create_user(
            username="sol_tu",
            email="sol_tu@test.com",
            password="testpass123",
            role=User.Role.SOLICITANTE,
            default_unit=test_unit,
        )

        # Solicitante em outra unidade — NAO ve o gasto
        solicitante_outra = User.objects.create_user(
            username="sol_outra",
            email="sol_outra@test.com",
            password="testpass123",
            role=User.Role.SOLICITANTE,
            default_unit=outra_unidade,
        )

        kpis_tu = services.get_dashboard_kpis(solicitante_test_unit)
        kpis_outra = services.get_dashboard_kpis(solicitante_outra)

        assert kpis_tu["gasto_mes"] == Decimal("1500.00"), (
            f"Solicitante da test_unit deve ver 1500, obtido {kpis_tu['gasto_mes']}"
        )
        assert kpis_outra["gasto_mes"] == Decimal("0"), (
            f"Solicitante de outra unidade deve ver 0, obtido {kpis_outra['gasto_mes']}"
        )
