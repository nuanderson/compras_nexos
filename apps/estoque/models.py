"""
Modelos do app estoque.

EST-01 — cadastro de item de estoque por unidade organizacional
EST-02 — quantidade mínima (ponto de pedido)
EST-04 — propriedade abaixo_do_minimo
EST-05 — UniqueConstraint nome+unidade_organizacional (evita duplicatas internas)
D-04   — UnidadeMedida configurável, seeded com 8 unidades
D-06   — FK para UnidadeOrganizacional para isolamento por unidade
"""
from django.db import models

from apps.core.models import TimestampedModel


class UnidadeMedida(models.Model):
    """Unidade de medida configurável pelo Admin. D-04."""

    nome = models.CharField(max_length=50, unique=True)
    sigla = models.CharField(max_length=10, unique=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "Unidade de Medida"
        verbose_name_plural = "Unidades de Medida"

    def __str__(self) -> str:
        return f"{self.nome} ({self.sigla})"


class ItemEstoque(TimestampedModel):
    """
    Item de estoque vinculado a uma unidade organizacional. D-06.

    UniqueConstraint(nome, unidade_organizacional) previne duplicatas internas
    sem bloquear o mesmo nome em unidades diferentes.
    """

    nome = models.CharField(max_length=200)
    unidade_medida = models.ForeignKey(
        UnidadeMedida,
        on_delete=models.PROTECT,
        related_name="itens_estoque",
    )
    quantidade_atual = models.IntegerField(default=0)
    quantidade_minima = models.IntegerField(default=0)
    unidade_organizacional = models.ForeignKey(
        "accounts.UnidadeOrganizacional",
        on_delete=models.PROTECT,
        related_name="itens_estoque",
    )

    class Meta:
        verbose_name = "Item de Estoque"
        verbose_name_plural = "Itens de Estoque"
        ordering = ["nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["nome", "unidade_organizacional"],
                name="unique_item_por_unidade",
            )
        ]

    def __str__(self) -> str:
        return f"{self.nome} ({self.unidade_organizacional})"

    @property
    def abaixo_do_minimo(self) -> bool:
        """True se quantidade_atual < quantidade_minima. EST-04."""
        return self.quantidade_atual < self.quantidade_minima
