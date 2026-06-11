---
phase: "04-quotations-rfq"
plan: "03"
subsystem: "cotacoes"
tags: [views, forms, templates, htmx, cot-02, cot-03, cot-04, rfq, comparativo, vencedor]
dependency_graph:
  requires:
    - apps.cotacoes.models.RFQ
    - apps.cotacoes.models.CotacaoFornecedor
    - apps.cotacoes.services.adicionar_cotacao
    - apps.cotacoes.services.remover_cotacao
    - apps.cotacoes.services.calcular_comparativo
    - apps.cotacoes.services.selecionar_vencedor
    - apps.fornecedores.views.CompradorRequiredMixin
    - django_htmx.http.HttpResponseClientRedirect
  provides:
    - apps.cotacoes.forms.CotacaoFornecedorForm
    - apps.cotacoes.views.AdicionarCotacaoView
    - apps.cotacoes.views.RemoverCotacaoView
    - apps.cotacoes.views.ModalSelecionarVencedorView
    - apps.cotacoes.views.SelecionarVencedorView
    - apps.cotacoes.views.DetalheRFQView (comparativo + form injetados)
    - apps.cotacoes.templates.cotacoes.partials.cotacao_row
    - apps.cotacoes.templates.cotacoes.partials.modal_selecionar
  affects:
    - apps/cotacoes/views.py
    - apps/cotacoes/forms.py
    - apps/cotacoes/urls.py
    - apps/cotacoes/templates/cotacoes/rfq_detail.html
tech_stack:
  added: []
  patterns:
    - HttpResponseClientRedirect para HX-Redirect (D-10, Pitfall 2)
    - guard rfq.tem_vencedor nas views (T-04-03)
    - except ValueError→409 em SelecionarVencedorView (T-04-06)
    - modal HTMX com justificativa obrigatória (padrão de modal_reprovar)
    - tabela comparativa estática com badge is_menor #e94560 e delta %
key_files:
  created:
    - apps/cotacoes/templates/cotacoes/partials/cotacao_row.html
    - apps/cotacoes/templates/cotacoes/partials/modal_selecionar.html
  modified:
    - apps/cotacoes/forms.py
    - apps/cotacoes/views.py
    - apps/cotacoes/urls.py
    - apps/cotacoes/templates/cotacoes/rfq_detail.html
    - apps/cotacoes/tests/test_views.py
decisions:
  - "HX-Redirect (HttpResponseClientRedirect) em add/remove recarrega página inteira para deltas consistentes (D-10, Pitfall 2 evitado)"
  - "Guard rfq.tem_vencedor na view antes de chamar o service: defense in depth (T-04-03)"
  - "modal_selecionar.html segue padrão exato de modal_reprovar.html: card com borda accent, textarea required, botão cancelar limpa #modal-container via onclick"
  - "TestAdicionarCotacaoView e TestRemoverCotacaoView expandidos com testes de bloqueio além do HX-Redirect"
  - "TestBloqueioPosSeletcao inclui teste de modal-selecionar→409 além dos add/remove→403 do plano original"
metrics:
  duration: "~10 minutos"
  completed_date: "2026-06-11"
  tasks_completed: 2
  files_created: 2
  files_modified: 5
---

# Phase 04 Plan 03: Slice Vertical Final — Cotações, Comparativo e Seleção de Vencedor

**One-liner:** Slice vertical completo do ciclo RFQ com CotacaoFornecedorForm (fornecedores ativos), add/remove via HX-Redirect (D-10), tabela comparativa com badge menor preço #e94560 e delta %, modal de seleção com justificativa obrigatória imutável, bloqueio total pós-seleção (403/409), e 33 testes GREEN sem skips.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | CotacaoFornecedorForm + add/remove views + comparativo + testes COT-02/03 | 887cccc | forms.py, views.py, urls.py, rfq_detail.html, cotacao_row.html, test_views.py |
| 2 | Modal de seleção + SelecionarVencedorView + testes COT-04 | bd51538 | modal_selecionar.html |

---

## Decisions Made

1. **HX-Redirect via `HttpResponseClientRedirect`:** Após adicionar ou remover cotação, a view retorna `HttpResponseClientRedirect` (header `HX-Redirect`) para recarregar a página completa. Isso garante que os deltas percentuais sejam sempre recalculados consistentemente (D-10, Pitfall 2 — deltas desatualizados evitados).

2. **Guard `rfq.tem_vencedor` antes do service (defense in depth):** Tanto `AdicionarCotacaoView` quanto `RemoverCotacaoView` verificam `rfq.tem_vencedor` na view e retornam 403 antes de chamar o service. O service também valida internamente — dupla proteção (T-04-03, D-08).

3. **`modal_selecionar.html` segue padrão de `modal_reprovar.html`:** Card com `border-color:#e94560`, `textarea required`, botão "Cancelar" com `onclick="document.getElementById('modal-container').innerHTML=''"`. O `required` no textarea é a primeira barreira; `selecionar_vencedor` no service valida novamente (defense in depth).

4. **Expansão dos testes de bloqueio:** `TestBloqueioPosSeletcao` inclui um terceiro teste (`test_bloqueia_modal_selecionar_apos_vencedor`) que verifica o retorno 409 em `ModalSelecionarVencedorView` — além dos dois testes de 403 em add/remove que existiam como stubs no plano original.

5. **Testes de `TestAdicionarCotacaoView`/`TestRemoverCotacaoView` expandidos:** Cada classe recebeu dois testes (HX-Redirect em sucesso + bloqueio pós-seleção), em vez do único teste stub do plano original.

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Testes rodavam localmente mas precisam do Docker**
- **Found during:** Task 1, primeira tentativa de `python -m pytest` local
- **Issue:** O banco configurado aponta para host `db` (Docker Compose); rodar pytest fora do container falhava com `OperationalError: could not translate host name "db"`.
- **Fix:** Todos os comandos `pytest` executados via `docker compose exec web python -m pytest` (padrão dos planos anteriores).
- **Files modified:** Nenhum — apenas ajuste no comando de execução.
- **Commit:** N/A

### Out-of-Scope

Nenhuma descoberta fora do escopo.

---

## Test Results

```
apps/cotacoes/tests/test_models.py    ......      (6 passed)
apps/cotacoes/tests/test_services.py  ...........  (11 passed)
apps/cotacoes/tests/test_views.py     ................  (16 passed)

Total: 33 passed, 0 skipped, 16 warnings
```

---

## Verification

- `python manage.py check` — sem erros (0 silenced) ✓
- `pytest apps/cotacoes/tests/test_views.py::TestAdicionarCotacaoView` — 2 passed ✓
- `pytest apps/cotacoes/tests/test_views.py::TestRemoverCotacaoView` — 2 passed ✓
- `pytest apps/cotacoes/tests/test_views.py::TestModalSelecionarVencedor` — 4 passed ✓
- `pytest apps/cotacoes/tests/test_views.py::TestBloqueioPosSeletcao` — 3 passed ✓
- `pytest apps/cotacoes/ -v` — 33 passed, 0 skipped ✓
- `apps/cotacoes/forms.py` contém `class CotacaoFornecedorForm` e `ativo=True` ✓
- `apps/cotacoes/views.py` contém `HttpResponseClientRedirect` e `rfq.tem_vencedor` ✓
- `apps/cotacoes/views.py` contém `class SelecionarVencedorView` e `except ValueError` ✓
- `apps/cotacoes/views.py` DetalheRFQView contém `services.calcular_comparativo` ✓
- `apps/cotacoes/urls.py` contém `name="selecionar-vencedor"` e `name="modal-selecionar"` ✓
- `cotacao_row.html` contém `is_menor` e `item.delta` ✓
- `modal_selecionar.html` contém `name="justificativa"` e `required` ✓

---

## Known Stubs

Nenhum stub que impeça o objetivo do plano. O ciclo RFQ está completo de ponta a ponta:
requisição aprovada → criar RFQ → adicionar cotações → comparativo → selecionar vencedor (imutável).

---

## Threat Flags

Nenhuma nova superfície de segurança além do declarado no `<threat_model>` do plano:
- T-04-03: guard `rfq.tem_vencedor` em add/remove/modal — implementado ✓
- T-04-05: `selecionar_vencedor` usa `select_for_update` no service — já existia ✓
- T-04-06: `except ValueError → 409` em `SelecionarVencedorView` — implementado ✓
- T-04-CSRF: `{% csrf_token %}` em todos os forms HTMX — implementado ✓

---

## Self-Check: PASSED

- apps/cotacoes/forms.py contém CotacaoFornecedorForm: FOUND
- apps/cotacoes/views.py contém AdicionarCotacaoView: FOUND
- apps/cotacoes/views.py contém RemoverCotacaoView: FOUND
- apps/cotacoes/views.py contém ModalSelecionarVencedorView: FOUND
- apps/cotacoes/views.py contém SelecionarVencedorView: FOUND
- apps/cotacoes/urls.py contém modal-selecionar e selecionar-vencedor: FOUND
- apps/cotacoes/templates/cotacoes/partials/cotacao_row.html: FOUND
- apps/cotacoes/templates/cotacoes/partials/modal_selecionar.html: FOUND
- Commit 887cccc: FOUND
- Commit bd51538: FOUND
