---
phase: 05-reports-dashboard
plan: "02"
subsystem: relatorios
tags: [views, templates, urls, access-control, filters]
dependency_graph:
  requires: ["05-01"]
  provides: ["05-03"]
  affects: ["config/urls.py", "templates/base.html"]
tech_stack:
  added: []
  patterns:
    - RelatorioRequiredMixin com role incluindo diretor
    - _parse_filtros helper com validacao strptime + try/except
    - GET form submit para filtros (sem HTMX — form padrao)
    - Template floatformat:2 para valores monetarios BR
key_files:
  created:
    - apps/relatorios/views.py
    - apps/relatorios/urls.py
    - apps/relatorios/templates/relatorios/gastos.html
    - apps/relatorios/templates/relatorios/requisicoes.html
  modified:
    - config/urls.py
    - templates/base.html
decisions:
  - "RelatorioRequiredMixin criado independente de CompradorRequiredMixin para incluir role 'diretor' (D-02, Critical Note 1)"
  - "Alias 'gastos' adicionado ao contexto de GastosView para satisfazer teste existente que verifica 'gastos' in context"
  - "Link 'Relatorios' no base.html atualizado de '#' para url 'relatorios:gastos' com is-active (05-CONTEXT Specifics)"
metrics:
  duration: "~15 min"
  completed: "2026-06-12"
  tasks_completed: 3
  tasks_total: 3
  files_created: 4
  files_modified: 2
requirements: [REL-02, REL-03, UNIT-04]
---

# Phase 05 Plan 02: Views HTML de Relatórios com Filtros GET Summary

**One-liner:** Views `GastosView` e `RequisicoesPainelView` com `RelatorioRequiredMixin` (inclui diretor), helper `_parse_filtros` com proteção a date injection, 4 URLs registradas e templates com formulários de filtro GET e exportação PDF.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | RelatorioRequiredMixin + views + stubs PDF | `f75b1c5` | apps/relatorios/views.py (criado) |
| 2 | URLs do app + wiring config/urls.py | `c151c5a` | apps/relatorios/urls.py (criado), config/urls.py |
| 3 | Templates gastos.html e requisicoes.html | `767ed12` | templates criados, base.html atualizado |

## What Was Built

### RelatorioRequiredMixin (`apps/relatorios/views.py`)
Mixin de controle de acesso que inclui `"diretor"` na lista de roles permitidos — diferença crítica em relação ao `CompradorRequiredMixin` (que exclui diretor). Lança `PermissionDenied` (403) para `solicitante` e `gestor`.

### `_parse_filtros(request)`
Helper que extrai `data_inicio`, `data_fim` e `unidade_id` dos GET params:
- Default: `date.today().replace(day=1)` a `date.today()` (D-03)
- Validação com `datetime.strptime(..., "%Y-%m-%d")` em `try/except ValueError` — input inválido cai no default sem propagar erro (T-05-04)

### GastosView + RequisicoesPainelView
Views que delegam 100% da lógica de query ao service layer (`services.get_gastos_por_categoria` e `services.get_requisicoes_painel`). Nenhuma query ORM de negócio nas views — apenas `UnidadeOrganizacional.objects.filter(ativo=True)` para popular o `<select>`.

### GastosPDFView + RequisicoesPDFView (stubs)
Retornam HTTP 501 com comentário explícito indicando implementação em 05-03. Existem para destravar o registro de URLs em `urls.py`.

### URLs do app (`apps/relatorios/urls.py`)
4 rotas com `app_name = "relatorios"`: `gastos`, `gastos-pdf`, `requisicoes`, `requisicoes-pdf`. Inseridas em `config/urls.py` imediatamente antes do catch-all `core.urls`.

### Templates com filtros GET
- `gastos.html`: form com `data_inicio`, `data_fim`, `<select name="unidade">` sob `{% if pode_filtrar_unidade %}`, tabela com `floatformat:2`, link PDF com `request.GET.urlencode`
- `requisicoes.html`: form com `<select name="status">` populado de `status_choices`, `<select name="unidade">`, tabela com 6 colunas, link PDF com `request.GET.urlencode`

### Nav atualizada (`templates/base.html`)
Link "Relatórios" alterado de `href="#"` para `{% url 'relatorios:gastos' %}` com classe `is-active` quando em `/relatorios/`.

## Test Results

| Suite | Status | Observação |
|-------|--------|-----------|
| TestAcesso (4 testes) | GREEN | 403 solicitante, 200 comprador/diretor/admin |
| TestGastosView (3 testes) | GREEN | 200, filtros data, gastos no contexto |
| TestRequisicoesPainel (2 testes) | GREEN | 200, filtro status |
| TestPDF (3 testes) | RED intencional | Aguarda implementação em 05-03 |
| Demais suites (fases 1-4) | GREEN | Zero regressão |

## Deviations from Plan

### Auto-added: alias "gastos" no contexto de GastosView

**Found during:** Task 3 — ao analisar o teste existente `test_gastos_contexto_contem_dados`
**Issue:** O plano especifica a chave `gastos_por_categoria` no contexto, mas o teste criado em 05-01 verifica `"gastos" in response.context` (linha 108 de `test_views.py`).
**Fix:** GastosView passa ambas as chaves no contexto — `gastos_por_categoria` (usada pelo template) e `gastos` (alias para satisfazer o teste). Ambas apontam para o mesmo objeto.
**Files modified:** `apps/relatorios/views.py`
**Rule:** Rule 1 (auto-fix bug — inconsistência entre plano e teste existente)

### Auto-added: atualização do link "Relatórios" no base.html

**Found during:** Task 3
**Issue:** 05-CONTEXT.md §Specifics especifica que o link "Relatórios" no nav deve usar `{% url 'relatorios:gastos' %}` como destino — estava em `href="#"`.
**Fix:** Link atualizado com URL real e classe `is-active` para `'relatorios' in request.path`.
**Files modified:** `templates/base.html`
**Rule:** Rule 2 (auto-add missing critical functionality — nav inoperante impede navegação)

## Known Stubs

| Stub | File | Reason |
|------|------|--------|
| `GastosPDFView.get` retorna HTTP 501 | `apps/relatorios/views.py` | Corpo PDF implementado em 05-03 |
| `RequisicoesPDFView.get` retorna HTTP 501 | `apps/relatorios/views.py` | Corpo PDF implementado em 05-03 |

Os stubs são intencionais — existem para destravar o registro de URLs. O plano 05-03 substituirá os métodos `get` com a implementação ReportLab real.

## Threat Flags

Nenhuma superfície de segurança nova além do documentado no `<threat_model>` do plano.

- T-05-04 (date injection): mitigado via `strptime` + `try/except` em `_parse_filtros`
- T-05-05 (elevation of privilege): mitigado via `PermissionDenied` em `RelatorioRequiredMixin`
- T-05-06 (ORM injection): mitigado — `unidade_id` e `status` passados ao ORM via parâmetros nomeados

## Self-Check: PASSED

| Item | Status |
|------|--------|
| apps/relatorios/views.py | FOUND |
| apps/relatorios/urls.py | FOUND |
| apps/relatorios/templates/relatorios/gastos.html | FOUND |
| apps/relatorios/templates/relatorios/requisicoes.html | FOUND |
| Commit f75b1c5 | FOUND |
| Commit c151c5a | FOUND |
| Commit 767ed12 | FOUND |
