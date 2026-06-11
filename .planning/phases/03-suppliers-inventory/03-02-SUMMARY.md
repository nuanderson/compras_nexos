---
phase: "03"
plan: "02"
subsystem: estoque
tags: [estoque, inventory, models, views, htmx, security, tdd]
dependency_graph:
  requires:
    - apps/core/models.py (TimestampedModel)
    - apps/accounts/models.py (User.Role, UnidadeOrganizacional)
  provides:
    - apps/estoque/models.py (UnidadeMedida, ItemEstoque)
    - apps/estoque/views.py (ListaEstoqueView, CadastrarItemEstoqueView, EditarItemEstoqueView, AtualizarQuantidadeView, VisaoConsolidadaView)
    - apps/estoque/urls.py (namespace=estoque)
    - templates/estoque/ (lista, form, atualizar_quantidade, visao_consolidada, partials/item_row)
  affects:
    - config/settings/base.py (INSTALLED_APPS)
    - config/urls.py (estoque/ path)
tech_stack:
  added: []
  patterns:
    - select_for_update + transaction.atomic para atualizações concorrentes
    - UniqueConstraint (não unique_together) para restrição nome+unidade
    - IDOR guard com get_object_or_404(filtro unidade_organizacional)
    - PermissionDenied para isolamento de role em visão consolidada
    - apps.get_model() em migration RunPython (não import direto)
key_files:
  created:
    - apps/estoque/models.py
    - apps/estoque/forms.py
    - apps/estoque/views.py
    - apps/estoque/urls.py
    - apps/estoque/admin.py
    - apps/estoque/apps.py
    - apps/estoque/migrations/0001_initial.py
    - apps/estoque/migrations/0002_seed_unidades.py
    - apps/estoque/tests/conftest.py
    - apps/estoque/tests/test_models.py
    - apps/estoque/tests/test_forms.py
    - apps/estoque/tests/test_views.py
    - templates/estoque/lista.html
    - templates/estoque/form.html
    - templates/estoque/atualizar_quantidade.html
    - templates/estoque/visao_consolidada.html
    - templates/estoque/partials/item_row.html
  modified:
    - config/settings/base.py (apps.estoque em INSTALLED_APPS)
    - config/urls.py (path estoque/)
decisions:
  - "UniqueConstraint(fields=[nome, unidade_organizacional]) — nunca unique_together (deprecated)"
  - "select_for_update() dentro de transaction.atomic() em AtualizarQuantidadeView (D-05)"
  - "unidade_organizacional atribuída por request.user.default_unit — nunca pelo form (T-03-09)"
  - "PermissionDenied (não 404) em VisaoConsolidadaView para Solicitante/Gestor/Diretor (T-03-06)"
  - "apps.get_model() em migration seed — nunca import direto do model"
metrics:
  duration: "~35 minutos"
  completed_date: "2026-06-11T14:52:42Z"
  tasks_completed: 2
  files_created: 19
  files_modified: 2
  tests_added: 25
  tests_passing: 25
---

# Phase 03 Plan 02: App Estoque — Modelos, Views e Isolamento de Unidade

**One-liner:** App `estoque` completo com UnidadeMedida configurável, ItemEstoque isolado por unidade organizacional, visão consolidada para Comprador/Admin, e atualização de quantidade via `select_for_update()`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Testes falhos — models e forms | b740a82 | tests/conftest.py, test_models.py, test_forms.py |
| 1 (GREEN) | Scaffold do app estoque | 8cb2383 | models.py, forms.py, admin.py, apps.py, migrations/*, urls.py, views.py (esqueleto), settings/urls |
| 2 (RED) | Testes falhos — views | a9cb5e9 | tests/test_views.py |
| 2 (GREEN) | Views e templates | cd85d96 | views.py (completo), templates/estoque/* |

## Requirements Delivered

| Req | Status | Notes |
|-----|--------|-------|
| EST-01 | Entregue | CadastrarItemEstoqueView com unidade_organizacional do usuário |
| EST-02 | Entregue | quantidade_minima no model e ItemEstoqueForm |
| EST-03 | Entregue | AtualizarQuantidadeView com select_for_update + atomic |
| EST-04 | Entregue | Propriedade abaixo_do_minimo; destaque visual com .abaixo-minimo |
| EST-05 | Entregue | get_object_or_404 com filtro unidade_organizacional (IDOR guard) |
| EST-06 | Entregue | VisaoConsolidadaView; PermissionDenied para Solicitante |

## Threat Mitigations Applied

| Threat ID | Mitigation | Onde |
|-----------|-----------|------|
| T-03-05 | get_object_or_404(ItemEstoque, pk=pk, unidade_organizacional=user.default_unit) | EditarItemEstoqueView, AtualizarQuantidadeView |
| T-03-06 | PermissionDenied se role not in (comprador, admin) e not is_superuser | VisaoConsolidadaView.dispatch() |
| T-03-07 | select_for_update() dentro de transaction.atomic() | AtualizarQuantidadeView.post() |
| T-03-08 | clean_quantidade_atual: raise ValidationError se valor < 0 | AtualizarQuantidadeForm |
| T-03-09 | item.unidade_organizacional = request.user.default_unit (nunca do POST) | CadastrarItemEstoqueView, EditarItemEstoqueView |

## TDD Gate Compliance

- RED gate (Task 1): commit b740a82 — `test(03-02): add failing tests for estoque models and forms`
- GREEN gate (Task 1): commit 8cb2383 — `feat(03-02): scaffold app estoque`
- RED gate (Task 2): commit a9cb5e9 — `test(03-02): add failing tests for estoque views`
- GREEN gate (Task 2): commit cd85d96 — `feat(03-02): views, URLs e templates de estoque`

Todas as gates RED/GREEN respeitadas em sequência correta.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Sigla "UN" no teste test_str_retorna_nome_e_sigla conflitava com seed**
- **Found during:** Task 1 GREEN — primeiro run dos testes
- **Issue:** A migration 0002_seed_unidades já havia criado o registro com sigla="UN" no banco de teste. O teste tentava criar um segundo UnidadeMedida com mesma sigla, levantando IntegrityError.
- **Fix:** Alterado o teste para usar nome="Unidade Teste Str" / sigla="UT_STR" — sigla distinta que não conflita com seeds.
- **Files modified:** apps/estoque/tests/test_models.py
- **Commit:** 8cb2383

**2. [Rule 3 - Blockers] Testes exigem PostgreSQL local — não Docker**
- **Found during:** Tentativa de rodar testes com `DB_HOST=db` (padrão do .env)
- **Issue:** O `.env` aponta para `DB_HOST=db` (nome do container Docker). A suíte de testes roda fora do container no host Windows. O PostgreSQL local na porta 5432 estava acessível.
- **Fix:** Execução dos testes com variável de ambiente `DB_HOST=localhost DB_PORT=5432`.
- **Impact:** Zero — os arquivos de produção não foram alterados. A convenção de testes locais exige `DB_HOST=localhost`.

## Known Stubs

Nenhum — todos os campos estão conectados ao modelo real.

## Threat Flags

Nenhuma superfície nova além do registrado no threat_model do plano.

## Self-Check

### Files exist

- FOUND: apps/estoque/models.py
- FOUND: apps/estoque/forms.py
- FOUND: apps/estoque/views.py
- FOUND: apps/estoque/urls.py
- FOUND: apps/estoque/admin.py
- FOUND: apps/estoque/migrations/0001_initial.py
- FOUND: apps/estoque/migrations/0002_seed_unidades.py
- FOUND: templates/estoque/lista.html
- FOUND: templates/estoque/visao_consolidada.html

### Commits exist

- FOUND: b740a82 (test RED models/forms)
- FOUND: 8cb2383 (feat GREEN scaffold)
- FOUND: a9cb5e9 (test RED views)
- FOUND: cd85d96 (feat GREEN views+templates)

### Tests

- 25 passed, 0 failures, 0 errors

## Self-Check: PASSED
