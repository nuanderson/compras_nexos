"""
URLs do app fornecedores.

namespace="fornecedores" para uso em {% url 'fornecedores:lista' %} etc.
"""
from django.urls import path

from .views import (
    CadastrarFornecedorView,
    EditarFornecedorView,
    ListaFornecedoresView,
    ToggleAtivoView,
)

app_name = "fornecedores"

urlpatterns = [
    path("", ListaFornecedoresView.as_view(), name="lista"),
    path("novo/", CadastrarFornecedorView.as_view(), name="cadastrar"),
    path("<int:pk>/editar/", EditarFornecedorView.as_view(), name="editar"),
    path("<int:pk>/toggle-ativo/", ToggleAtivoView.as_view(), name="toggle-ativo"),
]
