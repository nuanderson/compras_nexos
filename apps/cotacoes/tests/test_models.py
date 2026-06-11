"""
Testes de modelo para RFQ e CotacaoFornecedor.
"""
import pytest


class TestRFQStr:
    def test_str_inclui_pk_e_descricao(self, rfq):
        resultado = str(rfq)
        assert f"RFQ #{rfq.pk}" in resultado
        assert "Compra de notebooks" in resultado


class TestRFQTemVencedor:
    def test_sem_vencedor_retorna_false(self, rfq):
        assert rfq.tem_vencedor is False

    def test_com_vencedor_retorna_true(self, rfq, cotacao_fornecedor):
        rfq.vencedor = cotacao_fornecedor
        rfq.save()
        rfq.refresh_from_db()
        assert rfq.tem_vencedor is True


class TestRFQStatusDisplay:
    def test_sem_vencedor_retorna_em_andamento(self, rfq):
        assert rfq.status_display == "Em andamento"

    def test_com_vencedor_retorna_encerrado(self, rfq, cotacao_fornecedor):
        rfq.vencedor = cotacao_fornecedor
        rfq.save()
        rfq.refresh_from_db()
        assert rfq.status_display == "Encerrado"


class TestCotacaoFornecedorHerdaTimestamp:
    def test_cotacao_tem_criado_em(self, cotacao_fornecedor):
        assert cotacao_fornecedor.criado_em is not None
