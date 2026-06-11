"""
Views do app cotacoes.

Reutiliza CompradorRequiredMixin de apps.fornecedores.views (D-05).
Toda lógica de negócio delegada a services.py (padrão da fase).

Referências:
  COT-01  criar RFQ vinculado a requisição aprovada
  COT-02  adicionar/remover cotações de fornecedores com HX-Redirect (D-10)
  COT-03  comparativo de preços injetado no contexto (D-09)
  COT-04  seleção de vencedor com justificativa obrigatória (D-07/D-08)
  T-04-01 CompradorRequiredMixin → 403 para Solicitante/Gestor/Diretor
  T-04-02 IntegrityError capturado → re-render com status=409
  T-04-03 Guard rfq.tem_vencedor → 403/409 em add/remove/selecionar
  T-04-05 selecionar_vencedor usa select_for_update no service
  T-04-06 except ValueError → 409 quando vencedor já definido ou justificativa vazia
  D-05    CompradorRequiredMixin importado de apps.fornecedores.views
  D-06    OneToOneField → IntegrityError sinaliza duplicata
  D-10    HX-Redirect após add/remove mantém deltas consistentes (evita Pitfall 2)
"""
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from django_htmx.http import HttpResponseClientRedirect

from apps.fornecedores.views import CompradorRequiredMixin

from . import services
from .forms import CotacaoFornecedorForm, RFQForm
from .models import CotacaoFornecedor, RFQ


class ListaRFQView(CompradorRequiredMixin, View):
    """
    Hub /cotacoes/ — lista todos os RFQs ordenados por -criado_em.

    Status derivado de rfq.status_display (Em andamento / Encerrado).
    """

    def get(self, request):
        rfqs = RFQ.objects.select_related("requisicao", "vencedor").order_by("-criado_em")
        return render(request, "cotacoes/rfq_list.html", {"rfqs": rfqs})


class NovaRFQView(CompradorRequiredMixin, View):
    """
    Criação de RFQ via select de requisição aprovada sem RFQ.

    GET: formulário com queryset filtrado (APROVADO + rfq__isnull=True).
    POST: delega a services.criar_rfq; captura IntegrityError → 409 (T-04-02).
    """

    def get(self, request):
        form = RFQForm()
        return render(request, "cotacoes/rfq_form.html", {"form": form})

    def post(self, request):
        form = RFQForm(request.POST)
        if form.is_valid():
            try:
                rfq = services.criar_rfq(
                    form.cleaned_data["requisicao"].pk,
                    request.user,
                )
                return redirect("cotacoes:detalhe", pk=rfq.pk)
            except IntegrityError:
                # T-04-02: unicidade violada → mensagem inline, status 409
                form.add_error(
                    "requisicao",
                    "Já existe uma cotação para esta requisição.",
                )
                return render(
                    request,
                    "cotacoes/rfq_form.html",
                    {"form": form},
                    status=409,
                )
        return render(request, "cotacoes/rfq_form.html", {"form": form})


class DetalheRFQView(CompradorRequiredMixin, View):
    """
    Detalhe do RFQ — cabeçalho + dados da requisição + tabela comparativa.

    Injeta comparativo (COT-03, D-09) e form de adição de cotação (COT-02).
    T-04-IDOR: RFQ global para Compradores (sem isolamento por usuário — RESEARCH §Security).
    """

    def get(self, request, pk):
        rfq = get_object_or_404(
            RFQ.objects.select_related("requisicao", "vencedor__fornecedor"),
            pk=pk,
        )
        comparativo = services.calcular_comparativo(rfq)
        form = CotacaoFornecedorForm()
        return render(request, "cotacoes/rfq_detail.html", {
            "rfq": rfq,
            "comparativo": comparativo,
            "form": form,
        })


class AdicionarCotacaoView(CompradorRequiredMixin, View):
    """
    POST: adiciona CotacaoFornecedor ao RFQ. Responde com HX-Redirect (D-10).

    Guard rfq.tem_vencedor → 403 (T-04-03, D-08).
    Formulário inválido → re-render com status=422.
    HX-Redirect mantém deltas consistentes após adição (Pitfall 2).
    """

    def post(self, request, rfq_pk):
        rfq = get_object_or_404(RFQ, pk=rfq_pk)

        # Guard T-04-03: RFQ encerrado bloqueia novas cotações (D-08)
        if rfq.tem_vencedor:
            return HttpResponse("RFQ encerrado.", status=403)

        form = CotacaoFornecedorForm(request.POST)
        if form.is_valid():
            services.adicionar_cotacao(rfq, form.cleaned_data)
            # D-10: HX-Redirect recarrega página inteira para deltas consistentes (Pitfall 2)
            return HttpResponseClientRedirect(
                reverse("cotacoes:detalhe", args=[rfq.pk])
            )
        # Formulário inválido: re-render com erros e status 422
        comparativo = services.calcular_comparativo(rfq)
        return render(
            request,
            "cotacoes/rfq_detail.html",
            {"rfq": rfq, "comparativo": comparativo, "form": form},
            status=422,
        )


class RemoverCotacaoView(CompradorRequiredMixin, View):
    """
    POST: remove CotacaoFornecedor do RFQ. Responde com HX-Redirect (D-10).

    Guard rfq.tem_vencedor → 403 (T-04-03, D-08).
    """

    def post(self, request, rfq_pk, cotacao_pk):
        rfq = get_object_or_404(RFQ, pk=rfq_pk)

        # Guard T-04-03: RFQ encerrado bloqueia remoção (D-08)
        if rfq.tem_vencedor:
            return HttpResponse("RFQ encerrado.", status=403)

        services.remover_cotacao(rfq, cotacao_pk)
        # D-10: HX-Redirect recarrega página inteira para deltas consistentes
        return HttpResponseClientRedirect(
            reverse("cotacoes:detalhe", args=[rfq.pk])
        )


class ModalSelecionarVencedorView(CompradorRequiredMixin, View):
    """
    GET: retorna partial do modal de seleção de vencedor.

    Guard rfq.tem_vencedor → 409 (T-04-03 — vencedor imutável, D-07).
    """

    def get(self, request, rfq_pk, cotacao_pk):
        rfq = get_object_or_404(RFQ, pk=rfq_pk)

        # Guard T-04-03: vencedor já definido → 409
        if rfq.tem_vencedor:
            return HttpResponse("Vencedor já definido.", status=409)

        cotacao = get_object_or_404(CotacaoFornecedor, pk=cotacao_pk, rfq=rfq)
        return render(
            request,
            "cotacoes/partials/modal_selecionar.html",
            {"rfq": rfq, "cotacao": cotacao},
        )


class SelecionarVencedorView(CompradorRequiredMixin, View):
    """
    POST: seleciona vencedor do RFQ com justificativa obrigatória (COT-04, D-07).

    Delega a services.selecionar_vencedor (select_for_update, T-04-05).
    ValueError → 409 quando vencedor já definido ou justificativa vazia (T-04-06).
    Sucesso → HX-Redirect para detalhe.
    """

    def post(self, request, rfq_pk, cotacao_pk):
        justificativa = request.POST.get("justificativa", "")
        try:
            services.selecionar_vencedor(rfq_pk, cotacao_pk, justificativa, request.user)
        except ValueError as e:
            # T-04-06: justificativa vazia ou vencedor já definido → 409
            return HttpResponse(str(e), status=409)
        # Sucesso: HX-Redirect para página de detalhe
        return HttpResponseClientRedirect(
            reverse("cotacoes:detalhe", args=[rfq_pk])
        )
