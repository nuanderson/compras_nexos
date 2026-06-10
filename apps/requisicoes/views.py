"""
Views do Solicitante para o app de Requisições.

Views:
  - SolicitanteRequiredMixin: mixin de role
  - RequisicaoListView: lista das próprias requisições
  - RequisicaoCreateView: criar rascunho
  - RequisicaoUpdateView: editar rascunho
  - RequisicaoDetailView: detalhe + histórico
  - RequisicaoEnviarView: enviar para aprovação
  - RequisicaoCancelarView: cancelar requisição
  - StatusBadgeView: partial do badge de status (polling HTMX)
  - CopiarDadosView: pré-preencher campos a partir de requisição anterior
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import ListView

from apps.aprovacoes import services

from .forms import RequisicaoForm
from .models import Requisicao


# ──────────────────────────────────────────────────────────────────────────────
# Permission mixin
# ──────────────────────────────────────────────────────────────────────────────


class SolicitanteRequiredMixin(LoginRequiredMixin):
    """
    Restringe acesso a usuários com role='solicitante' ou 'admin', e superusers.

    Gestores e Diretores também podem acessar (eles têm visibilidade das requisições
    conforme a lógica de ownership em _get_requisicao_para).
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        # Todos os usuários autenticados do sistema podem acessar as views do Solicitante;
        # a filtragem por ownership é feita em _get_requisicao_para e get_queryset.
        return super().dispatch(request, *args, **kwargs)


# ──────────────────────────────────────────────────────────────────────────────
# Ownership helper
# ──────────────────────────────────────────────────────────────────────────────


def _get_requisicao_para(user, pk):
    """
    Retorna a Requisicao com pk dado, aplicando verificação de ownership.

    Regras (RESEARCH.md §Verificação Adicional de Ownership, T-02-04):
      - admin/superuser: vê tudo
      - diretor: vê tudo (D-06)
      - gestor: vê apenas requisições da própria unidade (D-05)
      - solicitante: vê apenas as próprias
    """
    req = get_object_or_404(Requisicao, pk=pk)

    if user.is_superuser or user.role in ("admin", "diretor"):
        return req

    if user.role == "gestor":
        if user.default_unit is None or req.unidade != user.default_unit:
            raise PermissionDenied
        return req

    # Solicitante (ou comprador): apenas as próprias
    if req.criado_por != user:
        raise PermissionDenied

    return req


# ──────────────────────────────────────────────────────────────────────────────
# Views
# ──────────────────────────────────────────────────────────────────────────────


class RequisicaoListView(SolicitanteRequiredMixin, ListView):
    """Lista das próprias requisições do Solicitante."""

    model = Requisicao
    template_name = "requisicoes/requisicao_list.html"
    context_object_name = "requisicoes"

    def get_queryset(self):
        return (
            Requisicao.objects.filter(criado_por=self.request.user)
            .select_related("categoria", "unidade")
            .order_by("-criado_em")
        )


class RequisicaoCreateView(SolicitanteRequiredMixin, View):
    """Criação de nova requisição em RASCUNHO. (D-12, REQ-01)"""

    def get(self, request):
        form = RequisicaoForm(user=request.user)
        requisicoes_anteriores = Requisicao.objects.filter(
            criado_por=request.user
        ).order_by("-criado_em")[:20]
        return render(
            request,
            "requisicoes/requisicao_form.html",
            {
                "form": form,
                "action": "create",
                "page_title": "Nova Requisição",
                "requisicoes_anteriores": requisicoes_anteriores,
            },
        )

    def post(self, request):
        form = RequisicaoForm(request.POST, user=request.user)
        if form.is_valid():
            req = form.save(commit=False)
            req.criado_por = request.user
            req.save()  # status=RASCUNHO por default (D-12) — NÃO submete
            if request.htmx:
                from django_htmx.http import HttpResponseClientRedirect

                return HttpResponseClientRedirect(reverse("requisicoes:lista"))
            return redirect("requisicoes:lista")

        template = (
            "requisicoes/partials/campos_requisicao.html"
            if request.htmx
            else "requisicoes/requisicao_form.html"
        )
        return render(
            request,
            template,
            {
                "form": form,
                "action": "create",
            },
        )


class RequisicaoUpdateView(SolicitanteRequiredMixin, View):
    """Edição de rascunho existente. Apenas status=RASCUNHO. (D-12)"""

    def get(self, request, pk):
        req = _get_requisicao_para(request.user, pk)
        if req.status != Requisicao.Status.RASCUNHO:
            raise PermissionDenied
        form = RequisicaoForm(instance=req, user=request.user)
        return render(
            request,
            "requisicoes/requisicao_form.html",
            {
                "form": form,
                "action": "edit",
                "requisicao": req,
                "page_title": "Editar Requisição",
            },
        )

    def post(self, request, pk):
        req = _get_requisicao_para(request.user, pk)
        if req.status != Requisicao.Status.RASCUNHO:
            raise PermissionDenied

        form = RequisicaoForm(request.POST, instance=req, user=request.user)
        if form.is_valid():
            form.save()
            if request.htmx:
                from django_htmx.http import HttpResponseClientRedirect

                return HttpResponseClientRedirect(
                    reverse("requisicoes:detalhe", kwargs={"pk": req.pk})
                )
            return redirect("requisicoes:detalhe", pk=req.pk)

        template = (
            "requisicoes/partials/campos_requisicao.html"
            if request.htmx
            else "requisicoes/requisicao_form.html"
        )
        return render(
            request,
            template,
            {"form": form, "action": "edit", "requisicao": req},
        )


class RequisicaoDetailView(SolicitanteRequiredMixin, View):
    """Detalhe da requisição com histórico de aprovações. (REQ-02, REQ-03)"""

    def get(self, request, pk):
        req = _get_requisicao_para(request.user, pk)
        logs = req.logs.select_related("aprovador").all()
        return render(
            request,
            "requisicoes/requisicao_detail.html",
            {
                "requisicao": req,
                "logs": logs,
                "page_title": f"Requisição #{req.pk}",
            },
        )


class RequisicaoEnviarView(SolicitanteRequiredMixin, View):
    """Envio da requisição para aprovação. RASCUNHO → PENDENTE_GESTOR. (REQ-03)"""

    def post(self, request, pk):
        try:
            req = services.submeter_requisicao(pk, request.user)
        except (ValueError, PermissionError) as exc:
            # Armadilha 4 do RESEARCH.md: retornar 409 com mensagem amigável
            from django.http import HttpResponse

            return HttpResponse(
                f"Não foi possível enviar a requisição: {exc}",
                status=409,
            )

        if request.htmx:
            from django_htmx.http import HttpResponseClientRedirect

            return HttpResponseClientRedirect(
                reverse("requisicoes:detalhe", kwargs={"pk": req.pk})
            )
        return redirect("requisicoes:detalhe", pk=req.pk)


class RequisicaoCancelarView(SolicitanteRequiredMixin, View):
    """Cancelamento da requisição. Permitido em RASCUNHO ou PENDENTE_GESTOR. (D-15)"""

    def post(self, request, pk):
        try:
            req = services.cancelar_requisicao(pk, request.user)
        except (ValueError, PermissionError) as exc:
            from django.http import HttpResponse

            return HttpResponse(
                f"Não foi possível cancelar a requisição: {exc}",
                status=409,
            )

        if request.htmx:
            return render(
                request,
                "requisicoes/partials/requisicao_row.html",
                {"requisicao": req},
            )
        return redirect("requisicoes:lista")


class StatusBadgeView(SolicitanteRequiredMixin, View):
    """
    Partial do badge de status para polling HTMX. (REQ-02)
    GET /requisicoes/<pk>/status/ → partials/status_badge.html
    """

    def get(self, request, pk):
        req = _get_requisicao_para(request.user, pk)
        return render(
            request,
            "requisicoes/partials/status_badge.html",
            {"requisicao": req},
        )


class CopiarDadosView(SolicitanteRequiredMixin, View):
    """
    Pré-preenchimento de campos a partir de requisição existente. (D-14)

    GET /requisicoes/copiar-dados/?requisicao_origem=<pk>
    Retorna partials/campos_requisicao.html com form inicializado a partir da origem.
    """

    def get(self, request):
        origem_pk = request.GET.get("requisicao_origem")
        if origem_pk:
            # Verificar ownership: Solicitante só pode copiar suas próprias (T-02-04)
            origem = get_object_or_404(
                Requisicao, pk=origem_pk, criado_por=request.user
            )
            # Inicializar form com dados da origem
            initial_data = {
                "descricao": origem.descricao,
                "categoria": origem.categoria,
                "valor_estimado": origem.valor_estimado,
                "justificativa": origem.justificativa,
                "unidade": origem.unidade,
            }
            form = RequisicaoForm(initial=initial_data, user=request.user)
        else:
            form = RequisicaoForm(user=request.user)

        return render(
            request,
            "requisicoes/partials/campos_requisicao.html",
            {"form": form},
        )
