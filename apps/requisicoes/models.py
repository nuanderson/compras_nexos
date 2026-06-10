"""
Modelos de Requisição de Compra.

CategoriaCompra: cadastrável via Admin (D-01, D-03).
Requisicao: herda AuditedModel; FSM com 6 estados e métodos predicado puros (D-12, D-15).
"""
from django.db import models

from apps.core.models import AuditedModel


class CategoriaCompra(models.Model):
    """Categoria de compra cadastrável pelo Admin via Django admin (D-01)."""

    nome = models.CharField(max_length=100)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Categoria de Compra"
        verbose_name_plural = "Categorias de Compra"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Requisicao(AuditedModel):
    """
    Requisição de Compra com máquina de estados de 6 estados.

    Métodos predicado são puros (sem efeito colateral) — a lógica de
    transição vive exclusivamente em apps/aprovacoes/services.py.
    """

    class Status(models.TextChoices):
        RASCUNHO = "RASCUNHO", "Rascunho"
        PENDENTE_GESTOR = "PENDENTE_GESTOR", "Aguardando Gestor"
        PENDENTE_DIRETOR = "PENDENTE_DIRETOR", "Aguardando Diretor"
        APROVADO = "APROVADO", "Aprovado"
        REPROVADO = "REPROVADO", "Reprovado"
        CANCELADO = "CANCELADO", "Cancelado"

    # Estados terminais — nenhuma transição é permitida a partir deles
    ESTADOS_TERMINAIS = {Status.APROVADO, Status.REPROVADO, Status.CANCELADO}

    # Estados em que o Solicitante pode cancelar (D-15)
    CANCELA_PERMISSOES = {Status.RASCUNHO, Status.PENDENTE_GESTOR}

    descricao = models.CharField(max_length=500)
    categoria = models.ForeignKey(
        "CategoriaCompra",
        on_delete=models.PROTECT,
        related_name="requisicoes",
    )
    # DecimalField — nunca FloatField (constraint arquitetural do projeto)
    valor_estimado = models.DecimalField(max_digits=12, decimal_places=2)
    justificativa = models.TextField()
    unidade = models.ForeignKey(
        "accounts.UnidadeOrganizacional",
        on_delete=models.PROTECT,
        related_name="requisicoes",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.RASCUNHO,
    )

    class Meta:
        verbose_name = "Requisição de Compra"
        verbose_name_plural = "Requisições de Compra"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.descricao[:40]} ({self.get_status_display()})"

    # --- Métodos predicado puros (sem efeito colateral) ---

    def pode_submeter(self) -> bool:
        """Solicitante pode enviar para aprovação apenas quando em RASCUNHO (D-12)."""
        return self.status == self.Status.RASCUNHO

    def pode_cancelar(self) -> bool:
        """Solicitante pode cancelar em RASCUNHO ou PENDENTE_GESTOR (D-15)."""
        return self.status in self.CANCELA_PERMISSOES

    def pode_gestor_agir(self) -> bool:
        """Gestor pode aprovar/reprovar apenas quando em PENDENTE_GESTOR."""
        return self.status == self.Status.PENDENTE_GESTOR

    def pode_diretor_agir(self) -> bool:
        """Diretor pode aprovar/reprovar apenas quando em PENDENTE_DIRETOR."""
        return self.status == self.Status.PENDENTE_DIRETOR
