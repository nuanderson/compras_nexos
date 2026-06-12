"""
URLs do app relatorios.

namespace="relatorios" para uso em {% url 'relatorios:gastos' %} etc.

Rotas do plano 05-02: gastos, gastos-pdf (stub), requisicoes, requisicoes-pdf (stub).
Os endpoints PDF retornam HTTP 501 ate o plano 05-03 implementar o corpo real.
"""
from django.urls import path

from .views import GastosPDFView, GastosView, RequisicoesPDFView, RequisicoesPainelView

app_name = "relatorios"

urlpatterns = [
    path("gastos/", GastosView.as_view(), name="gastos"),
    path("gastos/pdf/", GastosPDFView.as_view(), name="gastos-pdf"),
    path("requisicoes/", RequisicoesPainelView.as_view(), name="requisicoes"),
    path("requisicoes/pdf/", RequisicoesPDFView.as_view(), name="requisicoes-pdf"),
]
