"""
URLs do app de Requisições.

Namespace: requisicoes

Rotas:
  lista         GET  /requisicoes/
  nova          GET/POST  /requisicoes/nova/
  copiar-dados  GET  /requisicoes/copiar-dados/
  detalhe       GET  /requisicoes/<pk>/
  editar        GET/POST  /requisicoes/<pk>/editar/
  enviar        POST /requisicoes/<pk>/enviar/
  cancelar      POST /requisicoes/<pk>/cancelar/
  status        GET  /requisicoes/<pk>/status/

ATENÇÃO: as rotas sem pk (nova, copiar-dados) devem vir ANTES de <int:pk>/
"""
from django.urls import path

from . import views

app_name = "requisicoes"

urlpatterns = [
    # Rotas sem pk — devem vir antes de <int:pk>/
    path("", views.RequisicaoListView.as_view(), name="lista"),
    path("nova/", views.RequisicaoCreateView.as_view(), name="nova"),
    path("copiar-dados/", views.CopiarDadosView.as_view(), name="copiar-dados"),
    # Rotas com pk
    path("<int:pk>/", views.RequisicaoDetailView.as_view(), name="detalhe"),
    path("<int:pk>/editar/", views.RequisicaoUpdateView.as_view(), name="editar"),
    path("<int:pk>/enviar/", views.RequisicaoEnviarView.as_view(), name="enviar"),
    path("<int:pk>/cancelar/", views.RequisicaoCancelarView.as_view(), name="cancelar"),
    path("<int:pk>/status/", views.StatusBadgeView.as_view(), name="status"),
]
