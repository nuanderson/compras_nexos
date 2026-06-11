"""
URLs do app estoque.
"""
from django.urls import path

from . import views

app_name = "estoque"

urlpatterns = [
    path("", views.ListaEstoqueView.as_view(), name="lista"),
    path("novo/", views.CadastrarItemEstoqueView.as_view(), name="cadastrar"),
    path("<int:pk>/editar/", views.EditarItemEstoqueView.as_view(), name="editar"),
    path("<int:pk>/quantidade/", views.AtualizarQuantidadeView.as_view(), name="atualizar-quantidade"),
    path("consolidado/", views.VisaoConsolidadaView.as_view(), name="consolidado"),
]
