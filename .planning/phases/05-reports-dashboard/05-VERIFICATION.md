---
phase: 05-reports-dashboard
verified: 2026-06-12T12:40:00-03:00
status: human_needed
score: 4/4 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Login como comprador e acessar /relatorios/gastos/ com dados reais"
    expected: "Tabela exibe totais por categoria para o mês corrente; filtros de período e unidade funcionam ao clicar Filtrar"
    why_human: "Requer banco de dados com dados transacionais reais para verificar rendering end-to-end"
  - test: "Clicar 'Exportar PDF' em /relatorios/gastos/"
    expected: "Browser faz download de gastos_por_categoria.pdf; abre como tabela formatada com cabeçalho azul escuro, linhas alternadas, valores formatados como R$ X.XXX,XX"
    why_human: "Qualidade visual do PDF e integridade do download só verificáveis manualmente"
  - test: "Clicar 'Exportar PDF' em /relatorios/requisicoes/"
    expected: "Download de painel_requisicoes.pdf com colunas Descrição, Categoria, Unidade, Valor, Status, Criado em"
    why_human: "Layout tabular do PDF via ReportLab Platypus verificável apenas visualmente"
  - test: "Login como solicitante e tentar acessar /relatorios/gastos/"
    expected: "Recebe HTTP 403 (PermissionDenied); link Relatórios não aparece na sidebar"
    why_human: "Controle de acesso e rendering condicional da nav precisam de sessão ativa"
  - test: "Login como diretor e acessar /relatorios/gastos/"
    expected: "Recebe 200 (não 403); tabela de gastos renderiza; link Relatórios aparece na sidebar"
    why_human: "Verifica que RelatorioRequiredMixin inclui diretor conforme D-02 — precisa de sessão ativa"
  - test: "Login como solicitante e verificar dashboard"
    expected: "KPIs exibem valores filtrados pela unidade padrão do solicitante (não valores globais)"
    why_human: "Requer dados reais na base e sessão ativa do usuário solicitante para comparar com visão global"
---

# Phase 5: Reports & Dashboard — Relatório de Verificação

**Phase Goal:** All roles can view real-time KPIs and spending reports, and export formatted PDFs
**Verified:** 2026-06-12T12:40:00-03:00
**Status:** human_needed
**Re-verification:** Não — verificação inicial

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Dashboard displays live KPIs — open requisitions, active RFQs, current-month spend, and active suppliers — populated from real transaction data | VERIFIED | `apps/core/views.py` injeta `kpis = relatorios_services.get_dashboard_kpis(self.request.user)` via `get_context_data`; template `dashboard.html` renderiza `kpis.req_abertas`, `kpis.cotacoes_andamento`, `kpis.gasto_mes|floatformat:2`, `kpis.fornecedores_ativos`; service implementa queries reais de ORM em `services.py` (linhas 65-100) |
| 2 | Spending report shows totals by category and period, filterable by unit | VERIFIED | `GastosView` em `views.py` delega a `services.get_gastos_por_categoria`; template `gastos.html` contém form GET com `name="data_inicio"`, `name="data_fim"`, `name="unidade"` e tabela iterando `gastos_por_categoria`; service aplica filtros de período e `unidade_id` via ORM |
| 3 | Requisition status panel shows all requisitions with filters for status and unit | VERIFIED | `RequisicoesPainelView` em `views.py` delega a `services.get_requisicoes_painel`; template `requisicoes.html` contém `<select name="status">` populado de `status_choices` e `<select name="unidade">`; service filtra por `status` e `unidade_id` |
| 4 | Any report can be exported as a formatted PDF (ReportLab Platypus layout) directly from the browser | VERIFIED | `pdf.py` implementa `build_gastos_pdf` e `build_requisicoes_pdf` usando `SimpleDocTemplate + Table + TableStyle + Paragraph + KeepTogether`; `GastosPDFView` e `RequisicoesPDFView` retornam `FileResponse(buffer, as_attachment=True)`; endpoints `/relatorios/gastos/pdf/` e `/relatorios/requisicoes/pdf/` registrados em `urls.py` |

**Score:** 4/4 truths verificadas

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `apps/relatorios/__init__.py` | Marcador de pacote Python | VERIFIED | Existe, vazio conforme esperado |
| `apps/relatorios/apps.py` | `RelatoriosConfig` com `name = "apps.relatorios"` | VERIFIED | Linha 4-7: `class RelatoriosConfig(AppConfig)`, `name = "apps.relatorios"`, `verbose_name = "Relatórios"` |
| `apps/relatorios/services.py` | `get_dashboard_kpis`, `get_gastos_por_categoria`, `get_requisicoes_painel` | VERIFIED | 159 linhas; todas 3 funções implementadas com queries ORM reais, fallback `Decimal("0")`, filtro `__month` e `__year` |
| `apps/relatorios/views.py` | `RelatorioRequiredMixin`, `GastosView`, `RequisicoesPainelView`, `GastosPDFView`, `RequisicoesPDFView` | VERIFIED | 183 linhas; todas as classes implementadas; mixin inclui "diretor" explicitamente; stubs 501 removidos |
| `apps/relatorios/urls.py` | `app_name = "relatorios"` + 4 rotas | VERIFIED | 4 rotas: `gastos`, `gastos-pdf`, `requisicoes`, `requisicoes-pdf` |
| `apps/relatorios/pdf.py` | `build_gastos_pdf`, `build_requisicoes_pdf` via ReportLab Platypus | VERIFIED | 151 linhas; importa `SimpleDocTemplate, Table, TableStyle, Paragraph, KeepTogether`; BytesIO in-memory; `buffer.seek(0)` antes de retornar |
| `apps/relatorios/templates/relatorios/gastos.html` | Form filtro GET + tabela gastos | VERIFIED | Contém `name="data_inicio"`, `name="data_fim"`, `name="unidade"`, loop `gastos_por_categoria`, `floatformat:2`, link `relatorios:gastos-pdf` |
| `apps/relatorios/templates/relatorios/requisicoes.html` | Form filtro GET + tabela requisições | VERIFIED | Contém `<select name="status">`, `<select name="unidade">`, loop `requisicoes`, badge, link `relatorios:requisicoes-pdf` |
| `apps/core/views.py` | `DashboardView.get_context_data` injetando KPIs | VERIFIED | 13 linhas; `get_context_data` injeta `ctx["kpis"] = relatorios_services.get_dashboard_kpis(self.request.user)` |
| `apps/core/templates/core/dashboard.html` | 4 cards com valores reais (sem `&mdash;`) | VERIFIED | Contém `kpis.req_abertas`, `kpis.cotacoes_andamento`, `kpis.gasto_mes|floatformat:2`, `kpis.fornecedores_ativos`; sem `&mdash;` |
| `config/settings/base.py` | `"apps.relatorios"` em `INSTALLED_APPS` | VERIFIED | Linha 37: `"apps.relatorios",` após `"apps.cotacoes"` |
| `config/urls.py` | `path("relatorios/", include("apps.relatorios.urls"))` antes do catch-all | VERIFIED | Linha 16, antes de `path("", include("apps.core.urls"))` na linha 17 |
| `templates/base.html` | Link "Relatórios" → `relatorios:gastos` com estado ativo | VERIFIED | Linha 78: `<a href="{% url 'relatorios:gastos' %}"` com `{% if 'relatorios' in request.path %}is-active{% endif %}`; condição inclui comprador, diretor, admin, is_superuser |
| `apps/relatorios/tests/conftest.py` | Fixtures `rfq_com_vencedor`, `diretor_user` | VERIFIED | Ambas as fixtures definidas e implementadas (linhas 58-125) |
| `apps/relatorios/tests/test_services.py` | Classes `TestDashboardKpis`, `TestGastos`, `TestRequisicoesPainel`, `TestFiltroUnidade` | VERIFIED | Todas as 4 classes presentes; testes usam chaves canônicas; verificam `gasto_mes`, `req_abertas`, filtro de unidade |
| `apps/relatorios/tests/test_views.py` | Classes `TestAcesso`, `TestGastosView`, `TestRequisicoesPainelView`, `TestPDF` | VERIFIED | Todas as 4 classes presentes; assertivas contra 200/403 e `Content-Type: application/pdf` |
| `apps/core/tests/test_dashboard.py` | Testes de `DashboardView` com chaves canônicas | VERIFIED | `TestDashboardViewKpis` com 5 testes verificando as 4 chaves canônicas e filtro por unidade do solicitante |

**Nota:** `apps/relatorios/models.py` NÃO existe — correto conforme D-08.

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `apps/core/views.py` | `apps.relatorios.services.get_dashboard_kpis` | import + chamada em `get_context_data` | WIRED | Linha 4: `from apps.relatorios import services as relatorios_services`; linha 12: `relatorios_services.get_dashboard_kpis(self.request.user)` |
| `apps/core/templates/core/dashboard.html` | `kpis` context dict | variáveis de template | WIRED | `kpis.req_abertas`, `kpis.cotacoes_andamento`, `kpis.gasto_mes|floatformat:2`, `kpis.fornecedores_ativos` presentes |
| `config/settings/base.py` | `apps.relatorios` | `INSTALLED_APPS` | WIRED | Linha 37: `"apps.relatorios"` presente |
| `apps/relatorios/views.py` | `apps.relatorios.services.get_gastos_por_categoria` | chamada em `GastosView.get` | WIRED | Linha 110: `dados = services.get_gastos_por_categoria(data_inicio, data_fim, unidade_id)` |
| `apps/relatorios/views.py` | `apps.relatorios.services.get_requisicoes_painel` | chamada em `RequisicoesPainelView.get` | WIRED | Linha 138: `requisicoes = services.get_requisicoes_painel(status, unidade_id)` |
| `config/urls.py` | `apps.relatorios.urls` | `include()` | WIRED | Linha 16: `path("relatorios/", include("apps.relatorios.urls"))` antes do catch-all |
| `apps/relatorios/templates/relatorios/gastos.html` | `relatorios:gastos-pdf` | link Exportar PDF | WIRED | Linha 7: `{% url 'relatorios:gastos-pdf' %}?{{ request.GET.urlencode }}` |
| `apps/relatorios/views.py` | `apps.relatorios.pdf.build_gastos_pdf` | chamada em `GastosPDFView.get` | WIRED | Linha 163: `buffer = pdf.build_gastos_pdf(dados, data_inicio.isoformat(), data_fim.isoformat())` |
| `apps/relatorios/pdf.py` | `reportlab.platypus` | imports | WIRED | Linha 25: `from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Table, TableStyle` |
| `templates/base.html` | `relatorios:gastos` | nav-item href | WIRED | Linha 78: `<a href="{% url 'relatorios:gastos' %}"` |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `dashboard.html` | `kpis` | `services.get_dashboard_kpis(user)` via `DashboardView.get_context_data` | Sim — queries ORM reais: `Requisicao.objects.filter(...)`, `RFQ.objects.filter(...)`, `CotacaoFornecedor.objects.filter(...).aggregate(Sum(...))`, `Fornecedor.objects.filter(ativo=True).count()` | FLOWING |
| `gastos.html` | `gastos_por_categoria` | `services.get_gastos_por_categoria(data_inicio, data_fim, unidade_id)` | Sim — `CotacaoFornecedor.objects.filter(...).values(...).annotate(total=Sum("preco_unitario"))` | FLOWING |
| `requisicoes.html` | `requisicoes` | `services.get_requisicoes_painel(status, unidade_id)` | Sim — `Requisicao.objects.select_related(...).order_by("-criado_em")` com filtros | FLOWING |
| `GastosPDFView` → `build_gastos_pdf` | `dados` | mesmo `get_gastos_por_categoria` da view HTML | Sim — mesmos filtros GET via `_parse_filtros` | FLOWING |
| `RequisicoesPDFView` → `build_requisicoes_pdf` | `requisicoes` | mesmo `get_requisicoes_painel` da view HTML | Sim — mesmos filtros GET | FLOWING |

---

### Behavioral Spot-Checks

Docker não estava em execução durante a verificação. Verificação de comportamento em tempo de execução delegada para Human Verification abaixo.

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Suite de testes completa | `docker compose exec web python manage.py test` | Docker offline | SKIP — ver Human Verification |
| Módulo `services.py` importável | Verificação estática de imports | Sem erros de sintaxe detectados; imports resolvem contra arquivos existentes | PASS (estático) |
| Módulo `pdf.py` usa ReportLab Platypus | Grep `from reportlab.platypus import` | Linha 25 confirma `SimpleDocTemplate, Table, TableStyle, Paragraph, KeepTogether` | PASS (estático) |
| `GastosPDFView` retorna `FileResponse` (não 501) | Grep `status=501` em views.py | Sem correspondência — 501 removido | PASS |

---

### Probe Execution

Não há probes declaradas nos PLANs desta fase. Docker offline — execução de testes delegada para Human Verification.

---

### Requirements Coverage

| Requirement | Plano | Descrição | Status | Evidência |
|-------------|-------|-----------|--------|-----------|
| REL-01 | 05-01 | Dashboard exibe KPIs: requisições abertas, cotações em andamento, gasto do mês e fornecedores ativos | SATISFIED | `DashboardView.get_context_data` + `get_dashboard_kpis` + template com 4 cards reais |
| REL-02 | 05-02 | Relatório de gasto por categoria e período, filtrável por unidade | SATISFIED | `GastosView` + `get_gastos_por_categoria` + `gastos.html` com form filtro e tabela |
| REL-03 | 05-02 | Painel de status de todas as requisições com filtro por status e unidade | SATISFIED | `RequisicoesPainelView` + `get_requisicoes_painel` + `requisicoes.html` com selects de filtro |
| REL-04 | 05-03 | Relatórios podem ser exportados em PDF com layout formatado via ReportLab | SATISFIED | `pdf.py` com `build_gastos_pdf`/`build_requisicoes_pdf`; `GastosPDFView`/`RequisicoesPDFView` com `FileResponse(as_attachment=True)` |
| UNIT-04 | 05-02 | Relatórios podem ser filtrados por unidade | SATISFIED | `get_gastos_por_categoria(unidade_id)` + `get_requisicoes_painel(unidade_id)` + selects de unidade nos templates |

---

### Decisões do Contexto Verificadas

| Decisão | Descrição | Status | Evidência |
|---------|-----------|--------|-----------|
| D-01 | "Gasto do Mês" = `preco_unitario` dos vencedores (não `valor_estimado`) | VERIFIED | `services.py` linha 82-86: `CotacaoFornecedor.objects.filter(rfqs_vencidos__atualizado_em__month=...).aggregate(total=Sum("preco_unitario"))` |
| D-02 | KPIs role-based — solicitante filtra por `user.default_unit` | VERIFIED | `services.py` linhas 57-58: `if user.role == "solicitante" and user.default_unit: filtro_unidade_req = {"unidade": user.default_unit}`; usa `user.default_unit` (não `user.unidade`) |
| D-06 | Dois endpoints PDF: `/relatorios/gastos/pdf/` e `/relatorios/requisicoes/pdf/` | VERIFIED | `urls.py` linhas 16-19 registra ambos; views implementadas |
| D-07 | ReportLab Platypus (SimpleDocTemplate + Table + Paragraph + BytesIO + FileResponse) | VERIFIED | `pdf.py` usa todos esses componentes; nenhuma referência a xhtml2pdf ou WeasyPrint |
| D-08 | App `relatorios` sem models | VERIFIED | `apps/relatorios/models.py` não existe |
| D-09 | `DashboardView` enriquecida (não nova view) | VERIFIED | `apps/core/views.py` tem `get_context_data` na classe existente `DashboardView` |
| RelatorioRequiredMixin inclui diretor | Diretor pode acessar relatórios | VERIFIED | `views.py` linha 52: `request.user.role in ("comprador", "diretor", "admin")` — "diretor" explicitamente incluído |
| Pitfall month+year | Filtro de gasto usa `__month` E `__year` juntos | VERIFIED | `services.py` linhas 83-84: `rfqs_vencidos__atualizado_em__month=mes_atual, rfqs_vencidos__atualizado_em__year=ano_atual` |
| Fallback Decimal("0") | `Sum()` com fallback obrigatório | VERIFIED | `services.py` linha 88: `gasto_mes = resultado["total"] or Decimal("0")` |

---

### Anti-Patterns Found

| Arquivo | Linha | Padrão | Severidade | Impacto |
|---------|-------|--------|------------|---------|
| `apps/relatorios/views.py` | 11-12 | Docstring do módulo ainda menciona "STUB, corpo implementado em 05-03" para GastosPDFView e RequisicoesPDFView | INFO | Documentação desatualizada — as views têm implementação real; não afeta comportamento |

Sem marcadores TBD, FIXME ou XXX nos arquivos da fase. Sem implementações `return null`, `return []` sem justificativa, ou handlers vazios nos arquivos de produção.

---

### Human Verification Required

### 1. Rendering de KPIs reais no dashboard

**Test:** Login como comprador → navegar para `/`
**Expected:** 4 cards exibem números reais (não zero/vazio) se houver dados transacionais; formatação `R$ X.XXX,XX` no card "Gasto do Mês"
**Why human:** Requer banco de dados com dados transacionais reais e sessão autenticada ativa

### 2. Relatório de gastos com filtros ativos

**Test:** Login como comprador → `/relatorios/gastos/` → alterar datas e unidade → clicar Filtrar
**Expected:** Tabela atualiza exibindo apenas gastos do período/unidade selecionados; linha "Nenhum gasto no período." quando sem dados
**Why human:** Comportamento de filtragem e rendering condicional verificável somente com sessão + DB real

### 3. Download do PDF de gastos

**Test:** Login como comprador → `/relatorios/gastos/` → clicar "Exportar PDF"
**Expected:** Browser faz download de `gastos_por_categoria.pdf`; arquivo abre com cabeçalho "Relatório de Gastos por Categoria", tabela com fundo azul `#0f3460` no cabeçalho, linhas alternadas branco/cinza, valores no formato `R$ X.XXX,XX`
**Why human:** Qualidade visual e integridade do PDF verificáveis apenas com abertura real do arquivo

### 4. Download do PDF de requisições

**Test:** Login como comprador → `/relatorios/requisicoes/` → clicar "Exportar PDF"
**Expected:** Download de `painel_requisicoes.pdf` com 6 colunas (Descrição, Categoria, Unidade, Valor, Status, Criado em) e mesmo estilo visual
**Why human:** Layout tabular do PDF verificável apenas com abertura real

### 5. Controle de acesso (403 para solicitante)

**Test:** Login como solicitante → tentar acessar `/relatorios/gastos/`
**Expected:** Recebe HTTP 403; link "Relatórios" não aparece na sidebar
**Why human:** Controle de acesso e rendering condicional da nav requerem sessão ativa

### 6. Acesso do diretor aos relatórios

**Test:** Login como diretor → acessar `/relatorios/gastos/`
**Expected:** Recebe 200; tabela de gastos renderiza; link "Relatórios" aparece na sidebar com estado ativo
**Why human:** Confirma D-02 (diretor incluído em RelatorioRequiredMixin) em sessão real

### 7. Execução da suite de testes completa

**Test:** `docker compose exec web python manage.py test`
**Expected:** Termina com "OK" — zero falhas, zero erros; sem regressão nas fases 1-4
**Why human:** Docker não estava em execução durante a verificação automatizada; requer ambiente Docker ativo

---

### Gaps Summary

Nenhum gap bloqueador identificado. Todos os 4 critérios de sucesso do roadmap foram verificados estaticamente no código. As verificações humanas acima são de comportamento em tempo de execução e qualidade visual que não podem ser confirmadas sem Docker ativo e dados reais.

A nota de docstring desatualizada em `views.py` (linhas 11-12) é informacional — não afeta comportamento.

---

_Verified: 2026-06-12T12:40:00-03:00_
_Verifier: Claude (gsd-verifier)_
