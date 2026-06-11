"""
Views do app cotacoes.

Reutiliza CompradorRequiredMixin de apps.fornecedores.views (D-05).
Toda lógica de negócio delegada a services.py (padrão da fase).

Referências:
  COT-01  criar RFQ vinculado a requisição aprovada
  T-04-01 CompradorRequiredMixin → 403 para Solicitante/Gestor/Diretor
  T-04-02 IntegrityError capturado → re-render com status=409
  D-05    CompradorRequiredMixin importado de apps.fornecedores.views
  D-06    OneToOneField → IntegrityError sinaliza duplicata
"""
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.fornecedores.views import CompradorRequiredMixin

from . import services
from .forms import RFQForm
from .models import RFQ


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
    Detalhe do RFQ — cabeçalho + dados da requisição.

    O comparativo de preços (tabela e form de adição) é inserido no plano 03.
    T-04-IDOR: RFQ global para Compradores (sem isolamento por usuário — RESEARCH §Security).
    """

    def get(self, request, pk):
        rfq = get_object_or_404(
            RFQ.objects.select_related("requisicao", "vencedor__fornecedor"),
            pk=pk,
        )
        return render(request, "cotacoes/rfq_detail.html", {"rfq": rfq})
