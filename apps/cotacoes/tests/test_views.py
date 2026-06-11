"""
Testes de views para apps/cotacoes.

TestNovaRFQView: COT-01 — conectada no plano 02 (GREEN).
TestAdicionarCotacaoView: COT-02 — conectada no plano 03.
TestRemoverCotacaoView: COT-02 — conectada no plano 03.
TestModalSelecionarVencedor: COT-04 — conectada no plano 03.
TestBloqueioPosSeletcao: COT-04 — conectada no plano 03.
"""
from decimal import Decimal

import pytest

from apps.cotacoes.models import CotacaoFornecedor, RFQ
from apps.requisicoes.models import Requisicao


class TestNovaRFQView:
    """
    Testes COT-01: criação de RFQ via /cotacoes/nova/.

    Cobre:
      T-04-01  403 para Solicitante
      T-04-02  IntegrityError → 409 (duplicata)
      D-06     queryset filtrado APROVADO + rfq__isnull=True
    """

    def test_acesso_negado_solicitante(self, client, solicitante_user):
        """Solicitante deve receber 403 ao tentar acessar /cotacoes/nova/."""
        client.force_login(solicitante_user)
        response = client.get("/cotacoes/nova/")
        assert response.status_code == 403

    def test_acesso_negado_solicitante_lista(self, client, solicitante_user):
        """Solicitante deve receber 403 ao tentar acessar /cotacoes/."""
        client.force_login(solicitante_user)
        response = client.get("/cotacoes/")
        assert response.status_code == 403

    def test_select_filtra_aprovadas_sem_rfq(
        self, client, comprador_user, requisicao_aprovada, rfq
    ):
        """
        Select de requisições deve exibir apenas APROVADO sem RFQ vinculado.

        - requisicao_aprovada já foi usada pelo rfq fixture → NÃO deve aparecer.
        - Nova requisição aprovada sem RFQ → DEVE aparecer.
        - Requisição não-aprovada → NÃO deve aparecer.
        """
        # Criar requisição aprovada sem RFQ (fixture requisicao_aprovada já tem rfq)
        req_livre = Requisicao.objects.create(
            descricao="Outra requisição aprovada",
            status=Requisicao.Status.APROVADO,
            valor_estimado=Decimal("1000.00"),
            justificativa="teste",
            categoria=requisicao_aprovada.categoria,
            unidade=requisicao_aprovada.unidade,
            criado_por=comprador_user,
        )
        # Criar requisição RASCUNHO — não deve aparecer
        req_rascunho = Requisicao.objects.create(
            descricao="Requisição rascunho",
            status=Requisicao.Status.RASCUNHO,
            valor_estimado=Decimal("500.00"),
            justificativa="teste",
            categoria=requisicao_aprovada.categoria,
            unidade=requisicao_aprovada.unidade,
            criado_por=comprador_user,
        )

        client.force_login(comprador_user)
        response = client.get("/cotacoes/nova/")
        assert response.status_code == 200

        qs = response.context["form"].fields["requisicao"].queryset
        # req_livre deve estar no queryset
        assert req_livre in qs
        # requisicao_aprovada (com RFQ vinculado) NÃO deve aparecer
        assert requisicao_aprovada not in qs
        # req_rascunho NÃO deve aparecer
        assert req_rascunho not in qs

    def test_cria_rfq_e_redireciona(self, client, comprador_user, db, test_unit, categoria):
        """POST com requisição livre → cria RFQ e redireciona para detalhe."""
        req = Requisicao.objects.create(
            descricao="Requisição para criar RFQ",
            status=Requisicao.Status.APROVADO,
            valor_estimado=Decimal("2000.00"),
            justificativa="teste",
            categoria=categoria,
            unidade=test_unit,
            criado_por=comprador_user,
        )
        client.force_login(comprador_user)
        response = client.post("/cotacoes/nova/", data={"requisicao": req.pk})
        assert response.status_code == 302
        # RFQ deve existir no banco
        assert RFQ.objects.filter(requisicao=req).exists()
        rfq = RFQ.objects.get(requisicao=req)
        assert response["Location"] == f"/cotacoes/{rfq.pk}/"

    def test_segundo_rfq_retorna_409(self, client, comprador_user, db, test_unit, categoria):
        """
        Captura de IntegrityError → 409, sem duplicata (T-04-02).

        Usa mock para simular a condição de corrida onde a requisição estava
        livre no form GET mas já foi cotada entre o GET e o POST (race condition).
        A view deve capturar IntegrityError e retornar 409, nunca 500.
        """
        from unittest.mock import patch
        from django.db import IntegrityError as DjangoIntegrityError

        # Criar requisição aprovada livre (passará na validação do form)
        req = Requisicao.objects.create(
            descricao="Requisição para teste 409",
            status=Requisicao.Status.APROVADO,
            valor_estimado=Decimal("3000.00"),
            justificativa="teste",
            categoria=categoria,
            unidade=test_unit,
            criado_por=comprador_user,
        )

        client.force_login(comprador_user)
        # Mockar services.criar_rfq para lançar IntegrityError (simula race condition)
        with patch(
            "apps.cotacoes.views.services.criar_rfq",
            side_effect=DjangoIntegrityError("duplicate key"),
        ):
            response = client.post(
                "/cotacoes/nova/",
                data={"requisicao": req.pk},
            )
        # View deve capturar e retornar 409, não 500
        assert response.status_code == 409
        # Nenhum RFQ real foi criado (mock impediu a criação)
        assert not RFQ.objects.filter(requisicao=req).exists()


class TestAdicionarCotacaoView:
    """
    Testes COT-02: adição de cotação de fornecedor via POST.

    Cobre:
      D-10    HX-Redirect após add mantém deltas consistentes (Pitfall 2)
      T-04-03 Guard rfq.tem_vencedor → 403
    """

    def test_adicionar_cotacao_retorna_redirect_htmx(
        self, client, comprador_user, rfq, fornecedor
    ):
        """POST para adicionar cotacao deve retornar HX-Redirect para detalhe do RFQ."""
        client.force_login(comprador_user)
        response = client.post(
            f"/cotacoes/{rfq.pk}/cotacoes/adicionar/",
            data={
                "fornecedor": fornecedor.pk,
                "preco_unitario": "200.00",
                "prazo_entrega": "15 dias",
                "condicoes_pagamento": "30 dias",
            },
            HTTP_HX_REQUEST="true",
        )
        # HX-Redirect deve estar presente no header
        assert "HX-Redirect" in response
        assert response.status_code == 200
        # Cotação deve existir no banco
        assert CotacaoFornecedor.objects.filter(rfq=rfq, fornecedor=fornecedor).exists()

    def test_adicionar_cotacao_bloqueia_apos_vencedor(
        self, client, comprador_user, rfq, cotacao_fornecedor, fornecedor
    ):
        """Após selecionar vencedor, adicionar cotação deve retornar 403 (T-04-03)."""
        rfq.vencedor = cotacao_fornecedor
        rfq.save()

        client.force_login(comprador_user)
        response = client.post(
            f"/cotacoes/{rfq.pk}/cotacoes/adicionar/",
            data={
                "fornecedor": fornecedor.pk,
                "preco_unitario": "300.00",
            },
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 403


class TestRemoverCotacaoView:
    """
    Testes COT-02: remoção de cotação via POST.

    Cobre:
      D-10    HX-Redirect após remove mantém deltas consistentes
      T-04-03 Guard rfq.tem_vencedor → 403
    """

    def test_remover_cotacao_retorna_redirect_htmx(
        self, client, comprador_user, rfq, cotacao_fornecedor
    ):
        """POST para remover cotacao deve retornar HX-Redirect para detalhe do RFQ."""
        client.force_login(comprador_user)
        response = client.post(
            f"/cotacoes/{rfq.pk}/cotacoes/{cotacao_fornecedor.pk}/remover/",
            HTTP_HX_REQUEST="true",
        )
        assert "HX-Redirect" in response
        assert response.status_code == 200
        # Cotação deve ter sido removida
        assert not CotacaoFornecedor.objects.filter(pk=cotacao_fornecedor.pk).exists()

    def test_remover_cotacao_bloqueia_apos_vencedor(
        self, client, comprador_user, rfq, cotacao_fornecedor
    ):
        """Após selecionar vencedor, remover cotação deve retornar 403 (T-04-03)."""
        rfq.vencedor = cotacao_fornecedor
        rfq.save()

        client.force_login(comprador_user)
        response = client.post(
            f"/cotacoes/{rfq.pk}/cotacoes/{cotacao_fornecedor.pk}/remover/",
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 403


class TestBloqueioPosSeletcao:
    """
    Testes de bloqueio total pós-seleção (T-04-03).

    Após seleção do vencedor, add/remove/modal-selecionar devem ser bloqueados.
    """

    def test_bloqueia_adicionar_apos_vencedor(
        self, client, comprador_user, rfq, cotacao_fornecedor, fornecedor
    ):
        """Apos selecionar vencedor, adicionar cotacao deve retornar 403."""
        rfq.vencedor = cotacao_fornecedor
        rfq.save()
        client.force_login(comprador_user)
        response = client.post(
            f"/cotacoes/{rfq.pk}/cotacoes/adicionar/",
            data={
                "fornecedor": fornecedor.pk,
                "preco_unitario": "300.00",
            },
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 403

    def test_bloqueia_remover_apos_vencedor(
        self, client, comprador_user, rfq, cotacao_fornecedor
    ):
        """Apos selecionar vencedor, remover cotacao deve retornar 403."""
        rfq.vencedor = cotacao_fornecedor
        rfq.save()
        client.force_login(comprador_user)
        response = client.post(
            f"/cotacoes/{rfq.pk}/cotacoes/{cotacao_fornecedor.pk}/remover/",
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 403

    def test_bloqueia_modal_selecionar_apos_vencedor(
        self, client, comprador_user, rfq, cotacao_fornecedor
    ):
        """Apos selecionar vencedor, GET em modal-selecionar deve retornar 409 (T-04-03)."""
        rfq.vencedor = cotacao_fornecedor
        rfq.save()
        client.force_login(comprador_user)
        response = client.get(
            f"/cotacoes/{rfq.pk}/selecionar-vencedor/{cotacao_fornecedor.pk}/modal/",
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 409


class TestModalSelecionarVencedor:
    """
    Testes COT-04: seleção de vencedor via modal HTMX.

    Cobre:
      D-07    Vencedor imutável após seleção
      T-04-06 ValueError → 409 (justificativa vazia ou vencedor já definido)
    """

    def test_get_retorna_partial_modal(self, client, comprador_user, rfq, cotacao_fornecedor):
        """GET para modal de selecao deve retornar partial HTML com form de justificativa."""
        client.force_login(comprador_user)
        response = client.get(
            f"/cotacoes/{rfq.pk}/selecionar-vencedor/{cotacao_fornecedor.pk}/modal/",
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 200
        assert b"justificativa" in response.content

    def test_post_confirma_selecao_e_redireciona(
        self, client, comprador_user, rfq, cotacao_fornecedor
    ):
        """POST com justificativa deve selecionar vencedor e retornar HX-Redirect."""
        client.force_login(comprador_user)
        response = client.post(
            f"/cotacoes/{rfq.pk}/selecionar-vencedor/{cotacao_fornecedor.pk}/",
            data={"justificativa": "Melhor custo-beneficio."},
        )
        assert "HX-Redirect" in response
        assert response.status_code == 200
        rfq.refresh_from_db()
        assert rfq.tem_vencedor is True

    def test_post_justificativa_vazia_retorna_409(
        self, client, comprador_user, rfq, cotacao_fornecedor
    ):
        """POST com justificativa vazia deve retornar 409 e RFQ sem vencedor (T-04-06)."""
        client.force_login(comprador_user)
        response = client.post(
            f"/cotacoes/{rfq.pk}/selecionar-vencedor/{cotacao_fornecedor.pk}/",
            data={"justificativa": ""},
        )
        assert response.status_code == 409
        rfq.refresh_from_db()
        assert rfq.tem_vencedor is False

    def test_post_segundo_selecionar_retorna_409(
        self, client, comprador_user, rfq, cotacao_fornecedor
    ):
        """POST quando vencedor já definido deve retornar 409 (T-04-06, D-07)."""
        # Selecionar vencedor primeiro
        rfq.vencedor = cotacao_fornecedor
        rfq.justificativa_selecao = "Primeira seleção."
        rfq.save()

        client.force_login(comprador_user)
        response = client.post(
            f"/cotacoes/{rfq.pk}/selecionar-vencedor/{cotacao_fornecedor.pk}/",
            data={"justificativa": "Tentativa de segunda seleção."},
        )
        assert response.status_code == 409
