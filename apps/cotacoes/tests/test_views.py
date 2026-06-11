"""
Testes de views para apps/cotacoes.
Testes marcados com skip — as views serao conectadas nos planos 02 e 03.
"""
import pytest


@pytest.mark.skip(reason="View conectada no plano 02/03")
class TestNovaRFQView:
    def test_acesso_negado_solicitante(self, client, solicitante_user):
        """Solicitante deve receber 403 ao tentar acessar /cotacoes/nova/."""
        client.force_login(solicitante_user)
        response = client.get("/cotacoes/nova/")
        assert response.status_code == 403

    def test_select_filtra_aprovadas_sem_rfq(self, client, comprador_user, requisicao_aprovada):
        """Select de requisicoes deve exibir apenas APROVADO sem RFQ vinculado."""
        client.force_login(comprador_user)
        response = client.get("/cotacoes/nova/")
        assert response.status_code == 200
        assert requisicao_aprovada in response.context["form"].fields["requisicao"].queryset


@pytest.mark.skip(reason="View conectada no plano 02/03")
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


@pytest.mark.skip(reason="View conectada no plano 02/03")
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


@pytest.mark.skip(reason="View conectada no plano 02/03")
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


@pytest.mark.skip(reason="View conectada no plano 02/03")
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
