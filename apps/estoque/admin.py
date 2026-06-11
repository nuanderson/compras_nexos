"""
Admin do app estoque.
"""
from django.contrib import admin

from .models import ItemEstoque, UnidadeMedida


@admin.register(UnidadeMedida)
class UnidadeMedidaAdmin(admin.ModelAdmin):
    list_display = ["nome", "sigla", "ativo"]
    list_editable = ["ativo"]
    list_filter = ["ativo"]
    search_fields = ["nome", "sigla"]
    ordering = ["nome"]


@admin.register(ItemEstoque)
class ItemEstoqueAdmin(admin.ModelAdmin):
    list_display = [
        "nome",
        "unidade_organizacional",
        "quantidade_atual",
        "quantidade_minima",
        "abaixo_do_minimo_display",
    ]
    list_filter = ["unidade_organizacional", "unidade_medida"]
    search_fields = ["nome"]
    raw_id_fields = ["unidade_organizacional"]

    @admin.display(boolean=True, description="Abaixo do mínimo")
    def abaixo_do_minimo_display(self, obj):
        return obj.abaixo_do_minimo
