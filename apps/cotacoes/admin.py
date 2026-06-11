from django.contrib import admin

from .models import CotacaoFornecedor, RFQ


@admin.register(RFQ)
class RFQAdmin(admin.ModelAdmin):
    list_display = ("pk", "requisicao", "status_display", "criado_por", "criado_em")
    list_filter = ("criado_em",)
    readonly_fields = ("criado_em", "atualizado_em")


@admin.register(CotacaoFornecedor)
class CotacaoFornecedorAdmin(admin.ModelAdmin):
    list_display = ("pk", "rfq", "fornecedor", "preco_unitario", "prazo_entrega", "criado_em")
    list_filter = ("criado_em",)
    readonly_fields = ("criado_em", "atualizado_em")
