"""
Root URL configuration for ComprasNexos.
"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("requisicoes/", include("apps.requisicoes.urls")),
    path("aprovacoes/", include("apps.aprovacoes.urls")),
    path("fornecedores/", include("apps.fornecedores.urls")),
    path("estoque/", include("apps.estoque.urls")),
    path("cotacoes/", include("apps.cotacoes.urls")),
    path("relatorios/", include("apps.relatorios.urls")),
    path("", include("apps.core.urls")),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns
