"""
Aprovacoes views.
Slice vertical do Gestor: fila de aprovacao, modal de reprovacao, acoes de aprovar/reprovar.

Referencias:
  APROV-01  fila filtrada por unidade
  APROV-02  aprovar/reprovar 1o nivel
  APROV-05  motivo obrigatorio em reprovacao
  T-03-01   verificacao de ownership de unidade
  T-03-02   GestorRequiredMixin bloqueia Solicitante
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views import View
from django.views.generic import ListView

from apps.requisicoes.models import Requisicao
from . import services
from .forms import ReprovaForm


class GestorRequiredMixin(LoginRequiredMixin):
    """Restringe acesso a usuarios com role='gestor', 'admin' ou is_superuser. (T-03-02)"""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (
            request.user.is_superuser
            or request.user.role in (
                "gestor",
                "admin",
            )
        ):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class FilaGestorView(GestorRequiredMixin, ListView):
    """
    Fila de requisicoes PENDENTE_GESTOR filtrada pela unidade do Gestor. (APROV-01, D-04, D-05)
    Gestor com default_unit=None recebe queryset vazio (Armadilha 3).
    """
    template_name = "aprovacoes/fila_gestor.html"
    context_object_name = "requisicoes"

    def get_queryset(self):
        if not self.request.user.default_unit:
            return Requisicao.objects.none()
        return (
            Requisicao.objects
            .filter(
                status=Requisicao.Status.PENDENTE_GESTOR,
                unidade=self.request.user.default_unit,
            )
            .select_related("criado_por", "categoria", "unidade")
            .order_by("criado_em")
        )


class AprovarGestorView(GestorRequiredMixin, View):
    """
    POST: transicao PENDENTE_GESTOR -> APROVADO ou PENDENTE_DIRETOR via services.aprovar_gestor.
    Remove a linha da fila via outerHTML swap vazio. (APROV-02, D-09, T-03-01)
    """

    def post(self, request, pk):
        req = get_object_or_404(Requisicao, pk=pk)
        # Verificacao de ownership de unidade (T-03-01)
        if not (request.user.is_superuser or request.user.role == "admin"):
            if req.unidade != request.user.default_unit:
                raise PermissionDenied
        try:
            services.aprovar_gestor(pk, request.user)
        except (ValueError, PermissionError) as e:
            return HttpResponse(str(e), status=409)
        # Retorna resposta vazia para remover a linha da fila via outerHTML swap
        return HttpResponse("")


class ModalReprovarView(GestorRequiredMixin, View):
    """
    GET: retorna o partial do modal de reprovacao com o formulario. (APROV-05, T-03-01)
    """

    def get(self, request, pk):
        req = get_object_or_404(Requisicao, pk=pk)
        # Verificacao de ownership de unidade (T-03-01)
        if not (request.user.is_superuser or request.user.role == "admin"):
            if req.unidade != request.user.default_unit:
                raise PermissionDenied
        form = ReprovaForm()
        return render(request, "aprovacoes/partials/modal_reprovar.html", {
            "requisicao": req,
            "form": form,
        })


class ReprovarGestorView(GestorRequiredMixin, View):
    """
    POST: transicao para REPROVADO via services.reprovar_requisicao.
    Motivo obrigatorio validado pelo form (APROV-05, T-03-03).
    Remove a linha da fila via outerHTML swap vazio. (T-03-01)
    """

    def post(self, request, pk):
        req = get_object_or_404(Requisicao, pk=pk)
        # Verificacao de ownership de unidade (T-03-01)
        if not (request.user.is_superuser or request.user.role == "admin"):
            if req.unidade != request.user.default_unit:
                raise PermissionDenied
        form = ReprovaForm(request.POST)
        if not form.is_valid():
            # Retorna o modal com erros sem transicionar o estado (APROV-05)
            return render(request, "aprovacoes/partials/modal_reprovar.html", {
                "requisicao": req,
                "form": form,
            }, status=200)
        try:
            services.reprovar_requisicao(pk, request.user, form.cleaned_data["motivo"])
        except (ValueError, PermissionError) as e:
            return HttpResponse(str(e), status=409)
        # Retorna resposta vazia para remover a linha da fila via outerHTML swap
        return HttpResponse("")


# ─────────────────────────────────────────────────────────────────────────────
# Slice do Diretor — 2o nível de aprovacao
# APROV-03  fila sem filtro de unidade (D-06)
# APROV-04  aprovar/reprovar de 2o nivel
# APROV-05  motivo obrigatorio em reprovacao
# D-13      reprovacao permanente
# T-04-01   DiretorRequiredMixin bloqueia Gestor/Solicitante
# T-04-05   csrf_token no modal
# ─────────────────────────────────────────────────────────────────────────────


class DiretorRequiredMixin(LoginRequiredMixin):
    """Restringe acesso a usuarios com role='diretor', 'admin' ou is_superuser. (T-04-01)"""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (
            request.user.is_superuser
            or request.user.role in (
                "diretor",
                "admin",
            )
        ):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class FilaDiretorView(DiretorRequiredMixin, ListView):
    """
    Fila de requisicoes PENDENTE_DIRETOR de TODAS as unidades. (APROV-03, D-06)
    Diretor nao tem filtro de unidade — ve o orgao inteiro.
    """

    template_name = "aprovacoes/fila_diretor.html"
    context_object_name = "requisicoes"

    def get_queryset(self):
        # Sem filtro de unidade (D-06) — Diretor ve todas as unidades
        return (
            Requisicao.objects
            .filter(status=Requisicao.Status.PENDENTE_DIRETOR)
            .select_related("criado_por", "categoria", "unidade")
            .order_by("criado_em")
        )


class AprovarDiretorView(DiretorRequiredMixin, View):
    """
    POST: transicao PENDENTE_DIRETOR -> APROVADO via services.aprovar_diretor.
    Remove a linha da fila via outerHTML swap vazio. (APROV-04, T-04-03, T-04-04)
    """

    def post(self, request, pk):
        get_object_or_404(Requisicao, pk=pk)   # raises 404 for unknown pk (CR-01)
        try:
            services.aprovar_diretor(pk, request.user)
        except (ValueError, PermissionError) as e:
            return HttpResponse(str(e), status=409)
        # Retorna resposta vazia para remover a linha da fila via outerHTML swap
        return HttpResponse("")


class ModalReprovarDiretorView(DiretorRequiredMixin, View):
    """
    GET: retorna o partial do modal de reprovacao do Diretor. (APROV-05, T-04-05)
    """

    def get(self, request, pk):
        req = get_object_or_404(Requisicao, pk=pk)
        form = ReprovaForm()
        return render(request, "aprovacoes/partials/modal_reprovar_diretor.html", {
            "requisicao": req,
            "form": form,
        })


class ReprovarDiretorView(DiretorRequiredMixin, View):
    """
    POST: transicao para REPROVADO via services.reprovar_requisicao.
    Motivo obrigatorio validado pelo form (APROV-05, T-04-02, T-04-03).
    Remove a linha da fila via outerHTML swap vazio.
    """

    def post(self, request, pk):
        req = get_object_or_404(Requisicao, pk=pk)
        form = ReprovaForm(request.POST)
        if not form.is_valid():
            # Retorna o modal com erros sem transicionar o estado (APROV-05)
            return render(request, "aprovacoes/partials/modal_reprovar_diretor.html", {
                "requisicao": req,
                "form": form,
            }, status=200)
        try:
            services.reprovar_requisicao(pk, request.user, form.cleaned_data["motivo"])
        except (ValueError, PermissionError) as e:
            return HttpResponse(str(e), status=409)
        # Retorna resposta vazia para remover a linha da fila via outerHTML swap
        return HttpResponse("")
