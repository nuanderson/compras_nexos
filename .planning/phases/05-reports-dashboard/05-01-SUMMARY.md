---
phase: 05-reports-dashboard
plan: "01"
subsystem: relatorios
tags: [relatorios, dashboard, kpis, service-layer, tdd, wave-0]
dependency_graph:
  requires: [apps.cotacoes, apps.requisicoes, apps.fornecedores, apps.accounts]
  provides: [apps.relatorios, get_dashboard_kpis, get_gastos_por_categoria, get_requisicoes_painel, DashboardView.get_context_data]
  affects: [apps.core.views, apps.core.templates.core.dashboard, config.settings.base]
tech_stack:
  added: []
  patterns: [service-layer, TDD-wave-0, cross-app-aggregation, Django-TemplateView-get_context_data]
key_files:
  created:
    - apps/relatorios/__init__.py
    - apps/relatorios/apps.py
    - apps/relatorios/services.py
    - apps/relatorios/tests/__init__.py
    - apps/relatorios/tests/conftest.py
    - apps/relatorios/tests/test_services.py
    - apps/relatorios/tests/test_views.py
    - apps/core/tests/__init__.py
    - apps/core/tests/test_dashboard.py
  modified:
    - config/settings/base.py
    - apps/core/views.py
    - apps/core/templates/core/dashboard.html
decisions:
  - "Chaves canônicas do dict get_dashboard_kpis: req_abertas, cotacoes_andamento, gasto_mes, fornecedores_ativos (contrato T-05-01 — vence RESEARCH.md Pattern 1)"
  - "user.default_unit (não user.unidade) para filtrar KPIs por unidade do solicitante (Pitfall 3)"
  - "Filtro gasto_mes usa __month E __year juntos para evitar acúmulo de anos anteriores (Pitfall 2)"
  - "Fallback Decimal('0') obrigatório após Sum() pois retorna None em queryset vazio (Pitfall 1)"
  - "test_views.py RED intencional (Wave 0) — views /relatorios/* implementadas no plano 05-02"
metrics:
  duration: "~15 min"
  completed: "2026-06-12T02:56:46Z"
  tasks_completed: 3
  tasks_total: 3
  files_created: 9
  files_modified: 3
---

# Phase 05 Plan 01: Scaffold do App Relatorios + Service Layer + Dashboard KPIs Summary

**One-liner:** App `relatorios` registrado, service layer com 3 funções de query (filtro por role/unidade + Decimal fallback + month+year guard), dashboard exibindo 4 KPIs reais com 18 testes GREEN e 12 testes RED intencional (Wave 0).

## Tasks Completed

| Task | Name | Commit | Arquivos Principais |
|------|------|--------|---------------------|
| 1 | Scaffold do app relatorios + registro em INSTALLED_APPS | 44bb692 | apps/relatorios/__init__.py, apps.py, tests/__init__.py, settings/base.py |
| 2 | Service layer — get_dashboard_kpis, get_gastos_por_categoria, get_requisicoes_painel | 2f7b8d4 | apps/relatorios/services.py |
| 3 | Scaffold de testes Wave 0 (RED) + enriquecer DashboardView e template | 7293ceb | tests/conftest.py, test_services.py, test_views.py, test_dashboard.py, core/views.py, dashboard.html |

## Verification Results

- `manage.py check` — Sistema sem issues (0 silenciados)
- `pytest apps/relatorios/tests/test_services.py apps/core/tests/test_dashboard.py` — **18 passed** (GREEN)
- `pytest apps/relatorios/tests/test_views.py` — **12 failed** (RED intencional — Wave 0; views criadas no plano 05-02)
- `pytest apps/requisicoes/ apps/cotacoes/ apps/fornecedores/ apps/accounts/` — **103 passed** (sem regressão)

## Deviations from Plan

None — plano executado exatamente como escrito.

## TDD Gate Compliance

Task 3 seguiu o ciclo RED/GREEN:

1. **RED gate:** Testes de test_views.py criados primeiro — confirmado 12 falhas (404 para URLs inexistentes)
2. **GREEN gate:** DashboardView.get_context_data() implementada + dashboard.html atualizado — 5 testes test_dashboard.py passando
3. **test_services.py** já passou GREEN imediatamente pois services.py (Task 2) estava implementado antes dos testes

## Key Decisions Made

1. **Contrato de chaves KPI (T-05-01 autoritativo):** `req_abertas`, `cotacoes_andamento`, `gasto_mes`, `fornecedores_ativos` — vence os nomes obsoletos `requisicoes_abertas`/`cotacoes_em_andamento` do RESEARCH.md Pattern 1. Aplicado consistentemente em services.py, views.py, dashboard.html e todos os arquivos de teste.

2. **Filtro month+year obrigatório (Pitfall 2):** A query `CotacaoFornecedor.objects.filter(rfqs_vencidos__atualizado_em__month=mes_atual, rfqs_vencidos__atualizado_em__year=ano_atual)` — sem o `__year`, o sistema acumularia dados do mesmo mês de anos anteriores em produção.

3. **user.default_unit (Pitfall 3):** Campo correto verificado em accounts/models.py linha 44. Código usa `user.default_unit` em todos os pontos — nunca `user.unidade` (causaria AttributeError).

4. **Fallback Decimal("0") (Pitfall 1):** `resultado["total"] or Decimal("0")` aplicado em toda query `aggregate(total=Sum(...))` — Sum() retorna None em queryset vazio.

5. **Wave 0 RED intencional:** test_views.py criado com testes que batem em URLs `/relatorios/*` inexistentes. Isso é o scaffold de Wave 0 — GREEN vem no plano 05-02 (views) e 05-03 (PDF). Cada classe de teste documenta esse comportamento no docstring.

## Known Stubs

Nenhum stub que impeça o objetivo do plano. O dashboard exibe KPIs reais (não mais `&mdash;`). As views de relatório (`/relatorios/gastos/`, `/relatorios/requisicoes/`) são intencionalmente adiadas para o plano 05-02 — isso é planejado, não um stub acidental.

## Threat Flags

Nenhuma superfície nova de segurança além do previsto no threat model do plano:
- `DashboardView` já tinha `LoginRequiredMixin` — mantido
- `get_dashboard_kpis` filtra por `user.default_unit` quando `user.role == "solicitante"` — mitigation T-05-01 aplicada
- Nenhum endpoint novo exposto (views do app relatorios serão no plano 05-02)

## Self-Check: PASSED

Todos os 12 arquivos criados/modificados verificados como presentes no filesystem.
Todos os 3 commits (44bb692, 2f7b8d4, 7293ceb) verificados como existentes no repositório git.
