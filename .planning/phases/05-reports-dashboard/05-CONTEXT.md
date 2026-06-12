# Phase 5: Reports & Dashboard - Context

**Gathered:** 2026-06-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Camada de leitura transversal — lê dados de todas as fases anteriores (requisições, cotações, fornecedores, unidades) e os apresenta como KPIs em tempo real no dashboard, relatórios filtráveis por período e unidade, e exportação em PDF via ReportLab. O app `relatorios` não terá models próprios: importa e agrega de todos os outros apps.

**Entrega:** dashboard com KPIs reais, relatório de gasto por categoria, painel de status de requisições com filtros, e exportação PDF dos dois relatórios — funcionando end-to-end para todos os perfis com visibilidade ajustada por role.

</domain>

<decisions>
## Implementation Decisions

### KPI "Gasto do Mês" — base de cálculo (REL-01)

- **D-01:** "Gasto do Mês" = soma dos `CotacaoFornecedor.preco_unitario` dos vencedores selecionados no mês corrente (i.e., `RFQ.vencedor IS NOT NULL` e `RFQ.atualizado_em` dentro do mês). Representa o valor efetivamente comprometido para compra, não a estimativa.
  - Query: `CotacaoFornecedor.objects.filter(rfqs_vencidos__atualizado_em__month=mes_atual).aggregate(total=Sum('preco_unitario'))`

### Dashboard com filtro de unidade (REL-01, UNIT-04)

- **D-02:** KPIs variam por role:
  - `solicitante` → KPIs filtrados pela unidade padrão do usuário (`user.unidade`)
  - `comprador`, `diretor`, `admin` → KPIs globais (todas as unidades)
  - "Requisições Abertas" = status IN [PENDENTE_GESTOR, PENDENTE_DIRETOR] (não inclui RASCUNHO — não está "aberta" no sentido operacional)
  - "Cotações em Andamento" = RFQs sem vencedor (`vencedor_id IS NULL`)
  - "Fornecedores Ativos" = `Fornecedor.objects.filter(ativo=True).count()` — global para todos os roles

### Relatório de Gasto por Categoria (REL-02)

- **D-03:** Período padrão = mês corrente (`date.today().replace(day=1)` até `date.today()`). Usuário pode ajustar via campos `data_inicio` e `data_fim` (inputs HTML `type=date`).
- **D-04:** Filtro de unidade: dropdown `<select>` com todas as unidades + opção "Todas". Comprador/Diretor/Admin veem o filtro; Solicitante tem a unidade pré-fixada na sua.
- **D-05 (Claude's discretion):** Agrega `CotacaoFornecedor.preco_unitario` dos vencedores (preço real) — não `valor_estimado`. Consistente com D-01. Agrupado por `CategoriaCompra` da requisição vinculada à RFQ.

### Exportação PDF (REL-04)

- **D-06:** Dois relatórios exportam PDF:
  1. `/relatorios/gastos/pdf/` — exporta o relatório de gasto por categoria com os mesmos filtros aplicados na visualização web
  2. `/relatorios/requisicoes/pdf/` — exporta o painel de status de requisições com os mesmos filtros

- **D-07 (Claude's discretion):** PDF gerado com ReportLab Platypus (obrigatório — definido pelo cliente). Estrutura: `SimpleDocTemplate` + `Table` + `TableStyle` + `Paragraph`. Resposta HTTP com `Content-Type: application/pdf` e `Content-Disposition: attachment; filename=...`. Filtros passados via GET params para o endpoint PDF.

### Estrutura do App (Claude's discretion)

- **D-08 (Claude's discretion):** Criar app `relatorios` dedicado (`python manage.py startapp relatorios`). Prefixo `/relatorios/`. Sem models. Views importam de `apps.requisicoes`, `apps.cotacoes`, `apps.fornecedores`, `apps.accounts`. Service layer em `apps/relatorios/services.py` centraliza as queries.
- **D-09 (Claude's discretion):** Dashboard (`core:dashboard`) atualizado na `DashboardView` existente — não criar nova view. A view existente em `apps/core/views.py` é enriquecida com KPIs no contexto.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requisitos e Roadmap
- `.planning/REQUIREMENTS.md` §Relatórios — REL-01..04, UNIT-04 (escopo completo da fase)
- `.planning/ROADMAP.md` §Phase 5 — success criteria e dependências (depende de Phases 2, 3, 4)

### Dashboard existente (atualizar, não recriar)
- `apps/core/views.py` — `DashboardView` (TemplateView) — enriquecer com contexto de KPIs
- `apps/core/templates/core/dashboard.html` — 4 cards stub com `—` aguardando dados reais
- `apps/core/urls.py` — rota `core:dashboard` já definida
- `templates/base.html` — nav com link "Relatórios" em `href="#"` — atualizar para URL real

### Modelos fonte de dados (somente leitura — não alterar)
- `apps/requisicoes/models.py` — `Requisicao` com `Status`, `categoria`, `unidade`, `valor_estimado`, `criado_em`
- `apps/cotacoes/models.py` — `RFQ` com `vencedor`, `atualizado_em`; `CotacaoFornecedor` com `preco_unitario`
- `apps/fornecedores/models.py` — `Fornecedor` com `ativo`, `categoria`
- `apps/accounts/models.py` — `User` com `role`, `unidade`; `UnidadeOrganizacional`

### Padrões obrigatórios (fases anteriores)
- `apps/fornecedores/views.py` — `CompradorRequiredMixin` (para restringir relatórios a comprador + admin + diretor)
- `apps/aprovacoes/services.py` — padrão service layer: toda lógica de query em `services.py`
- `CLAUDE.md` §PDF Generation — `SimpleDocTemplate`, `Table`, `TableStyle`, `Paragraph`, `KeepTogether`
- `CLAUDE.md` §HTMX Patterns — Pattern 1 (form com filtros), hx-boost para navegação

### Padrões de tema visual
- `static/css/main.css` — dark theme, classes `.card`, `.card-grid`, `.card-label`, `.card-value`, `.table-container`, `.badge`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DashboardView` (`apps/core/views.py`): TemplateView existente — adicionar `get_context_data()` com KPIs calculados pelo service
- `apps/core/templates/core/dashboard.html`: template stub com 4 cards — substituir `&mdash;` por valores reais do context
- `CompradorRequiredMixin` (`apps/fornecedores/views.py`): reutilizar para restringir acesso às views de relatórios
- `TimestampedModel.criado_em` / `atualizado_em`: campos de data para filtrar por período em todas as queries

### Established Patterns
- **Service layer:** toda lógica de agregação (KPIs, totais por categoria, lista de requisições) em `apps/relatorios/services.py` — views chamam services, nunca fazem queries diretamente
- **DecimalField e Sum:** usar `from django.db.models import Sum` + `aggregate()` para somas monetárias — resultado é `Decimal` ou `None` (tratar com `or Decimal('0')`)
- **PDF via BytesIO:** `buffer = BytesIO(); doc = SimpleDocTemplate(buffer); doc.build(story); buffer.seek(0); return FileResponse(buffer, as_attachment=True, filename='...')`
- **Filtros GET:** params de filtro passados como GET query string — `request.GET.get('data_inicio', default)` — mesmos params na view web e no endpoint PDF

### Integration Points
- `DashboardView.get_context_data()` → chama `services.get_dashboard_kpis(user)` que filtra por role (D-02)
- `GastosView` → chama `services.get_gastos_por_categoria(data_inicio, data_fim, unidade_id)` → retorna lista de dicts `{categoria, total}`
- `RequisicoesPainelView` → chama `services.get_requisicoes_painel(status, unidade_id)` → retorna queryset paginado
- `GastosPDFView` → mesmos params GET → chama `services.get_gastos_por_categoria()` → ReportLab → FileResponse
- Nav `templates/base.html` → atualizar href do link "Relatórios" de `#` para `{% url 'relatorios:gastos' %}`
- `config/urls.py` → adicionar `path("relatorios/", include("apps.relatorios.urls"))`
- `config/settings/base.py` → adicionar `"apps.relatorios"` em `INSTALLED_APPS`

</code_context>

<specifics>
## Specific Ideas

- O card "Gasto do Mês" no dashboard deve exibir o valor formatado como `R$ 12.345,67` — usar filtro `floatformat:2` + separador de milhar.
- KPIs do dashboard não precisam de polling HTMX (os dados mudam raramente em 20 usuários). Carregados sincrono no page load.
- Na nav, o link "Relatórios" deve usar `{% url 'relatorios:gastos' %}` como destino padrão (relatório de gastos é a tela principal de relatórios).
- Painel de requisições (REL-03) deve ter filtro de status via `<select>` simples (HTMX não necessário — submit de form padrão).

</specifics>

<deferred>
## Deferred Ideas

- **Exportação CSV/Excel** — v2 (REL-V2-01)
- **Indicadores de SLA de aprovação** — v2 (REL-V2-02)
- **Comparativo de gasto entre unidades** — v2 (REL-V2-03)
- **Relatório de saving (menor preço vs. selecionado)** — v2 (FORN-V2-02)
- **Polling HTMX no dashboard** — não necessário para 20 usuários (page load síncrono é suficiente)

</deferred>

---

*Phase: 5-Reports-Dashboard*
*Context gathered: 2026-06-11*
