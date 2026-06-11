---
phase: "04-quotations-rfq"
plan: "02"
subsystem: "cotacoes"
tags: [views, forms, templates, urls, htmx, cot-01, rfq]
dependency_graph:
  requires: [apps.cotacoes.models.RFQ, apps.cotacoes.services.criar_rfq, apps.fornecedores.views.CompradorRequiredMixin]
  provides: [apps.cotacoes.views.ListaRFQView, apps.cotacoes.views.NovaRFQView, apps.cotacoes.views.DetalheRFQView, apps.cotacoes.forms.RFQForm, apps.cotacoes.urls]
  affects: [config/urls.py, templates/base.html]
tech_stack:
  added: []
  patterns: [CompradorRequiredMixin reutilizado de fornecedores, IntegrityError capturado na view → 409, queryset filtrado no form (rfq__isnull=True), mock de IntegrityError para testar race condition 409]
key_files:
  created:
    - apps/cotacoes/forms.py
    - apps/cotacoes/views.py
    - apps/cotacoes/urls.py
    - apps/cotacoes/templates/cotacoes/rfq_list.html
    - apps/cotacoes/templates/cotacoes/rfq_form.html
    - apps/cotacoes/templates/cotacoes/rfq_detail.html
  modified:
    - apps/cotacoes/tests/test_views.py
    - config/urls.py
    - templates/base.html
decisions:
  - "test_segundo_rfq_retorna_409 usa unittest.mock para simular IntegrityError: o queryset rfq__isnull=True impede que a requisição já cotada apareça no form, logo o caminho real do IntegrityError só ocorre em race condition — mock é a abordagem correta"
  - "base.html link Cotações incluído is_superuser além de comprador/admin para paridade com CompradorRequiredMixin"
metrics:
  duration: "~11 minutos"
  completed_date: "2026-06-11"
  tasks_completed: 2
  files_created: 6
  files_modified: 3
---

# Phase 04 Plan 02: Slice Vertical RFQ — Views, Forms, Templates e Testes COT-01

**One-liner:** Slice vertical completo de COT-01 com ListaRFQView/NovaRFQView/DetalheRFQView (CompradorRequiredMixin), RFQForm (queryset filtrado APROVADO+rfq__isnull=True), três templates estendendo base.html, namespace `cotacoes` registrado em config/urls.py, e 5 testes COT-01 GREEN incluindo mock de race condition 409.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | RFQForm + views + urls + registro config/urls.py | 2d51824 | forms.py, views.py, urls.py, config/urls.py |
| 2 | Templates rfq_list/rfq_form/rfq_detail + testes COT-01 GREEN | b4a23b6 | rfq_list.html, rfq_form.html, rfq_detail.html, test_views.py, base.html |

---

## Decisions Made

1. **Mock para teste de race condition 409:** O queryset `rfq__isnull=True` no `RFQForm` impede que uma requisição já vinculada a RFQ apareça no select, tornando impossível acionar o IntegrityError pela interface normal. O único cenário real é uma race condition entre dois compradores simultâneos. O teste usa `unittest.mock.patch` em `services.criar_rfq` para forçar o `IntegrityError` e verificar que a view retorna 409 corretamente (nunca 500).

2. **base.html sidebar inclui `is_superuser`:** O link "Cotações" foi atualizado para incluir `is_superuser` além de `comprador` e `admin`, para manter paridade com o comportamento do `CompradorRequiredMixin` (que também permite superusers).

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Import `*` dentro de método de teste causava SyntaxError**
- **Found during:** Task 2, primeira execução dos testes
- **Issue:** O código inicial incluía `from apps.cotacoes.tests.conftest import *` dentro de um método de teste, o que é sintaticamente inválido em Python.
- **Fix:** Linha removida — as fixtures do conftest são injetadas automaticamente pelo pytest, não precisam de import explícito.
- **Files modified:** `apps/cotacoes/tests/test_views.py`
- **Commit:** b4a23b6

**2. [Rule 1 - Bug] test_segundo_rfq_retorna_409 retornava 200 em vez de 409**
- **Found during:** Task 2, primeira rodada de testes no Docker
- **Issue:** O teste postava `requisicao_aprovada.pk` que já tinha RFQ vinculado. O `RFQForm` com `rfq__isnull=True` invalidava o form antes de chamar o service, retornando 200 (form inválido) em vez de 409 (IntegrityError capturado).
- **Fix:** Redesenhar o teste para usar `unittest.mock.patch` em `services.criar_rfq` com `side_effect=IntegrityError`, simulando a condição de corrida que é o cenário real de uso.
- **Files modified:** `apps/cotacoes/tests/test_views.py`
- **Commit:** b4a23b6

---

## Test Results

```
apps/cotacoes/tests/test_views.py::TestNovaRFQView    .....   (5 passed)
apps/cotacoes/tests/test_views.py — outros            ssssss  (6 skipped — plano 03)
apps/cotacoes/tests/test_models.py                    ......  (6 passed)
apps/cotacoes/tests/test_services.py                  ....... (11 passed)

Total: 22 passed, 6 skipped
```

---

## Verification

- `python manage.py check` — sem erros ✓
- `python -c "...reverse('cotacoes:lista')..."` → `/cotacoes/` ✓
- `apps/cotacoes/forms.py` contém `rfq__isnull=True` e `label_from_instance` ✓
- `apps/cotacoes/views.py` contém `from apps.fornecedores.views import CompradorRequiredMixin` ✓
- `apps/cotacoes/views.py` contém `services.criar_rfq` e `except IntegrityError` ✓
- `apps/cotacoes/urls.py` contém `app_name = "cotacoes"` ✓
- `config/urls.py` contém `cotacoes/` ✓
- `rfq_detail.html` contém `id="modal-container"` e "Adicione cotações" ✓
- `pytest apps/cotacoes/tests/test_views.py::TestNovaRFQView -x -q` — 5 passed ✓
- `pytest apps/cotacoes/ -x -q` — 22 passed, 6 skipped ✓

---

## Known Stubs

- `rfq_detail.html` exibe placeholder "Adicione cotações de fornecedores para ver o comparativo." — intencional (D-10). A tabela comparativa e o formulário de adição de cotações serão implementados no plano 03.

---

## Threat Flags

Nenhuma nova superfície de segurança além do declarado no `<threat_model>` do plano.

---

## Self-Check: PASSED

- apps/cotacoes/forms.py: FOUND
- apps/cotacoes/views.py: FOUND
- apps/cotacoes/urls.py: FOUND
- apps/cotacoes/templates/cotacoes/rfq_list.html: FOUND
- apps/cotacoes/templates/cotacoes/rfq_form.html: FOUND
- apps/cotacoes/templates/cotacoes/rfq_detail.html: FOUND
- Commit 2d51824: FOUND
- Commit b4a23b6: FOUND
