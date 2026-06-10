"""
Registro de modelos de aprovação no Django admin.

ConfiguracaoAlcada: singleton — impede criação de 2ª linha e exclusão (D-08, D-11, APROV-06).
AprovacaoLog: somente-leitura — trilha de auditoria imutável (REQ-03).
"""
from django.contrib import admin

from .models import AprovacaoLog, ConfiguracaoAlcada


@admin.register(ConfiguracaoAlcada)
class ConfiguracaoAlcadaAdmin(admin.ModelAdmin):
    """
    Singleton — Admin/Diretor configura o valor máximo para aprovação pelo Gestor.

    Segurança (T-02-01-02):
    - has_add_permission: bloqueia criação de 2ª linha (singleton pk=1 via obter())
    - has_delete_permission: impede remoção e recriação fora do pk=1
    """

    list_display = ["valor_maximo_gestor"]

    def has_add_permission(self, request):
        """Impede criação de mais de uma configuração de alçada (singleton)."""
        return not ConfiguracaoAlcada.objects.exists()

    def has_delete_permission(self, request, obj=None):
        """Singleton não pode ser deletado — evita recriar fora do pk=1."""
        return False


@admin.register(AprovacaoLog)
class AprovacaoLogAdmin(admin.ModelAdmin):
    """
    Trilha de auditoria imutável — apenas leitura.

    Segurança (T-02-01-03):
    - has_add_permission: False — logs são criados apenas pelo service layer
    - has_delete_permission: False — log de auditoria não pode ser apagado (REQ-03)
    - readonly_fields: todos os campos são somente-leitura
    """

    list_display = ["requisicao", "aprovador", "evento", "criado_em"]
    list_filter = ["evento"]
    readonly_fields = [
        "requisicao",
        "aprovador",
        "evento",
        "motivo",
        "criado_em",
        "atualizado_em",
    ]

    def has_add_permission(self, request):
        """Logs são criados automaticamente pelo service — não pelo admin."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Logs de auditoria são imutáveis — nunca excluir (REQ-03)."""
        return False
