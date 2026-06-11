"""
Testes de views para apps/cotacoes.

TestNovaRFQView: conectada no plano 02 — COT-01 GREEN.
Demais classes (plano 03): ainda em skip.
"""
from decimal import Decimal

import pytest

from apps.cotacoes.models import RFQ
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


@pytest.mark.skip(reason="View conectada no plano 03")
class TestAdicionarCotacaoView:
    def test_adicionar_cotacao_retorna_redirect_htmx(self, client, comprador_user, rfq, fornecedor):
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
        assert response.status_code in (200, 302)
        assert "HX-Redirect" in response or response.status_code == 302


@pytest.mark.skip(reason="View conectada no plano 03")
class TestRemoverCotacaoView:
    def test_remover_cotacao_retorna_redirect_htmx(
        self, client, comprador_user, rfq, cotacao_fornecedor
    ):
        """POST para remover cotacao deve retornar HX-Redirect para detalhe do RFQ."""
        client.force_login(comprador_user)
        response = client.post(
            f"/cotacoes/{rfq.pk}/cotacoes/{cotacao_fornecedor.pk}/remover/",
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code in (200, 302)


@pytest.mark.skip(reason="View conectada no plano 03")
class TestBloqueioPosSeletcao:
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


@pytest.mark.skip(reason="View conectada no plano 03")
class TestModalSelecionarVencedor:
    def test_get_retorna_partial_modal(self, client, comprador_user, rfq, cotacao_fornecedor):
        """GET para modal de selecao deve retornar partial HTML com form."""
        client.force_login(comprador_user)
        response = client.get(
            f"/cotacoes/{rfq.pk}/selecionar-vencedor/{cotacao_fornecedor.pk}/",
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 200

    def test_post_confirma_selecao_e_redireciona(
        self, client, comprador_user, rfq, cotacao_fornecedor
    ):
        """POST com justificativa deve selecionar vencedor e redirecionar."""
        client.force_login(comprador_user)
        response = client.post(
            f"/cotacoes/{rfq.pk}/selecionar-vencedor/{cotacao_fornecedor.pk}/",
            data={"justificativa": "Melhor custo-beneficio."},
        )
        assert response.status_code in (200, 302)
        rfq.refresh_from_db()
        assert rfq.tem_vencedor is True
