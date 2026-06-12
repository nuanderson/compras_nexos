"""
Service layer para apps/relatorios.

Toda a logica de aggregacao e query cross-app vive aqui — as views delegam a estas
funcoes e nunca contem logica de negocio diretamente (padrao estabelecido em
aprovacoes/services.py e cotacoes/services.py).

Funcoes:
  get_dashboard_kpis        — retorna dict com os 4 KPIs do dashboard, filtrado por role (REL-01, D-01, D-02)
  get_gastos_por_categoria  — retorna lista de gastos reais por categoria no periodo (REL-02, D-05)
  get_requisicoes_painel    — retorna queryset de requisicoes com filtros opcionais (REL-03)

Contrato de chaves (T-05-01 — autoritativo):
  get_dashboard_kpis retorna exatamente:
    {"req_abertas": int, "cotacoes_andamento": int, "gasto_mes": Decimal, "fornecedores_ativos": int}

Seguranca:
  T-05-01  Solicitante sempre filtrado por user.default_unit — nunca ve dados globais (D-02)
  T-05-03  Pitfall 2 — filtros __month e __year sempre juntos para evitar acumulo de anos anteriores
  Pitfall 3 — campo correto e user.default_unit (nunca user.unidade — causaria AttributeError)
  Pitfall 1 — Sum() pode retornar None em queryset vazio; fallback Decimal("0") e obrigatorio
"""
from datetime import date
from decimal import Decimal

from django.db.models import F, Sum

from apps.cotacoes.models import CotacaoFornecedor, RFQ
from apps.fornecedores.models import Fornecedor
from apps.requisicoes.models import Requisicao


def get_dashboard_kpis(user) -> dict:
    """
    Retorna os 4 KPIs do dashboard, filtrados por role do usuario.

    - solicitante: dados filtrados pela unidade padrao do usuario (user.default_unit, D-02)
    - comprador / diretor / admin: dados globais (todas as unidades, D-02)

    Chaves de retorno (contrato T-05-01 — canonico e vinculante):
      req_abertas        — int: requisicoes PENDENTE_GESTOR + PENDENTE_DIRETOR (exclui RASCUNHO)
      cotacoes_andamento — int: RFQs sem vencedor definido (global para todos os roles)
      gasto_mes          — Decimal: soma dos preco_unitario dos vencedores no mes+ano corrente
      fornecedores_ativos — int: fornecedores com ativo=True (global para todos os roles)

    IMPORTANTE: campo correto e user.default_unit (nao user.unidade — causaria AttributeError).
    IMPORTANTE: filtro de gasto usa __month E __year juntos (Pitfall 2 — sem __year acumula anos anteriores).
    IMPORTANTE: fallback Decimal("0") obrigatorio pois Sum() retorna None em queryset vazio (Pitfall 1).
    """
    hoje = date.today()
    mes_atual = hoje.month
    ano_atual = hoje.year

    # Filtro de unidade para solicitante (D-02)
    # Usa user.default_unit — NUNCA user.unidade (Pitfall 3 / campo correto verificado em accounts/models.py linha 44)
    filtro_unidade_req = {}
    if user.role == "solicitante" and user.default_unit:
        filtro_unidade_req = {"unidade": user.default_unit}

    # KPI 1: Requisicoes Abertas = PENDENTE_GESTOR + PENDENTE_DIRETOR (exclui RASCUNHO — D-02)
    estados_abertos = [
        Requisicao.Status.PENDENTE_GESTOR,
        Requisicao.Status.PENDENTE_DIRETOR,
    ]
    req_abertas = Requisicao.objects.filter(
        status__in=estados_abertos,
        **filtro_unidade_req,
    ).count()

    # KPI 2: Cotacoes em Andamento = RFQs sem vencedor (global para todos os roles — D-02)
    cotacoes_andamento = RFQ.objects.filter(vencedor_id__isnull=True).count()

    # KPI 3: Gasto do Mes = soma dos preco_unitario dos vencedores selecionados no mes corrente
    # Filtro de unidade para solicitante (via rfq -> requisicao -> unidade)
    filtro_unidade_gasto = {}
    if user.role == "solicitante" and user.default_unit:
        filtro_unidade_gasto = {
            "rfqs_vencidos__requisicao__unidade": user.default_unit
        }

    # CRITICO — Pitfall 2: usar __month E __year juntos para nao acumular dados de anos anteriores
    resultado = CotacaoFornecedor.objects.filter(
        rfqs_vencidos__atualizado_em__month=mes_atual,
        rfqs_vencidos__atualizado_em__year=ano_atual,
        **filtro_unidade_gasto,
    ).aggregate(total=Sum("preco_unitario"))
    # CRITICO — Pitfall 1: Sum() retorna None em queryset vazio; fallback Decimal("0") obrigatorio
    gasto_mes = resultado["total"] or Decimal("0")

    # KPI 4: Fornecedores Ativos = global para todos os roles (D-02)
    fornecedores_ativos = Fornecedor.objects.filter(ativo=True).count()

    # Retorna dict com as chaves canonicas (contrato T-05-01 — vence RESEARCH.md Pattern 1)
    # NAO usar 'requisicoes_abertas' nem 'cotacoes_em_andamento' (nomes obsoletos do RESEARCH.md)
    return {
        "req_abertas": req_abertas,
        "cotacoes_andamento": cotacoes_andamento,
        "gasto_mes": gasto_mes,
        "fornecedores_ativos": fornecedores_ativos,
    }


def get_gastos_por_categoria(data_inicio, data_fim, unidade_id=None) -> list:
    """
    Retorna lista de dicts com gastos reais por categoria no periodo informado.

    Agrega CotacaoFornecedor.preco_unitario dos vencedores (preco real, nao valor_estimado — D-05).
    Agrupado por CategoriaCompra da requisicao vinculada ao RFQ (chain: CotacaoFornecedor -> RFQ -> Requisicao -> CategoriaCompra).
    Filtro por periodo via atualizado_em do RFQ (data em que o vencedor foi selecionado — D-01).

    Args:
        data_inicio: date — inicio do periodo (inclusive)
        data_fim:    date — fim do periodo (inclusive)
        unidade_id:  int | None — se fornecido, filtra por unidade da requisicao (UNIT-04)

    Retorna:
        list de dicts: [{"categoria_nome": str | None, "total": Decimal}, ...]
        Ordenado por total decrescente.
    """
    qs = CotacaoFornecedor.objects.filter(
        rfqs_vencidos__atualizado_em__date__gte=data_inicio,
        rfqs_vencidos__atualizado_em__date__lte=data_fim,
        rfqs_vencidos__isnull=False,  # apenas cotacoes que sao vencedoras de algum RFQ
    )
    if unidade_id:
        qs = qs.filter(rfqs_vencidos__requisicao__unidade_id=unidade_id)

    return list(
        qs.values(categoria_nome=F("rfqs_vencidos__requisicao__categoria__nome"))
        .annotate(total=Sum("preco_unitario"))
        .order_by("-total")
    )


def get_requisicoes_painel(status=None, unidade_id=None):
    """
    Retorna queryset de requisicoes para o painel de status (REL-03).

    Filtros opcionais: status e unidade_id.
    Ordenado por criado_em decrescente (mais recente primeiro).

    Args:
        status:     str | None — valor de Requisicao.Status para filtrar
        unidade_id: int | None — PK de UnidadeOrganizacional para filtrar (UNIT-04)

    Retorna:
        QuerySet de Requisicao com select_related em categoria, unidade e criado_por.
    """
    qs = Requisicao.objects.select_related(
        "categoria", "unidade", "criado_por"
    ).order_by("-criado_em")

    if status:
        qs = qs.filter(status=status)
    if unidade_id:
        qs = qs.filter(unidade_id=unidade_id)

    return qs
