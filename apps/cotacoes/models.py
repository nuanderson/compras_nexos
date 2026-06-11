"""
Modelos de Cotacao (RFQ).

RFQ: processo de cotacao vinculado a uma Requisicao aprovada (OneToOneField, D-06).
CotacaoFornecedor: cotacao de preco de um fornecedor para um RFQ especifico.

Restricoes:
  D-06  OneToOneField garante um RFQ por Requisicao no DB
  D-07  Vencedor armazenado como FK; apos definido, RFQ fica somente leitura
  D-03  preco_unitario = DecimalField — nunca FloatField (constraint arquitetural)
  T-04-04  MinValueValidator(0.01) + guard `menor > 0` em services.calcular_comparativo
"""
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import TimestampedModel


class RFQ(TimestampedModel):
    """
    Processo de cotacao vinculado a uma Requisicao aprovada.
    OneToOneField garante unicidade no DB (D-06).
    """

    requisicao = models.OneToOneField(
        "requisicoes.Requisicao",
        on_delete=models.PROTECT,
        related_name="rfq",
    )
    criado_por = models.ForeignKey(
        "accounts.User",
        null=True,
        on_delete=models.SET_NULL,
        related_name="rfqs_criados",
    )
    vencedor = models.ForeignKey(
        "CotacaoFornecedor",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="rfqs_vencidos",
    )
    justificativa_selecao = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "RFQ"
        verbose_name_plural = "RFQs"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"RFQ #{self.pk} — {self.requisicao.descricao[:40]}"

    @property
    def tem_vencedor(self) -> bool:
        """Propriedade derivada — RFQ esta encerrado quando vencedor definido (D-07)."""
        return self.vencedor_id is not None

    @property
    def status_display(self) -> str:
        return "Encerrado" if self.tem_vencedor else "Em andamento"


class CotacaoFornecedor(TimestampedModel):
    """
    Cotacao de um fornecedor especifico para um RFQ.
    preco_unitario: DecimalField — nunca FloatField (constraint arquitetural).
    MinValueValidator(0.01) previne divisao por zero em calcular_comparativo (T-04-04).
    """

    rfq = models.ForeignKey(
        RFQ,
        on_delete=models.CASCADE,
        related_name="cotacoes",
    )
    fornecedor = models.ForeignKey(
        "fornecedores.Fornecedor",
        on_delete=models.PROTECT,
        related_name="cotacoes",
    )
    preco_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    prazo_entrega = models.CharField(max_length=100, blank=True, default="")
    condicoes_pagamento = models.CharField(max_length=200, blank=True, default="")
    observacoes = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Cotacao de Fornecedor"
        verbose_name_plural = "Cotacoes de Fornecedores"
        ordering = ["preco_unitario"]

    def __str__(self):
        return f"Cotacao {self.fornecedor} — RFQ #{self.rfq_id} — R$ {self.preco_unitario}"
