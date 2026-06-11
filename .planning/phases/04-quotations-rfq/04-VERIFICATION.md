---
phase: 04-quotations-rfq
verified: 2026-06-11T21:40:00Z
status: human_needed
score: 20/20 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Login como Comprador → item 'Cotações' visível na barra lateral; Login como Solicitante → item ausente"
    expected: "Link 'Cotações' aparece apenas para comprador/admin; Solicitante não vê o link"
    why_human: "Condicional de role no template verificado estaticamente; renderização real depende de sessão de browser"
  - test: "Acessar /cotacoes/, clicar 'Nova Cotação', selecionar uma requisição aprovada, criar RFQ, adicionar duas cotações, verificar tabela comparativa"
    expected: "Menor preço destacado com badge vermelho (#e94560); delta % exibido para os demais fornecedores; botão 'Selecionar Vencedor' visível"
    why_human: "Renderização visual e interação HTMX não verificáveis por grep; destaque de cor requer browser"
  - test: "Clicar 'Selecionar Vencedor' para a menor cotação, digitar justificativa e confirmar"
    expected: "Modal fecha, página recarrega com card 'Vencedor Selecionado', botões add/remove/selecionar desaparecem, formulário de adição oculto"
    why_human: "Comportamento HTMX pós-seleção (HX-Redirect + rerender) requer browser para confirmar"
  - test: "Após seleção de vencedor, tentar acessar botão de 'Adicionar Cotação' ou 'Remover' via URL direta"
    expected: "Resposta 403 para add/remove; 409 para modal-selecionar"
    why_human: "Guard testado automaticamente, mas UX de bloqueio pós-seleção merece confirmação manual"
---

# Phase 04: Cotações (RFQ) — Verification Report

**Phase Goal:** Comprador executa o ciclo completo de RFQ — cria processo vinculado a requisição aprovada, registra cotações de múltiplos fornecedores, visualiza comparativo de preços automático, e seleciona o vencedor com justificativa obrigatória (imutável após salvo). Acesso restrito a Comprador e Admin.
**Verified:** 2026-06-11T21:40:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | App `apps.cotacoes` em INSTALLED_APPS e migra sem erro | VERIFIED | `config/settings/base.py` line 37: `"apps.cotacoes"`; `makemigrations --check` → "No changes detected"; 2 migrations applied (0001_initial + 0002_alter_rfq_vencedor_protect) |
| 2 | Modelo RFQ com OneToOneField para Requisicao (unicidade no DB) | VERIFIED | `apps/cotacoes/models.py` lines 27-31: `OneToOneField("requisicoes.Requisicao", on_delete=PROTECT, related_name="rfq")`; migration 0001 confirms `UNIQUE` constraint on `requisicao_id` |
| 3 | Modelo CotacaoFornecedor com preco_unitario DecimalField e MinValueValidator(0.01) | VERIFIED | `apps/cotacoes/models.py` lines 82-86: `DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])` |
| 4 | `services.calcular_comparativo` retorna menor preço com `is_menor=True` e delta % | VERIFIED | `apps/cotacoes/services.py` lines 70-101: implementation with guard `if menor and menor > 0`, quantized delta; `TestCalcularComparativo` + `TestDeltaPercentual` + `TestDeltaZero` all pass |
| 5 | `services.selecionar_vencedor` usa select_for_update + transaction.atomic e é imutável | VERIFIED | `apps/cotacoes/services.py` lines 128-138: `with transaction.atomic(): rfq = RFQ.objects.select_for_update().get(pk=rfq_pk)`; guard `if rfq.tem_vencedor: raise ValueError` inside transaction |
| 6 | Suite de testes Wave 0 existe e roda (33 testes GREEN) | VERIFIED | `docker compose exec web python -m pytest apps/cotacoes/` → **33 passed, 0 skipped, 0 failed** |
| 7 | Comprador acessa /cotacoes/ e vê lista de RFQs com status derivado | VERIFIED | `ListaRFQView` renders `rfq_list.html` with `rfq.status_display`; template displays "Em andamento"/"Encerrado" badges |
| 8 | Comprador cria RFQ selecionando requisição APROVADA sem RFQ vinculado | VERIFIED | `NovaRFQView.post()` delegates to `services.criar_rfq()`; redirects to `cotacoes:detalhe`; `test_cria_rfq_e_redireciona` passes |
| 9 | Select exclui requisições já vinculadas a RFQ e não-APROVADAS | VERIFIED | `apps/cotacoes/forms.py` lines 38-43: `filter(status=Requisicao.Status.APROVADO, rfq__isnull=True)`; `test_select_filtra_aprovadas_sem_rfq` passes |
| 10 | Segundo RFQ para mesma requisição retorna 409 (não 500) | VERIFIED | `NovaRFQView.post()` catches `IntegrityError` → `status=409`; `test_segundo_rfq_retorna_409` passes via mock |
| 11 | Solicitante recebe 403 em todas as rotas de /cotacoes/ | VERIFIED | `CompradorRequiredMixin` imported from `apps.fornecedores.views`; `test_acesso_negado_solicitante` + `test_acesso_negado_solicitante_lista` both pass |
| 12 | Comprador adiciona cotações; página recarrega via HX-Redirect | VERIFIED | `AdicionarCotacaoView.post()` returns `HttpResponseClientRedirect(...)`; `test_adicionar_cotacao_retorna_redirect_htmx` passes (asserts `"HX-Redirect" in response`) |
| 13 | Comprador remove cotação antes da seleção; tabela recarrega via HX-Redirect | VERIFIED | `RemoverCotacaoView.post()` returns `HttpResponseClientRedirect(...)`; `test_remover_cotacao_retorna_redirect_htmx` passes |
| 14 | Tabela comparativa destaca menor preço (#e94560) e mostra delta % | VERIFIED | `cotacao_row.html`: `{% if item.is_menor %}` → badge with `background-color:#e94560`; delta cell renders `{{ item.delta }}%`; `DetalheRFQView` injects `comparativo = services.calcular_comparativo(rfq)` |
| 15 | Comprador seleciona vencedor via modal com justificativa obrigatória; seleção imutável | VERIFIED | `SelecionarVencedorView` delegates to `services.selecionar_vencedor`; `modal_selecionar.html` has `textarea name="justificativa" required`; `test_post_confirma_selecao_e_redireciona` + `test_post_justificativa_vazia_retorna_409` + `test_post_segundo_selecionar_retorna_409` all pass |
| 16 | Após seleção, add/remove/selecionar retornam 403/409 | VERIFIED | Guard `if rfq.tem_vencedor` in all three views; `TestBloqueioPosSeletcao` (3 tests) all pass |
| 17 | Link "Cotações" no nav aponta para /cotacoes/ e fica ativo na seção | VERIFIED | `templates/base.html` line 56-59: `href="{% url 'cotacoes:lista' %}"` with `{% if 'cotacoes' in request.path %}is-active{% endif %}` |
| 18 | Link visível apenas para Comprador e Admin | VERIFIED | `templates/base.html` line 55: `{% if request.user.role == 'comprador' or request.user.role == 'admin' or request.user.is_superuser %}` |
| 19 | Suite completa do projeto está verde | VERIFIED | `docker compose exec web python -m pytest --tb=short` → **169 passed, 0 failed** |
| 20 | README.md marca Fase 4 como concluída | VERIFIED | `README.md` line 123: `\| 4 \| Cotações (RFQ) \| ✅ Completa \|`; Phase 4 section documents all RFQ features |

**Score:** 20/20 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `apps/cotacoes/models.py` | Modelos RFQ e CotacaoFornecedor | VERIFIED | `class RFQ(TimestampedModel)` + `class CotacaoFornecedor(TimestampedModel)`, OneToOneField, MinValueValidator |
| `apps/cotacoes/services.py` | criar_rfq, calcular_comparativo, selecionar_vencedor | VERIFIED | All 5 functions implemented; `select_for_update` + `transaction.atomic` in `selecionar_vencedor`; zero-division guard |
| `apps/cotacoes/tests/conftest.py` | Fixtures rfq, cotacao_fornecedor, requisicao_aprovada | VERIFIED | All fixtures present and wired |
| `apps/cotacoes/views.py` | 6 views including SelecionarVencedorView | VERIFIED | All 6 views implemented; CompradorRequiredMixin on all; HX-Redirect wired |
| `apps/cotacoes/forms.py` | RFQForm + CotacaoFornecedorForm | VERIFIED | `rfq__isnull=True` filter in RFQForm; `ativo=True` filter in CotacaoFornecedorForm |
| `apps/cotacoes/urls.py` | namespace cotacoes, 7 URL patterns | VERIFIED | `app_name = "cotacoes"`; all 7 routes registered |
| `apps/cotacoes/templates/cotacoes/rfq_list.html` | List template | VERIFIED | Extends base.html, loops rfqs, status badge, "Ver" link |
| `apps/cotacoes/templates/cotacoes/rfq_form.html` | Form template | VERIFIED | Extends base.html, requisicao select, CSRF, submit |
| `apps/cotacoes/templates/cotacoes/rfq_detail.html` | Detail template with comparativo | VERIFIED | Comparativo table, add-cotacao form (hidden post-selection), winner card, `id="modal-container"` |
| `apps/cotacoes/templates/cotacoes/partials/cotacao_row.html` | Row with badge + delta | VERIFIED | `is_menor` badge in #e94560, `item.delta` display, hx-get modal button |
| `apps/cotacoes/templates/cotacoes/partials/modal_selecionar.html` | Modal with justificativa | VERIFIED | `name="justificativa"` + `required`, hx-post to selecionar-vencedor |
| `apps/cotacoes/migrations/0001_initial.py` | Initial migration | VERIFIED | Generated by Django; includes OneToOneField + MinValueValidator |
| `apps/cotacoes/migrations/0002_alter_rfq_vencedor_protect.py` | Vencedor PROTECT migration | VERIFIED | Intentional deviation from plan (SET_NULL → PROTECT for stronger immutability) |
| `templates/base.html` | Cotações nav link wired | VERIFIED | `{% url 'cotacoes:lista' %}` + is-active guard + role guard |
| `README.md` | Phase 4 marked complete | VERIFIED | Phase 4 row shows ✅ Completa |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `config/urls.py` | `apps.cotacoes.urls` | `include("apps.cotacoes.urls")` | WIRED | Line 15: `path("cotacoes/", include("apps.cotacoes.urls"))` |
| `apps/cotacoes/views.py` | `apps.cotacoes.services.criar_rfq` | Delegation in NovaRFQView.post() | WIRED | `services.criar_rfq(form.cleaned_data["requisicao"].pk, request.user)` |
| `apps/cotacoes/views.py` | `apps.cotacoes.services.selecionar_vencedor` | Delegation in SelecionarVencedorView.post() | WIRED | `services.selecionar_vencedor(rfq_pk, cotacao_pk, justificativa, request.user)` |
| `apps/cotacoes/views.py` | `HttpResponseClientRedirect / HX-Redirect` | add/remove views return HX-Redirect | WIRED | `HttpResponseClientRedirect(reverse("cotacoes:detalhe", args=[rfq.pk]))` |
| `apps/cotacoes/templates/cotacoes/rfq_detail.html` | `comparativo` variable | Loop over `{cotacao, delta, is_menor}` dicts | WIRED | `{% for item in comparativo %}{% include "cotacoes/partials/cotacao_row.html" %}{% endfor %}` |
| `apps/cotacoes/models.py` | `apps.requisicoes.models.Requisicao` | OneToOneField | WIRED | `models.OneToOneField("requisicoes.Requisicao", on_delete=PROTECT, related_name="rfq")` |
| `apps/cotacoes/services.py` | `RFQ.objects.select_for_update()` | transaction.atomic + select_for_update | WIRED | `with transaction.atomic(): rfq = RFQ.objects.select_for_update().get(pk=rfq_pk)` |
| `templates/base.html` | `cotacoes:lista` | url tag in nav-item | WIRED | `href="{% url 'cotacoes:lista' %}"` with role guard and is-active state |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `rfq_list.html` | `rfqs` | `RFQ.objects.select_related("requisicao", "vencedor").order_by("-criado_em")` in `ListaRFQView.get()` | Yes — live DB query | FLOWING |
| `rfq_detail.html` | `comparativo` | `services.calcular_comparativo(rfq)` → `rfq.cotacoes.select_related("fornecedor").order_by("preco_unitario")` | Yes — live DB query | FLOWING |
| `rfq_detail.html` | `form` | `CotacaoFornecedorForm()` with `Fornecedor.objects.filter(ativo=True)` | Yes — live DB query | FLOWING |
| `cotacao_row.html` | `item` | Dict from `calcular_comparativo` — traced to DB above | Yes | FLOWING |
| `modal_selecionar.html` | `cotacao` | `get_object_or_404(CotacaoFornecedor, pk=cotacao_pk, rfq=rfq)` | Yes — live DB query | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `apps/cotacoes` test suite | `docker compose exec web python -m pytest apps/cotacoes/ -q` | 33 passed, 0 failed | PASS |
| Full project test suite | `docker compose exec web python -m pytest --tb=short` | 169 passed, 0 failed | PASS |
| Django system check | `docker compose exec web python manage.py check` | System check identified no issues (0 silenced) | PASS |
| Migration state clean | `docker compose exec web python manage.py makemigrations cotacoes --check --dry-run` | No changes detected | PASS |

### Probe Execution

No probe scripts declared in PLAN files. Step 7c: SKIPPED (no probe-*.sh files found for this phase).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| COT-01 | Plans 01, 02, 04 | Comprador cria RFQ vinculado a requisição aprovada (um RFQ por requisição) | SATISFIED | OneToOneField + service.criar_rfq + NovaRFQView + TestNovaRFQView (5 tests passing) |
| COT-02 | Plans 01, 03 | Comprador registra cotações de múltiplos fornecedores (preço, prazo, condições) | SATISFIED | CotacaoFornecedorForm + AdicionarCotacaoView + RemoverCotacaoView + 4 tests passing |
| COT-03 | Plans 01, 03 | Sistema exibe comparativo com destaque do menor preço e delta % | SATISFIED | `services.calcular_comparativo` + `cotacao_row.html` (is_menor badge + delta) + 3 service tests |
| COT-04 | Plans 01, 03 | Comprador seleciona fornecedor vencedor com justificativa obrigatória (imutável após salvo) | SATISFIED | `services.selecionar_vencedor` (select_for_update, ValueError guard) + SelecionarVencedorView + modal + 4 view tests |

All 4 requirements (COT-01, COT-02, COT-03, COT-04) are SATISFIED with automated test coverage.

### Notable Deviation — Not a Gap

**RFQ.vencedor on_delete: SET_NULL → PROTECT (CR-02)**

The PLAN specified `on_delete=SET_NULL` for `RFQ.vencedor`. The implementation upgraded this to `on_delete=PROTECT` via migration `0002_alter_rfq_vencedor_protect.py`. This is an intentional improvement: `SET_NULL` would silently reset a winner-selected RFQ back to "Em andamento" if the winning `CotacaoFornecedor` were deleted; `PROTECT` raises `ProtectedError` instead, enforcing the immutability guarantee at the DB layer. `makemigrations --check` confirms model and migration are in sync.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `apps/cotacoes/views.py` | 38 | `Hub /cotacoes/` in docstring — benign comment | Info | No impact — documentation only |
| `apps/cotacoes/templates/cotacoes/partials/modal_selecionar.html` | 24 | `placeholder="Descreva o motivo..."` — textarea hint text | Info | No impact — UX text, not a stub |

No `TBD`, `FIXME`, `XXX`, `return null`, or empty implementation patterns found in any modified file.

### Human Verification Required

Automated checks pass on all 20 must-haves. The following items require browser-based testing to confirm correct visual rendering and HTMX interaction flow:

#### 1. Nav Visibility by Role

**Test:** Login as Comprador — verify "Cotações" link visible in sidebar and navigates to `/cotacoes/`. Then login as Solicitante — verify "Cotações" link is absent from sidebar.
**Expected:** Comprador sees and can click "Cotações"; Solicitante sees no such link.
**Why human:** Role-conditional template rendering verified statically; browser session required to confirm correct runtime behavior.

#### 2. Comparativo Table Rendering

**Test:** Create an RFQ, add two supplier quotes with different prices, view the detail page.
**Expected:** Lowest price row shows red badge (#e94560) labeled "Menor preço"; other row(s) show amber delta percentage (e.g., "+50.0%"). Table columns show supplier name, price, delta, prazo, conditions, observations, action buttons.
**Why human:** CSS color rendering and HTMX-driven table update require browser; grep cannot verify pixel-level appearance.

#### 3. End-to-End Winner Selection Flow

**Test:** With two quotes loaded, click "Selecionar Vencedor" on the cheapest row. In the modal that appears, enter a justification and click "Confirmar Seleção".
**Expected:** Modal closes, page reloads showing "Vencedor Selecionado" card with supplier name, price, and justification. Add-cotacao form and action buttons disappear. Badge changes to "Encerrado".
**Why human:** HTMX HX-Redirect client-side navigation and DOM update after winner selection require browser interaction to verify.

#### 4. Post-Selection Immutability UX

**Test:** After a winner is selected, try navigating directly to `/cotacoes/<rfq_pk>/cotacoes/adicionar/` (POST) and `/cotacoes/<rfq_pk>/selecionar-vencedor/<cotacao_pk>/modal/` (GET).
**Expected:** 403 for add; 409 for modal. The UI should show no add-cotacao form and no "Selecionar Vencedor" buttons after selection.
**Why human:** Guard behavior tested automatically; UI confirmation that blocked paths produce appropriate user-facing responses (not raw 403/409 text in production) merits review.

### Gaps Summary

No gaps. All 20 must-have truths are VERIFIED against the codebase. The phase goal is fully achieved:

- COT-01: RFQ creation flow is end-to-end operational with uniqueness enforced at DB level
- COT-02: Quote add/remove is implemented with HX-Redirect for delta consistency
- COT-03: Price comparison table with automatic lowest-price highlighting and delta % is implemented
- COT-04: Winner selection is immutable, justified, and protected at both service and view layers

The 4 human verification items are visual/interactive confirmations of correctly implemented code, not functional gaps.

---

_Verified: 2026-06-11T21:40:00Z_
_Verifier: Claude (gsd-verifier)_
