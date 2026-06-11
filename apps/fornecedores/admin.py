"""
Django Admin para o app fornecedores.

FornecedorAdmin: listagem com filtros e busca.
"""
from django.contrib import admin

from .models import Fornecedor


@admin.register(Fornecedor)
class FornecedorAdmin(admin.ModelAdmin):
    list_display = ["razao_social", "cnpj", "categoria", "ativo"]
    list_filter = ["ativo", "categoria"]
    search_fields = ["razao_social", "cnpj"]
    list_editable = ["ativo"]
    ordering = ["razao_social"]
