"""
Testes de views para apps/relatorios — Wave 0 (RED intencional).

ESTADO: RED INTENCIONAL
As views /relatorios/gastos/, /relatorios/requisicoes/, /relatorios/gastos/pdf/ e
/relatorios/requisicoes/pdf/ ainda NAO existem (sao criadas no plano 05-02).
Estes testes falham com 404 ou NoReverseMatch porque as URLs ainda nao estao registradas.
Esse comportamento e o esperado para a Wave 0 (scaffold de testes).
GREEN vem no plano 05-02 (views) e 05-03 (PDF).
"""
import pytest


class TestAcesso:
    """
    Testes de controle de acesso as views de relatorios (T-05-12).

    RED intencional — views ainda nao existem (plano 05-02).
    Quando as views existirem:
      - Solicitante deve receber 403 em /relatorios/gastos/
      - Comprador, Diretor e Admin devem receber 200
    """

    def test_solicitante_negado_gastos(self, client, solicitante_user):
        """
        Solicitante deve receber 403 ao tentar acessar /relatorios/gastos/.

        RED: falha com 404 enquanto a URL nao esta registrada (plano 05-02).
        GREEN: esperado 403 apos implementacao de GastosView com RelatorioRequiredMixin.
        """
        client.force_login(solicitante_user)
        response = client.get("/relatorios/gastos/")
        # RED: 404 enquanto URL nao existe; GREEN: 403
        assert response.status_code == 403

    def test_comprador_acessa_gastos(self, client, comprador_user):
        """
        Comprador deve receber 200 em /relatorios/gastos/.

        RED: falha com 404 enquanto a URL nao esta registrada (plano 05-02).
        """
        client.force_login(comprador_user)
        response = client.get("/relatorios/gastos/")
        assert response.status_code == 200

    def test_diretor_acessa_gastos(self, client, diretor_user):
        """
        Diretor deve receber 200 em /relatorios/gastos/.

        RED: falha enquanto a URL nao esta registrada (plano 05-02).
        """
        client.force_login(diretor_user)
        response = client.get("/relatorios/gastos/")
        assert response.status_code == 200

    def test_admin_acessa_gastos(self, client, admin_user):
        """
        Admin deve receber 200 em /relatorios/gastos/.

        RED: falha enquanto a URL nao esta registrada (plano 05-02).
        """
        client.force_login(admin_user)
        response = client.get("/relatorios/gastos/")
        assert response.status_code == 200


class TestGastosView:
    """
    Testes para GastosView — /relatorios/gastos/ (T-05-06..08, REL-02).

    RED intencional — view ainda nao existe (plano 05-02).
    """

    def test_gastos_retorna_200(self, client, comprador_user):
        """
        GET /relatorios/gastos/ deve retornar 200 para comprador.

        RED: falha com 404 enquanto a URL nao esta registrada.
        """
        client.force_login(comprador_user)
        response = client.get("/relatorios/gastos/")
        assert response.status_code == 200

    def test_gastos_com_filtros_de_data(self, client, comprador_user):
        """
        GET /relatorios/gastos/?data_inicio=...&data_fim=... deve retornar 200.

        RED: falha enquanto a URL nao esta registrada.
        """
        from datetime import date
        hoje = date.today()
        inicio = hoje.replace(day=1).isoformat()
        fim = hoje.isoformat()

        client.force_login(comprador_user)
        response = client.get(f"/relatorios/gastos/?data_inicio={inicio}&data_fim={fim}")
        assert response.status_code == 200

    def test_gastos_contexto_contem_dados(self, client, comprador_user):
        """
        GastosView deve passar 'gastos' no contexto do template.

        RED: falha enquanto a view nao esta implementada.
        """
        client.force_login(comprador_user)
        response = client.get("/relatorios/gastos/")
        assert response.status_code == 200
        assert "gastos" in response.context


class TestRequisicoesPainelView:
    """
    Testes para RequisicoesPainelView — /relatorios/requisicoes/ (T-05-09..11, REL-03).

    RED intencional — view ainda nao existe (plano 05-02).
    """

    def test_requisicoes_retorna_200(self, client, comprador_user):
        """
        GET /relatorios/requisicoes/ deve retornar 200 para comprador.

        RED: falha enquanto a URL nao esta registrada.
        """
        client.force_login(comprador_user)
        response = client.get("/relatorios/requisicoes/")
        assert response.status_code == 200

    def test_requisicoes_com_filtro_status(self, client, comprador_user):
        """
        GET /relatorios/requisicoes/?status=RASCUNHO deve retornar 200.

        RED: falha enquanto a URL nao esta registrada.
        """
        client.force_login(comprador_user)
        response = client.get("/relatorios/requisicoes/?status=RASCUNHO")
        assert response.status_code == 200


class TestPDF:
    """
    Testes para GastosPDFView e RequisicoesPainelPDFView (T-05-... REL-04).

    RED intencional — views PDF ainda nao existem (plano 05-03).
    """

    def test_pdf_gastos_content_type(self, client, comprador_user):
        """
        GET /relatorios/gastos/pdf/ deve retornar Content-Type: application/pdf.

        RED: falha com 404 enquanto a URL nao esta registrada.
        """
        client.force_login(comprador_user)
        response = client.get("/relatorios/gastos/pdf/")
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"

    def test_pdf_gastos_attachment(self, client, comprador_user):
        """
        GET /relatorios/gastos/pdf/ deve ter Content-Disposition: attachment.

        RED: falha enquanto a URL nao esta registrada.
        """
        client.force_login(comprador_user)
        response = client.get("/relatorios/gastos/pdf/")
        assert response.status_code == 200
        assert "attachment" in response.get("Content-Disposition", "")

    def test_pdf_requisicoes_content_type(self, client, comprador_user):
        """
        GET /relatorios/requisicoes/pdf/ deve retornar Content-Type: application/pdf.

        RED: falha enquanto a URL nao esta registrada.
        """
        client.force_login(comprador_user)
        response = client.get("/relatorios/requisicoes/pdf/")
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"
