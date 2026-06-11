---
phase: "04-quotations-rfq"
plan: "01"
subsystem: "cotacoes"
tags: [models, services, tdd, rfq, migrations]
dependency_graph:
  requires: [apps.requisicoes.models.Requisicao, apps.fornecedores.models.Fornecedor, apps.core.models.TimestampedModel]
  provides: [apps.cotacoes.models.RFQ, apps.cotacoes.models.CotacaoFornecedor, apps.cotacoes.services]
  affects: [config/settings/base.py, apps/cotacoes/migrations]
tech_stack:
  added: []
  patterns: [select_for_update + transaction.atomic, MinValueValidator, OneToOneField unicidade, TDD RED/GREEN]
key_files:
  created:
    - apps/cotacoes/__init__.py
    - apps/cotacoes/apps.py
    - apps/cotacoes/models.py
    - apps/cotacoes/services.py
    - apps/cotacoes/admin.py
    - apps/cotacoes/migrations/__init__.py
    - apps/cotacoes/migrations/0001_initial.py
    - apps/cotacoes/tests/__init__.py
    - apps/cotacoes/tests/conftest.py
    - apps/cotacoes/tests/test_models.py
    - apps/cotacoes/tests/test_services.py
    - apps/cotacoes/tests/test_views.py
    - apps/fornecedores/migrations/0002_remove_fornecedor_fornecedor_ativo_idx_and_more.py
  modified:
    - config/settings/base.py
decisions:
  - "OneToOneField RFQ→Requisicao garante unicidade no DB; IntegrityError propaga para a view capturar (D-06)"
  - "MinValueValidator(0.01) no model + guard `menor > 0` no service evitam ZeroDivisionError (T-04-04)"
  - "selecionar_vencedor valida justificativa antes de abrir transaction.atomic (padrão reprovar_requisicao)"
  - "Testes de view marcados @pytest.mark.skip — conectados nos planos 02/03"
  - "fornecedores/0002 incluído para corrigir drift entre migration 0001 (com indexes) e model atual (sem indexes)"
metrics:
  duration: "~20 minutos"
  completed_date: "2026-06-11"
  tasks_completed: 3
  files_created: 13
  files_modified: 1
---

# Phase 04 Plan 01: Cotacoes — Modelos, Migração e Service Layer

**One-liner:** App `apps/cotacoes` com modelos RFQ (OneToOneField) e CotacaoFornecedor (DecimalField + MinValueValidator), migração 0001, service layer com select_for_update para imutabilidade do vencedor, e suite de testes Wave 0 (17 testes GREEN, 8 skips para views futuras).

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Scaffold Wave 0 — conftest + stubs RED | 22e2021 | conftest.py, test_models.py, test_services.py, test_views.py |
| 2 | Modelos RFQ + CotacaoFornecedor, migração, admin, INSTALLED_APPS | 0fb1d0d | models.py, apps.py, admin.py, 0001_initial.py, base.py |
| 3 | Service layer — criar_rfq, calcular_comparativo, selecionar_vencedor | 1b57d12 | services.py |

---

## Decisions Made

1. **OneToOneField RFQ→Requisicao:** Um RFQ por Requisicao, enforçado no banco. IntegrityError propaga para a view capturar (D-06).
2. **MinValueValidator(0.01) + guard `menor > 0`:** Dupla proteção contra ZeroDivisionError em `calcular_comparativo`. O validator protege formulários; o guard protege inserções diretas no banco (T-04-04).
3. **Validação antes da transação em `selecionar_vencedor`:** Mesma estrutura de `reprovar_requisicao` — justificativa vazia levanta ValueError antes de abrir `transaction.atomic()` (defense in depth).
4. **Testes de view com `@pytest.mark.skip`:** Os testes de view existem como contratos futuros; planos 02 e 03 removem os skips ao conectar as views.
5. **`fornecedores/0002`:** Migration gerada automaticamente para corrigir drift pré-existente (indexes em 0001 sem correspondência no model atual). Incluída para manter estado consistente.

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ValueError message mismatch no TestVencedorImutavel**
- **Found during:** Task 3, primeira execução dos testes
- **Issue:** O teste usava `match="Vencedor já foi definido"` (com acento) e o service havia sido escrito sem acento (`"Vencedor ja foi definido"`).
- **Fix:** Atualizado `services.py` para usar `"Vencedor já foi definido para este RFQ."` com acento correto.
- **Files modified:** `apps/cotacoes/services.py`
- **Commit:** 1b57d12 (corrigido antes do commit final)

### Out-of-Scope Discoveries

**Drift em `apps/fornecedores/migrations/`:** A migration 0001 dos fornecedores adicionava dois indexes (`fornecedor_ativo_idx`, `fornecedor_categoria_idx`) que não existem mais no modelo atual. Ao rodar `makemigrations`, o Django gerou automaticamente a migration 0002 para remover esses indexes. Incluída no commit da Task 2 para manter consistência.

---

## Test Results

```
apps/cotacoes/tests/test_models.py   ......    (6 passed)
apps/cotacoes/tests/test_services.py ...........  (11 passed)
apps/cotacoes/tests/test_views.py    ssssssss  (8 skipped — planos 02/03)

Total: 17 passed, 8 skipped
```

---

## Verification

- `python manage.py makemigrations cotacoes --check --dry-run` — "No changes detected" ✓
- `python -m pytest apps/cotacoes/ -q` — 17 passed, 8 skipped ✓
- `apps/cotacoes/models.py` contém `class RFQ(` e `OneToOneField` ✓
- `apps/cotacoes/models.py` contém `MinValueValidator(Decimal("0.01"))` ✓
- `config/settings/base.py` contém `"apps.cotacoes"` ✓
- `apps/cotacoes/services.py` contém `def selecionar_vencedor` e `select_for_update` ✓
- `apps/cotacoes/services.py` contém `def calcular_comparativo` e `menor > 0` ✓

---

## Known Stubs

Nenhum stub que impeça o objetivo do plano. Os testes de view marcados com `@pytest.mark.skip` são stubs intencionais — serão conectados nos planos 02 e 03 quando as views existirem.

---

## Threat Flags

Nenhuma nova superfície de segurança além do declarado no `<threat_model>` do plano.

---

## Self-Check: PASSED

- apps/cotacoes/models.py: FOUND
- apps/cotacoes/services.py: FOUND
- apps/cotacoes/migrations/0001_initial.py: FOUND
- apps/cotacoes/tests/conftest.py: FOUND
- Commit 22e2021: FOUND
- Commit 0fb1d0d: FOUND
- Commit 1b57d12: FOUND
