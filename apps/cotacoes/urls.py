"""
URLs do app cotacoes.

namespace="cotacoes" para uso em {% url 'cotacoes:lista' %} etc.

Rotas do plano 02: lista, nova, detalhe.
Rotas do plano 03: adicionar-cotacao, remover-cotacao, modal-selecionar, selecionar-vencedor.
"""
from django.urls import path

from .views import (
    AdicionarCotacaoView,
    DetalheRFQView,
    ListaRFQView,
    ModalSelecionarVencedorView,
    NovaRFQView,
    RemoverCotacaoView,
    SelecionarVencedorView,
)

app_name = "cotacoes"

urlpatterns = [
    path("", ListaRFQView.as_view(), name="lista"),
    path("nova/", NovaRFQView.as_view(), name="nova"),
    path("<int:pk>/", DetalheRFQView.as_view(), name="detalhe"),
    # COT-02: adicionar e remover cotações de fornecedores
    path(
        "<int:rfq_pk>/cotacoes/adicionar/",
        AdicionarCotacaoView.as_view(),
        name="adicionar-cotacao",
    ),
    path(
        "<int:rfq_pk>/cotacoes/<int:cotacao_pk>/remover/",
        RemoverCotacaoView.as_view(),
        name="remover-cotacao",
    ),
    # COT-04: modal e confirmação de seleção de vencedor
    path(
        "<int:rfq_pk>/selecionar-vencedor/<int:cotacao_pk>/modal/",
        ModalSelecionarVencedorView.as_view(),
        name="modal-selecionar",
    ),
    path(
        "<int:rfq_pk>/selecionar-vencedor/<int:cotacao_pk>/",
        SelecionarVencedorView.as_view(),
        name="selecionar-vencedor",
    ),
]
