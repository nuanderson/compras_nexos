"""
Views do app relatorios.

RelatorioRequiredMixin: restringe acesso a comprador, diretor, admin e superuser.
CRITICO: inclui "diretor" explicitamente — diferenca em relacao a CompradorRequiredMixin
(que exclui diretor). Decisao D-02 e nota critica do 05-PATTERNS.md item 1.

Views:
  GastosView             — relatorio de gasto por categoria e periodo (REL-02, D-03, D-04, D-05)
  RequisicoesPainelView  — painel de status de requisicoes com filtros (REL-03, UNIT-04)
  GastosPDFView          — STUB, corpo implementado em 05-03
  RequisicoesPDFView     — STUB, corpo implementado em 05-03

Helper:
  _parse_filtros(request) — extrai e valida data_inicio, data_fim, unidade_id dos GET params
    - Default: data_inicio = primeiro dia do mes corrente, data_fim = hoje (D-03)
    - Validacao com strptime + try/except para bloquear date injection (T-05-04)

Seguranca:
  T-05-04  _parse_filtros valida datas com strptime; input invalido cai no default
  T-05-05  RelatorioRequiredMixin levanta PermissionDenied (403) para solicitante/gestor
  T-05-06  unidade_id passado ao service como string — ORM parametriza (sem SQL injection)
"""
from datetime import date, datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import FileResponse
from django.shortcuts import render
from django.views import View

from apps.accounts.models import UnidadeOrganizacional
from apps.requisicoes.models import Requisicao

from . import pdf, services


class RelatorioRequiredMixin(LoginRequiredMixin):
    """
    Restringe acesso a usuarios com role comprador, diretor, admin ou is_superuser.

    CRITICO: inclui "diretor" — CompradorRequiredMixin nao inclui diretor (D-02, 05-PATTERNS §Critical Notes 1).
    Lanca PermissionDenied (HTTP 403) para solicitante e gestor.
    Referencia: T-05-05.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (
            request.user.is_superuser
            or request.user.role in ("comprador", "diretor", "admin")
        ):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


def _parse_filtros(request):
    """
    Extrai e valida os parametros de filtro de data e unidade do GET request.

    Seguranca — T-05-04: datas validadas com datetime.strptime + try/except.
    Input invalido (date injection, formato incorreto) cai silenciosamente no default
    sem propagar erro ao usuario nem ao ORM.

    Returns:
        tuple: (data_inicio: date, data_fim: date, unidade_id: str | None)
    """
    # Defaults: primeiro dia do mes corrente ate hoje (D-03)
    default_inicio = date.today().replace(day=1)
    default_fim = date.today()

    # Validar data_inicio — T-05-04
    data_inicio_raw = request.GET.get("data_inicio", "")
    if data_inicio_raw:
        try:
            data_inicio = datetime.strptime(data_inicio_raw, "%Y-%m-%d").date()
        except ValueError:
            data_inicio = default_inicio
    else:
        data_inicio = default_inicio

    # Validar data_fim — T-05-04
    data_fim_raw = request.GET.get("data_fim", "")
    if data_fim_raw:
        try:
            data_fim = datetime.strptime(data_fim_raw, "%Y-%m-%d").date()
        except ValueError:
            data_fim = default_fim
    else:
        data_fim = default_fim

    # unidade_id: string vazia convertida para None (ORM parametriza — T-05-06)
    unidade_id = request.GET.get("unidade", "") or None

    return data_inicio, data_fim, unidade_id


class GastosView(RelatorioRequiredMixin, View):
    """
    Relatorio de gastos reais por categoria e periodo filtrado por data e unidade.

    GET: exibe tabela com totais por categoria.
    Filtros via GET params: data_inicio, data_fim, unidade.
    Delega toda a logica de query ao service (REL-02, D-05, UNIT-04).
    """

    def get(self, request):
        data_inicio, data_fim, unidade_id = _parse_filtros(request)
        dados = services.get_gastos_por_categoria(data_inicio, data_fim, unidade_id)

        ctx = {
            # Chave principal usada no template
            "gastos_por_categoria": dados,
            # Alias para compatibilidade com testes existentes (test_views.py verifica "gastos")
            "gastos": dados,
            "data_inicio": data_inicio.isoformat(),
            "data_fim": data_fim.isoformat(),
            "unidades": UnidadeOrganizacional.objects.filter(ativo=True),
            "unidade_selecionada": unidade_id or "",
            "pode_filtrar_unidade": True,
        }
        return render(request, "relatorios/gastos.html", ctx)


class RequisicoesPainelView(RelatorioRequiredMixin, View):
    """
    Painel de status de requisicoes com filtros por status e unidade.

    GET: exibe tabela de requisicoes filtradas.
    Filtros via GET params: status, unidade.
    Delega toda a logica de query ao service (REL-03, UNIT-04).
    """

    def get(self, request):
        status = request.GET.get("status", "") or None
        unidade_id = request.GET.get("unidade", "") or None
        requisicoes = services.get_requisicoes_painel(status, unidade_id)

        ctx = {
            "requisicoes": requisicoes,
            "status_choices": Requisicao.Status.choices,
            "status_selecionado": status or "",
            "unidades": UnidadeOrganizacional.objects.filter(ativo=True),
            "unidade_selecionada": unidade_id or "",
        }
        return render(request, "relatorios/requisicoes.html", ctx)


class GastosPDFView(RelatorioRequiredMixin, View):
    """
    Exporta o relatório de Gastos por Categoria em PDF.

    Reutiliza os mesmos filtros GET da GastosView (_parse_filtros) e o mesmo
    service layer (get_gastos_por_categoria) — D-06, D-07, REL-04.
    Gera o PDF via ReportLab Platypus (pdf.build_gastos_pdf) e serve como
    download com Content-Disposition: attachment (T-05-07, T-05-08, T-05-09).
    """

    def get(self, request):
        data_inicio, data_fim, unidade_id = _parse_filtros(request)
        dados = services.get_gastos_por_categoria(data_inicio, data_fim, unidade_id)
        buffer = pdf.build_gastos_pdf(dados, data_inicio.isoformat(), data_fim.isoformat())
        return FileResponse(buffer, as_attachment=True, filename="gastos_por_categoria.pdf")


class RequisicoesPDFView(RelatorioRequiredMixin, View):
    """
    Exporta o Painel de Status de Requisições em PDF.

    Reutiliza os mesmos filtros GET da RequisicoesPainelView (status, unidade) e
    o mesmo service layer (get_requisicoes_painel) — D-06, D-07, REL-04.
    Gera o PDF via ReportLab Platypus (pdf.build_requisicoes_pdf) e serve como
    download com Content-Disposition: attachment (T-05-07, T-05-08, T-05-09).
    """

    def get(self, request):
        status = request.GET.get("status", "") or None
        unidade_id = request.GET.get("unidade", "") or None
        requisicoes = services.get_requisicoes_painel(status, unidade_id)
        buffer = pdf.build_requisicoes_pdf(requisicoes)
        return FileResponse(buffer, as_attachment=True, filename="painel_requisicoes.pdf")
