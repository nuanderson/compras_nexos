---
phase: 04-quotations-rfq
reviewed: 2026-06-11T21:00:00Z
depth: standard
files_reviewed: 20
files_reviewed_list:
  - apps/cotacoes/__init__.py
  - apps/cotacoes/admin.py
  - apps/cotacoes/apps.py
  - apps/cotacoes/forms.py
  - apps/cotacoes/migrations/0001_initial.py
  - apps/cotacoes/models.py
  - apps/cotacoes/services.py
  - apps/cotacoes/templates/cotacoes/partials/cotacao_row.html
  - apps/cotacoes/templates/cotacoes/partials/modal_selecionar.html
  - apps/cotacoes/templates/cotacoes/rfq_detail.html
  - apps/cotacoes/templates/cotacoes/rfq_form.html
  - apps/cotacoes/templates/cotacoes/rfq_list.html
  - apps/cotacoes/tests/conftest.py
  - apps/cotacoes/tests/test_models.py
  - apps/cotacoes/tests/test_services.py
  - apps/cotacoes/tests/test_views.py
  - apps/cotacoes/urls.py
  - apps/cotacoes/views.py
  - config/urls.py
  - templates/base.html
findings:
  critical: 4
  warning: 3
  info: 2
  total: 9
status: issues_found
---

# Phase 04: Code Review Report

**Reviewed:** 2026-06-11T21:00:00Z
**Depth:** standard
**Files Reviewed:** 20
**Status:** issues_found

## Summary

The quotations/RFQ module is structurally sound — the service layer pattern is consistent, the select_for_update concurrency guard is in place, and HTMX HX-Redirect pattern is applied correctly. However, four critical defects were found that can each cause a production crash or silent data corruption, and three warnings require attention before this is considered shippable quality.

---

## Critical Issues

### CR-01: `remover_cotacao` raises `DoesNotExist` — view has no handler, returns HTTP 500

**File:** `apps/cotacoes/views.py:153` / `apps/cotacoes/services.py:66`

**Issue:** `services.remover_cotacao` calls `CotacaoFornecedor.objects.get(pk=cotacao_pk, rfq=rfq)` and raises `CotacaoFornecedor.DoesNotExist` when the cotacao does not belong to the rfq, or when it has already been deleted (double-click, concurrent remove). `RemoverCotacaoView.post` does not catch this exception. Django will serve an unhandled 500, exposing a stack trace in non-DEBUG mode and a full traceback in DEBUG mode. The docstring in services.py acknowledges the exception is raised, but no caller catches it.

**Fix:**
```python
# views.py — RemoverCotacaoView.post
from apps.cotacoes.models import CotacaoFornecedor

def post(self, request, rfq_pk, cotacao_pk):
    rfq = get_object_or_404(RFQ, pk=rfq_pk)
    if rfq.tem_vencedor:
        return HttpResponse("RFQ encerrado.", status=403)
    try:
        services.remover_cotacao(rfq, cotacao_pk)
    except CotacaoFornecedor.DoesNotExist:
        return HttpResponse("Cotação não encontrada.", status=404)
    return HttpResponseClientRedirect(reverse("cotacoes:detalhe", args=[rfq.pk]))
```

---

### CR-02: `vencedor` FK uses `on_delete=SET_NULL` — deleting a `CotacaoFornecedor` silently erases the winner record

**File:** `apps/cotacoes/models.py:42`

**Issue:** `RFQ.vencedor` is a FK to `CotacaoFornecedor` with `on_delete=models.SET_NULL`. The `CotacaoFornecedor` model uses `on_delete=CASCADE` from `RFQ`. This means: if an RFQ is deleted (or if admin bulk-deletes a `CotacaoFornecedor` row), `rfq.vencedor` is silently set to `NULL`, destroying the immutability invariant stated in D-07 with no error raised, no audit trail, and no validation block.

Furthermore, because `CotacaoFornecedor` is itself cascade-deleted when its parent `RFQ` is deleted (correct), the SET_NULL path is reachable via direct admin deletion of a single `CotacaoFornecedor` row. An admin user can delete the winning cotacao row, and the RFQ's `vencedor` becomes NULL — the RFQ goes back to "Em andamento" silently, and the selection justification is orphaned in `justificativa_selecao` while `tem_vencedor` returns `False`.

**Fix:** Change to `on_delete=models.PROTECT` so that deleting a cotacao that is referenced as a winner raises an `IntegrityError` rather than silently nulling the reference. Generate a new migration.

```python
# models.py
vencedor = models.ForeignKey(
    "CotacaoFornecedor",
    null=True,
    blank=True,
    on_delete=models.PROTECT,  # was SET_NULL — prevents silent erasure of winner
    related_name="rfqs_vencidos",
)
```

---

### CR-03: `update_fields` in `selecionar_vencedor` omits `vencedor_id` — winner is never persisted

**File:** `apps/cotacoes/services.py:137`

**Issue:** Django's `update_fields` on `save()` is a whitelist of column names to write. The FK column for `vencedor` on the database is `vencedor_id`, not `vencedor`. Passing `update_fields=["vencedor", ...]` causes Django to raise a `ValueError` at runtime: `"The following fields do not exist in this model, are m2m fields, or are non-concrete fields: vencedor"`.

Test coverage misses this because `test_selecionar_vencedor_define_rfq_vencedor` calls `rfq_result.refresh_from_db()` after the save, and if the exception is silently swallowed (it is not — it crashes), but in Python the `ValueError` from `update_fields` would propagate before the `return rfq` line, causing a 500 in the view. Confirm: Django docs state `update_fields` must contain field names or attnames (i.e. `vencedor_id` for FK fields when using `_id` attname).

Note: Django actually accepts the attribute name `"vencedor"` on `save()` and internally resolves it to `vencedor_id`, so this specific case depends on the Django version. In Django 5.x this works as-is. However, including `"atualizado_em"` in `update_fields` alongside an `auto_now=True` field IS the issue: per Django docs, `auto_now` fields are only updated when `update_fields` is None OR when `atualizado_em` is explicitly included in the list. The current code does include it, so `auto_now` will fire correctly. **Revised verdict:** The `update_fields` call is correct. This finding is retracted — see WR-01 for a lesser issue in this area.

**Retracted — see WR-01.**

---

### CR-03 (revised): `selecionar_vencedor` raises `CotacaoFornecedor.DoesNotExist` — `SelecionarVencedorView` has no handler

**File:** `apps/cotacoes/views.py:194` / `apps/cotacoes/services.py:134`

**Issue:** `services.selecionar_vencedor` can raise `CotacaoFornecedor.DoesNotExist` if `cotacao_pk` does not exist or does not belong to the given `rfq`. The view catches only `ValueError` (line 195). Any `DoesNotExist` propagates unhandled, returning HTTP 500. A user who crafts a URL with a mismatched `rfq_pk`/`cotacao_pk` pair (e.g. `POST /cotacoes/1/selecionar-vencedor/999/`) will receive a 500 rather than a 404.

**Fix:**
```python
# views.py — SelecionarVencedorView.post
from apps.cotacoes.models import CotacaoFornecedor

def post(self, request, rfq_pk, cotacao_pk):
    justificativa = request.POST.get("justificativa", "")
    try:
        services.selecionar_vencedor(rfq_pk, cotacao_pk, justificativa, request.user)
    except ValueError as e:
        return HttpResponse(str(e), status=409)
    except CotacaoFornecedor.DoesNotExist:
        return HttpResponse("Cotação não encontrada.", status=404)
    return HttpResponseClientRedirect(reverse("cotacoes:detalhe", args=[rfq_pk]))
```

---

### CR-04: Migration header claims "Generated by Django 6.0.6" — version mismatch signals migration was generated in a different environment

**File:** `apps/cotacoes/migrations/0001_initial.py:1`

**Issue:** The migration file header reads `# Generated by Django 6.0.6 on 2026-06-11 20:12`. The project's `CLAUDE.md` mandates Django 5.2 LTS. Django 6 does not exist as of the project's knowledge cutoff. This indicates either the migration was manually edited to have a wrong header, or (more concerningly) it was generated against a different environment whose Django version diverges from the locked version. If the actual installed Django is 5.2 but a developer runs `migrate` against this file on a clean environment, Django may reject or misinterpret the migration if the generated SQL relies on version-specific behaviour.

This is a data integrity risk because migrations are the authoritative schema source. A version mismatch in the header is a strong signal the migration was not generated cleanly with the pinned stack.

**Fix:** Regenerate the migration against the correct environment (`Django==5.2.x`). The header comment line can also be deleted — it is cosmetic — but the underlying risk is that the migration may have been written by hand or tooling drift rather than `manage.py makemigrations`.

---

## Warnings

### WR-01: `update_fields` includes `"atualizado_em"` — redundant with `auto_now`, but harmless; however omitting it would break `auto_now` semantics

**File:** `apps/cotacoes/services.py:137`

**Issue:** `rfq.save(update_fields=["vencedor", "justificativa_selecao", "atualizado_em"])` explicitly includes `"atualizado_em"`. This is correct per Django docs — when `update_fields` is used, `auto_now` fields are only written if included in the list. However, the attribute name for the FK column is ambiguous: Django accepts `"vencedor"` here (it resolves to the column `vencedor_id`), but the convention inconsistency (field name vs. attname) could mislead future developers who add FK fields and use `_id` naming in `update_fields`. Documenting this explicitly would prevent future bugs.

**Fix:** Add a comment or use the explicit `"vencedor_id"` to make intent clear:
```python
rfq.save(update_fields=["vencedor_id", "justificativa_selecao", "atualizado_em"])
# "atualizado_em" must be listed explicitly when using update_fields + auto_now=True
```

---

### WR-02: Duplicate CSRF token injection — `cotacao_row.html` uses `hx-headers` alongside global `htmx:configRequest` handler in `base.html`

**File:** `apps/cotacoes/templates/cotacoes/partials/cotacao_row.html:31` / `templates/base.html:13-16`

**Issue:** `base.html` registers an `htmx:configRequest` event listener that injects `X-CSRFToken` into every HTMX request. `cotacao_row.html` additionally hardcodes `hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'` on the Remover button (line 31). The CSRF token is therefore sent twice for this specific request — once from `hx-headers` (applied first) and once from the global listener (which overwrites it). While the end result is the same CSRF token value, the duplicate mechanism is a maintenance hazard: if the global handler is ever changed or removed, only `cotacao_row.html` will break silently, and the inconsistency will make debugging harder.

**Fix:** Remove the `hx-headers` attribute from `cotacao_row.html`. The global `htmx:configRequest` listener in `base.html` is the authoritative CSRF injection point for all HTMX requests in the application.

```html
<!-- cotacao_row.html — remove the hx-headers line -->
<button
  hx-post="{% url 'cotacoes:remover-cotacao' rfq.pk item.cotacao.pk %}"
  hx-confirm="Deseja remover a cotação de {{ item.cotacao.fornecedor.razao_social }}?"
  class="btn btn-secondary"
  style="font-size:12px;padding:4px 10px;">
  Remover
</button>
```

---

### WR-03: `AdicionarCotacaoView` on form error re-renders `rfq_detail.html` without loading `select_related` data — can raise `AttributeError` on template rendering

**File:** `apps/cotacoes/views.py:130-136`

**Issue:** When the form is invalid, the view fetches `rfq = get_object_or_404(RFQ, pk=rfq_pk)` with no `select_related`. It then renders `rfq_detail.html`, which accesses `rfq.requisicao.descricao`, `rfq.requisicao.categoria`, `rfq.requisicao.unidade`, `rfq.vencedor.fornecedor.razao_social` (in the winner card), etc. All of these will trigger additional N+1 queries. More critically, `rfq.vencedor.fornecedor` access when the winner exists will issue two extra queries instead of using the prefetched path — but in the error re-render path `rfq.tem_vencedor` gates the winner card, so the attribute error is deferred. The `rfq.requisicao.*` fields will always be accessed without a join.

Compare with `DetalheRFQView.get` (line 93-94) which correctly uses `select_related("requisicao", "vencedor__fornecedor")`. The error re-render path should use the same queryset.

**Fix:**
```python
# views.py — AdicionarCotacaoView.post (invalid form path)
rfq = get_object_or_404(
    RFQ.objects.select_related("requisicao", "vencedor__fornecedor"),
    pk=rfq_pk,
)
```

---

## Info

### IN-01: No `UniqueConstraint` on `(rfq, fornecedor)` in `CotacaoFornecedor` — same supplier can be added twice to one RFQ

**File:** `apps/cotacoes/models.py:65-97` / `apps/cotacoes/migrations/0001_initial.py`

**Issue:** There is no database-level or form-level constraint preventing a buyer from adding the same `Fornecedor` twice to the same `RFQ`. The form does not validate for duplicates; the service layer does not check; the model has no `UniqueConstraint`. This will produce a confusing comparativo table showing the same supplier twice with potentially different prices, with no indication that this is an error.

**Fix:** Add a `UniqueConstraint` and generate a migration:
```python
# models.py — CotacaoFornecedor.Meta
class Meta:
    verbose_name = "Cotacao de Fornecedor"
    verbose_name_plural = "Cotacoes de Fornecedores"
    ordering = ["preco_unitario"]
    constraints = [
        models.UniqueConstraint(
            fields=["rfq", "fornecedor"],
            name="unique_cotacao_por_fornecedor_rfq",
        )
    ]
```

---

### IN-02: `CompradorRequiredMixin` is imported from `apps.fornecedores.views` — tight cross-app coupling

**File:** `apps/cotacoes/views.py:29`

**Issue:** `cotacoes` imports `CompradorRequiredMixin` from `apps.fornecedores.views`. This creates a cross-app dependency where `cotacoes` cannot be used without also loading `fornecedores`. The mixin is pure auth logic that belongs in `apps.core` or `apps.accounts`. If `fornecedores` is ever refactored, all views in `cotacoes` break at import time.

**Fix:** Move `CompradorRequiredMixin` to `apps/core/mixins.py` (or `apps/accounts/mixins.py`) and update imports in both `apps/fornecedores/views.py` and `apps/cotacoes/views.py`.

---

_Reviewed: 2026-06-11T21:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
