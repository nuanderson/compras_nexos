"""
URLs do app cotacoes.

namespace="cotacoes" para uso em {% url 'cotacoes:lista' %} etc.
"""
from django.urls import path

from .views import DetalheRFQView, ListaRFQView, NovaRFQView

app_name = "cotacoes"

urlpatterns = [
    path("", ListaRFQView.as_view(), name="lista"),
    path("nova/", NovaRFQView.as_view(), name="nova"),
    path("<int:pk>/", DetalheRFQView.as_view(), name="detalhe"),
]
