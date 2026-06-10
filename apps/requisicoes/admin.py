"""
Registro de modelos de requisição no Django admin.

CategoriaCompra é gerenciável via admin (D-01, D-03).
"""
from django.contrib import admin

from .models import CategoriaCompra


@admin.register(CategoriaCompra)
class CategoriaCompraAdmin(admin.ModelAdmin):
    """Permite ao Admin criar e gerenciar categorias de compra."""

    list_display = ["nome", "ativo"]
    list_filter = ["ativo"]
    search_fields = ["nome"]
