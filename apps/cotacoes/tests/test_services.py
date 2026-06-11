"""
Testes de service layer para apps/cotacoes.
Estes testes ficam RED ate a Task 3 (services.py) ser implementada.
"""
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.cotacoes import services
from apps.cotacoes.models import CotacaoFornecedor, RFQ


class TestCriarRFQ:
    def test_cria_rfq_vinculado_a_requisicao(self, db, requisicao_aprovada, comprador_user):
        rfq = services.criar_rfq(requisicao_aprovada.pk, comprador_user)
        assert rfq.pk is not None
        assert rfq.requisicao == requisicao_aprovada
        assert rfq.criado_por == comprador_user

    def test_rfq_sem_vencedor_inicial(self, db, requisicao_aprovada, comprador_user):
        rfq = services.criar_rfq(requisicao_aprovada.pk, comprador_user)
        assert rfq.tem_vencedor is False


class TestCriarRFQDuplicado:
    def test_segundo_rfq_para_mesma_requisicao_levanta_integrity_error(
        self, db, requisicao_aprovada, comprador_user
    ):
        services.criar_rfq(requisicao_aprovada.pk, comprador_user)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                services.criar_rfq(requisicao_aprovada.pk, comprador_user)


class TestCalcularComparativo:
    def test_menor_preco_marcado_como_is_menor(self, db, rfq, fornecedor, categoria):
        from apps.fornecedores.models import Fornecedor
        fornecedor2 = Fornecedor.objects.create(
            cnpj="22333444000195",
            razao_social="Empresa B Ltda",
            email="b@empresa.com",
            categoria=categoria,
            ativo=True,
        )
        CotacaoFornecedor.objects.create(
            rfq=rfq,
            fornecedor=fornecedor,
            preco_unitario=Decimal("100.00"),
        )
        CotacaoFornecedor.objects.create(
            rfq=rfq,
            fornecedor=fornecedor2,
            preco_unitario=Decimal("150.00"),
        )
        comparativo = services.calcular_comparativo(rfq)
        assert len(comparativo) == 2
        menores = [item for item in comparativo if item["is_menor"]]
        assert len(menores) == 1
        assert menores[0]["cotacao"].preco_unitario == Decimal("100.00")

    def test_retorna_lista_vazia_sem_cotacoes(self, db, rfq):
        comparativo = services.calcular_comparativo(rfq)
        assert comparativo == []


class TestDeltaPercentual:
    def test_delta_de_50_para_cotacao_150_vs_menor_100(self, db, rfq, fornecedor, categoria):
        from apps.fornecedores.models import Fornecedor
        fornecedor2 = Fornecedor.objects.create(
            cnpj="33444555000106",
            razao_social="Empresa C Ltda",
            email="c@empresa.com",
            categoria=categoria,
            ativo=True,
        )
        CotacaoFornecedor.objects.create(
            rfq=rfq,
            fornecedor=fornecedor,
            preco_unitario=Decimal("100.00"),
        )
        CotacaoFornecedor.objects.create(
            rfq=rfq,
            fornecedor=fornecedor2,
            preco_unitario=Decimal("150.00"),
        )
        comparativo = services.calcular_comparativo(rfq)
        # ordenado por preco ASC: [100, 150]
        item_mais_caro = comparativo[1]
        assert item_mais_caro["delta"] == Decimal("50.0")
        assert item_mais_caro["is_menor"] is False


class TestDeltaZero:
    def test_guard_divisao_por_zero_com_preco_zero(self, db, rfq, fornecedor):
        # Cria cotacao diretamente no banco com preco=0 (burla o validator de form)
        CotacaoFornecedor.objects.create(
            rfq=rfq,
            fornecedor=fornecedor,
            preco_unitario=Decimal("0"),
        )
        # Nao deve levantar ZeroDivisionError
        comparativo = services.calcular_comparativo(rfq)
        assert len(comparativo) == 1
        assert comparativo[0]["delta"] == Decimal("0")


class TestSelecionarVencedor:
    def test_selecionar_vencedor_define_rfq_vencedor(self, db, rfq, cotacao_fornecedor, comprador_user):
        rfq_result = services.selecionar_vencedor(
            rfq_pk=rfq.pk,
            cotacao_pk=cotacao_fornecedor.pk,
            justificativa="Melhor preco e prazo de entrega.",
            comprador=comprador_user,
        )
        rfq_result.refresh_from_db()
        assert rfq_result.tem_vencedor is True
        assert rfq_result.vencedor == cotacao_fornecedor
        assert rfq_result.justificativa_selecao == "Melhor preco e prazo de entrega."


class TestVencedorImutavel:
    def test_segundo_selecionar_vencedor_levanta_value_error(
        self, db, rfq, cotacao_fornecedor, comprador_user
    ):
        services.selecionar_vencedor(
            rfq_pk=rfq.pk,
            cotacao_pk=cotacao_fornecedor.pk,
            justificativa="Primeira selecao.",
            comprador=comprador_user,
        )
        with pytest.raises(ValueError, match="Vencedor já foi definido"):
            services.selecionar_vencedor(
                rfq_pk=rfq.pk,
                cotacao_pk=cotacao_fornecedor.pk,
                justificativa="Segunda tentativa.",
                comprador=comprador_user,
            )


class TestJustificativaObrigatoria:
    def test_justificativa_vazia_levanta_value_error(self, db, rfq, cotacao_fornecedor, comprador_user):
        with pytest.raises(ValueError, match="Justificativa"):
            services.selecionar_vencedor(
                rfq_pk=rfq.pk,
                cotacao_pk=cotacao_fornecedor.pk,
                justificativa="   ",
                comprador=comprador_user,
            )

    def test_justificativa_nula_levanta_value_error(self, db, rfq, cotacao_fornecedor, comprador_user):
        with pytest.raises(ValueError, match="Justificativa"):
            services.selecionar_vencedor(
                rfq_pk=rfq.pk,
                cotacao_pk=cotacao_fornecedor.pk,
                justificativa="",
                comprador=comprador_user,
            )
