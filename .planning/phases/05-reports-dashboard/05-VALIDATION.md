---
phase: 5
slug: reports-dashboard
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-11
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-django |
| **Config file** | `pytest.ini` / `pyproject.toml` |
| **Quick run command** | `docker compose exec web python manage.py test apps/relatorios apps/core` |
| **Full suite command** | `docker compose exec web python manage.py test` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `docker compose exec web python manage.py test apps/relatorios apps/core`
- **After Wave 1:** Full suite — verify no regression in apps/requisicoes, apps/cotacoes, apps/fornecedores

---

## Wave 0 — Scaffold Tests (RED first)

Wave 0 establishes test scaffold before any implementation. Tests must FAIL (RED) when Wave 0 completes — GREEN happens in subsequent waves.

| Test ID | Description | File |
|---------|-------------|------|
| T-05-01 | `DashboardView` returns context with kpi keys: `req_abertas`, `cotacoes_andamento`, `gasto_mes`, `fornecedores_ativos` | `apps/core/tests/test_dashboard.py` |
| T-05-02 | KPI `req_abertas` counts only PENDENTE_GESTOR + PENDENTE_DIRETOR, not RASCUNHO | `apps/core/tests/test_dashboard.py` |
| T-05-03 | KPI `gasto_mes` sums `preco_unitario` of RFQ winners for current month+year only | `apps/relatorios/tests/test_services.py` |
| T-05-04 | `gasto_mes` returns `Decimal('0')` when no winners in current month | `apps/relatorios/tests/test_services.py` |
| T-05-05 | Solicitante KPIs filtered by `user.default_unit`; comprador sees global | `apps/core/tests/test_dashboard.py` |
| T-05-06 | `GastosView` returns 200 with `gastos_por_categoria` in context | `apps/relatorios/tests/test_views.py` |
| T-05-07 | `GastosView` filters by `data_inicio`/`data_fim` GET params | `apps/relatorios/tests/test_views.py` |
| T-05-08 | `RequisicoesPainelView` returns 200 with `requisicoes` in context | `apps/relatorios/tests/test_views.py` |
| T-05-09 | `RequisicoesPainelView` filters by `status` and `unidade_id` GET params | `apps/relatorios/tests/test_views.py` |
| T-05-10 | `GastosPDFView` returns PDF with `Content-Type: application/pdf` | `apps/relatorios/tests/test_views.py` |
| T-05-11 | `RequisicoesPDFView` returns PDF with `Content-Type: application/pdf` | `apps/relatorios/tests/test_views.py` |
| T-05-12 | Relatórios views accessible to comprador, diretor, admin; forbidden to solicitante | `apps/relatorios/tests/test_views.py` |

---

## Dimension Coverage

| Dimension | Status | Notes |
|-----------|--------|-------|
| D1 - Unit tests | planned | T-05-03, T-05-04 (service layer) |
| D2 - Integration tests | planned | T-05-06..12 (views + DB) |
| D3 - Role-based access | planned | T-05-12 |
| D4 - Edge cases | planned | T-05-04 (empty Sum), T-05-02 (status filter) |
| D5 - PDF output | planned | T-05-10, T-05-11 |
| D6 - Filter params | planned | T-05-07, T-05-09 |
| D7 - Cross-role KPI filtering | planned | T-05-05 |
| D8 - Nyquist sampling | planned | after every task commit |
