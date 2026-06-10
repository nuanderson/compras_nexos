"""
Modelos de Aprovação.

AprovacaoLog: trilha de auditoria imutável (REQ-03, D-19).
ConfiguracaoAlcada: singleton para configuração do valor máximo do Gestor (D-08, D-09, D-10).
"""
from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.core.models import TimestampedModel


class AprovacaoLog(TimestampedModel):
    """
    Trilha de auditoria imutável de cada transição de estado de uma Requisicao.

    Campos são somente-leitura após criação — nunca editar nem excluir logs (REQ-03).
    """

    class Evento(models.TextChoices):
        ENVIO = "ENVIO", "Envio para Aprovação"
        APROVACAO_GESTOR = "APROVACAO_GESTOR", "Aprovação pelo Gestor"
        APROVACAO_FINAL = "APROVACAO_FINAL", "Aprovação Final"
        REPROVACAO = "REPROVACAO", "Reprovação"
        CANCELAMENTO = "CANCELAMENTO", "Cancelamento"

    requisicao = models.ForeignKey(
        "requisicoes.Requisicao",
        on_delete=models.CASCADE,
        related_name="logs",
    )
    aprovador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="aprovacoes_realizadas",
    )
    evento = models.CharField(max_length=20, choices=Evento.choices)
    motivo = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Log de Aprovação"
        verbose_name_plural = "Logs de Aprovação"
        ordering = ["criado_em"]

    def __str__(self):
        return f"{self.get_evento_display()} — {self.requisicao_id}"


class ConfiguracaoAlcada(models.Model):
    """
    Configuração singleton de alçada de aprovação (D-08, D-09, D-10).

    Uma única linha na tabela — sempre acessada via `obter()`.
    Se `valor_maximo_gestor` for None, aplica o comportamento seguro: sempre 2 níveis (D-10).
    """

    # DecimalField — nunca FloatField (constraint arquitetural do projeto)
    valor_maximo_gestor = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=(
            "Valor máximo para aprovação apenas pelo Gestor (R$). "
            "Acima deste valor, exige aprovação do Diretor também. "
            "Deixe em branco para sempre exigir 2 níveis (comportamento seguro)."
        ),
    )

    class Meta:
        verbose_name = "Configuração de Alçada"
        verbose_name_plural = "Configuração de Alçada"

    def __str__(self):
        if self.valor_maximo_gestor is None:
            return "Alçada: sempre 2 níveis (sem limite configurado)"
        return f"Alçada: Gestor até R$ {self.valor_maximo_gestor:,.2f}"

    @classmethod
    def obter(cls) -> "ConfiguracaoAlcada":
        """
        Retorna a configuração singleton. Cria uma nova (pk=1) se não existir.

        Usar sempre este método — nunca `get(pk=1)` diretamente (armadilha 6 do RESEARCH.md).
        """
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def requer_diretor(self, valor: Decimal) -> bool:
        """
        Retorna True se o valor da requisição exige aprovação do Diretor (2 níveis).

        Fail-safe (D-10): se valor_maximo_gestor for None, sempre retorna True.
        """
        if self.valor_maximo_gestor is None:
            return True  # fail-safe: sem configuração = sempre 2 níveis
        return valor >= self.valor_maximo_gestor
