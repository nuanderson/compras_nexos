---
phase: 02-requisitions-approvals
reviewed: 2026-06-10T00:00:00Z
depth: standard
files_reviewed: 27
files_reviewed_list:
  - apps/aprovacoes/admin.py
  - apps/aprovacoes/forms.py
  - apps/aprovacoes/models.py
  - apps/aprovacoes/services.py
  - apps/aprovacoes/templates/aprovacoes/fila_diretor.html
  - apps/aprovacoes/templates/aprovacoes/fila_gestor.html
  - apps/aprovacoes/templates/aprovacoes/partials/fila_diretor_row.html
  - apps/aprovacoes/templates/aprovacoes/partials/fila_row.html
  - apps/aprovacoes/templates/aprovacoes/partials/modal_reprovar.html
  - apps/aprovacoes/templates/aprovacoes/partials/modal_reprovar_diretor.html
  - apps/aprovacoes/urls.py
  - apps/aprovacoes/views.py
  - apps/requisicoes/admin.py
  - apps/requisicoes/forms.py
  - apps/requisicoes/models.py
  - apps/requisicoes/templates/requisicoes/partials/campos_requisicao.html
  - apps/requisicoes/templates/requisicoes/partials/copiar_dados.html
  - apps/requisicoes/templates/requisicoes/partials/historico.html
  - apps/requisicoes/templates/requisicoes/partials/requisicao_row.html
  - apps/requisicoes/templates/requisicoes/partials/status_badge.html
  - apps/requisicoes/templates/requisicoes/requisicao_detail.html
  - apps/requisicoes/templates/requisicoes/requisicao_form.html
  - apps/requisicoes/templates/requisicoes/requisicao_list.html
  - apps/requisicoes/urls.py
  - apps/requisicoes/views.py
  - config/urls.py
  - templates/base.html
findings:
  critical: 4
  warning: 7
  info: 3
  total: 14
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-06-10T00:00:00Z
**Depth:** standard
**Files Reviewed:** 27
**Status:** issues_found

## Summary

Reviewed the full Phase 2 slice: Requisição + Aprovação models, service layer, views, URLs, and templates. The FSM skeleton is sound — `select_for_update()` is used consistently, transitions are guarded, and audit logs are created inside the same `atomic()` block. The gestor unit-filter logic (empty queryset when `default_unit=None`) is correct.

Four blockers are present: (1) `AprovarDiretorView` has no ownership/authorization check at all — any authenticated Diretor can approve a requisição from any unit regardless of prior Gestor validation; (2) the HTMX `Aprovar` buttons (both levels) issue POST requests without a CSRF token and without `hx-headers`, relying purely on the global `htmx:configRequest` listener — which fires only when the HTMX script has loaded and the handler has been registered, but is not present in the modal context for `ReprovarGestorView`/`ReprovarDiretorView` error-reload paths; (3) `RequisicaoListView.get_queryset` filters by `criado_por=self.request.user` for all roles, so Gestores and Diretores see an empty list if they have never created a requisição — this silently breaks the cross-role visibility described in `_get_requisicao_para` and in the `SolicitanteRequiredMixin` docstring; (4) the `alcada` boundary condition (`>=` vs `>`) means a requisição exactly equal to `valor_maximo_gestor` is routed to the Director — this matches the wording "acima deste valor" in the admin help text but contradicts both the field name ("valor **máximo** para aprovação apenas pelo Gestor") and typical procurement rules that allow the Gestor to handle up to-and-including the limit. Seven warnings address HTMX swap breakage on error, missing `get_object_or_404` in `AprovarDiretorView`, a data-race window in the modal flow, and other robustness gaps.

---

## Critical Issues

### CR-01: `AprovarDiretorView` has no ownership or state pre-check — any Diretor can approve any requisição

**File:** `apps/aprovacoes/views.py:182-188`

**Issue:** `AprovarDiretorView.post` calls `services.aprovar_diretor(pk, request.user)` directly without first fetching the object. If the `pk` does not exist, the service raises `Requisicao.DoesNotExist` (an unhandled exception, not a `ValueError`), which produces a 500 response. More critically, no state pre-check occurs at the view layer: a raw `pk` forgery by an authenticated Director will hit `select_for_update().get(pk=requisicao_pk)` and — if the state guard inside the service happens to pass — approve a requisição the Director was never meant to see. By contrast, `AprovarGestorView` performs a unit-ownership check at line 72-74. The Director's slice deliberately omits a unit filter (D-06), but it still needs a `get_object_or_404` guard to return 404 rather than 500 on bad PKs, and a state-guard check before calling the service.

**Fix:**
```python
def post(self, request, pk):
    get_object_or_404(Requisicao, pk=pk)   # raises 404 for unknown pk
    try:
        services.aprovar_diretor(pk, request.user)
    except (ValueError, PermissionError) as e:
        return HttpResponse(str(e), status=409)
    return HttpResponse("")
```

---

### CR-02: HTMX `Aprovar` buttons send POST without CSRF token — relies on fragile global listener that is absent when partial is re-rendered

**File:** `apps/aprovacoes/templates/aprovacoes/partials/fila_row.html:9-16` and `apps/aprovacoes/templates/aprovacoes/partials/fila_diretor_row.html:9-16`

**Issue:** The "Aprovar" `<button>` elements use `hx-post` but contain no `{% csrf_token %}` and no `hx-headers` attribute with the CSRF value. They rely entirely on the `htmx:configRequest` listener injected in `base.html:13-17`, which reads the `<meta name="csrf-token">` tag. This works only when `base.html` is part of the page. However, these partials are rendered by HTMX itself as replacements (outerHTML swap). If a row partial is ever re-rendered standalone (e.g., after an error path that returns just the row), the `<script>` block in `base.html` is already present — but the CSRF `<meta>` tag must also be present. In HTMX 2.x the `configRequest` event fires per-request and the listener works as long as it remains registered. The real danger is: if someone serves the partial in isolation (Django test client, direct URL fetch, or a future refactor that drops `base.html`), CSRF protection silently disappears and the POST will be rejected with 403 — or if CSRF middleware is relaxed, it will go through unprotected.

The standard safe pattern for HTMX + Django CSRF is either `hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'` on each form/button, or wrapping the button in a `<form>` with `{% csrf_token %}`. The global listener is an acceptable shortcut for page-load elements but not for dynamically injected partials that may survive page context loss.

**Fix:** Add `hx-headers` to each HTMX POST button in both row partials:
```html
<button
  hx-post="{% url 'aprovacoes:aprovar-gestor' req.pk %}"
  hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'
  hx-target="#fila-row-{{ req.pk }}"
  hx-swap="outerHTML"
  class="btn btn-primary btn-sm"
  style="margin-right:4px;">
  Aprovar
</button>
```
Apply the same pattern to `fila_diretor_row.html`.

---

### CR-03: `RequisicaoListView.get_queryset` always filters by `criado_por=self.request.user`, so Gestores and Diretores see only their own requisições — contradicts documented cross-role visibility

**File:** `apps/requisicoes/views.py:93-98`

**Issue:** The `SolicitanteRequiredMixin` docstring (line 38-39) explicitly states "Gestores e Diretores também podem acessar (eles têm visibilidade das requisições conforme a lógica de ownership em `_get_requisicao_para`)." The helper `_get_requisicao_para` at line 64-78 implements different visibility per role: Gestor sees all requisições from their unit, Diretor sees everything. But `RequisicaoListView.get_queryset` unconditionally filters `criado_por=self.request.user`, ignoring the user's role. A Gestor who navigates to `/requisicoes/` sees only their own personal requisições — not the unit's requisições they are supposed to manage. This is a silent business-logic failure: no error, no empty-state message that explains the discrepancy, just a wrong list.

**Fix:**
```python
def get_queryset(self):
    user = self.request.user
    if user.is_superuser or user.role in ("admin", "diretor"):
        return (
            Requisicao.objects
            .select_related("categoria", "unidade")
            .order_by("-criado_em")
        )
    if user.role == "gestor":
        if not user.default_unit:
            return Requisicao.objects.none()
        return (
            Requisicao.objects
            .filter(unidade=user.default_unit)
            .select_related("categoria", "unidade")
            .order_by("-criado_em")
        )
    # solicitante / comprador — próprias apenas
    return (
        Requisicao.objects
        .filter(criado_por=user)
        .select_related("categoria", "unidade")
        .order_by("-criado_em")
    )
```

---

### CR-04: `ConfiguracaoAlcada.requer_diretor` uses `>=` boundary, routing requisições exactly equal to `valor_maximo_gestor` to the Director — contradicts field semantics

**File:** `apps/aprovacoes/models.py:100`

**Issue:** The field is named `valor_maximo_gestor` — "maximum value for Gestor approval only." The admin `help_text` reads "Acima deste valor, exige aprovação do Diretor também." These two descriptions conflict with each other and with the implementation. With `return valor >= self.valor_maximo_gestor`:

- If `valor_maximo_gestor = 10000` and `valor_estimado = 10000`, `requer_diretor` returns `True` → routed to Director.
- If `valor_maximo_gestor = 10000` and `valor_estimado = 9999.99`, `requer_diretor` returns `False` → Gestor only.

The field name says the Gestor can approve **up to** (i.e., including) `valor_maximo_gestor`. The `help_text` says Director is required only **above** that value. The operator `>=` implements "strictly above" the threshold only if the field is named "minimo_diretor", not "maximo_gestor." Procurement rules typically allow the Gestor to approve up to and including the configured limit. The current code under-authorizes Gestores by one cent relative to the documented semantics, and will silently route edge-case requisições to the Director unexpectedly.

The discrepancy between field name and `help_text` means the correct intent is ambiguous — but one of the two must change. If "maximum Gestor value" is the intent (inclusive), change the operator to `>`. If "minimum Director threshold" is the intent (exclusive for Gestor), rename the field and update `help_text`.

**Fix (assuming "maximum Gestor value" is the canonical intent):**
```python
def requer_diretor(self, valor: Decimal) -> bool:
    if self.valor_maximo_gestor is None:
        return True
    return valor > self.valor_maximo_gestor  # Gestor approves UP TO (inclusive) the maximum
```

---

## Warnings

### WR-01: Modal `Cancelar` button uses `hx-get=""` — sends GET to the current page URL, not a no-op

**File:** `apps/aprovacoes/templates/aprovacoes/partials/modal_reprovar.html:28-32` and `apps/aprovacoes/templates/aprovacoes/partials/modal_reprovar_diretor.html:28-32`

**Issue:** The "Cancelar" button in both rejection modals is:
```html
<button type="button" hx-get="" hx-target="#modal-container" hx-swap="innerHTML" class="btn btn-secondary">Cancelar</button>
```
`hx-get=""` resolves to the current page URL (the fila view). HTMX will perform a full GET request against `aprovacoes/fila/` or `aprovacoes/fila-diretor/`, inject the full HTML response into `#modal-container`, and corrupt the page. The intent is clearly to dismiss the modal by clearing `#modal-container`. An empty GET response is not what `FilaGestorView` returns — it returns a full page.

**Fix:** Remove the HTMX attributes and use a plain `onclick`:
```html
<button type="button"
        onclick="document.getElementById('modal-container').innerHTML=''"
        class="btn btn-secondary">Cancelar</button>
```
Or, if keeping HTMX style, use a dedicated "empty partial" endpoint that returns `""`.

---

### WR-02: HTMX swap target mismatch on modal form validation error — modal content is swapped into the wrong container

**File:** `apps/aprovacoes/views.py:117-120` and `apps/aprovacoes/views.py:217-220`

**Issue:** When `ReprovarGestorView.post` returns the modal partial with form errors, the HTMX response replaces `hx-target` of the original request. The form `hx-target="#fila-row-{{ requisicao.pk }}"` (set in `modal_reprovar.html:7-8`). On a validation failure (HTTP 200), HTMX replaces the `<tr id="fila-row-X">` row with the modal HTML — rendering a `<div class="card">` inside a table row, which is invalid HTML and visually breaks the table layout. The modal HTML should swap back into `#modal-container`, not into the row.

The root cause: the form in the modal posts to `reprovar-gestor` and the form's `hx-target` points at the row (correct for success, wrong for error). HTMX does not distinguish targets by response status when `hx-swap` is `outerHTML`.

**Fix:** Use HTMX response headers on the error response to retarget the swap, or use a separate `hx-target` for error responses via `HX-Retarget`:
```python
# In ReprovarGestorView.post, on validation failure:
from django_htmx.http import reswap, retarget
response = render(request, "aprovacoes/partials/modal_reprovar.html", {...}, status=422)
retarget(response, "#modal-container")
reswap(response, "innerHTML")
return response
```
Apply the same fix to `ReprovarDiretorView`.

---

### WR-03: `RequisicaoCancelarView` returns the row partial after cancel — but the cancel button is only visible on the list page, not on the detail page; wrong redirect on non-HTMX path from detail page

**File:** `apps/requisicoes/views.py:249-255`

**Issue:** On HTMX cancel from the list, returning `requisicao_row.html` with status `CANCELADO` is correct — the row updates in place. However, the cancel button also appears on `requisicao_detail.html` (line 13-19), and on that page the HTMX attributes are:
```html
hx-target="body"
hx-swap="none"
hx-on::after-request="if(event.detail.successful) window.location.href='...'"
```
This means on the detail page, the HTMX response is not used at all (`hx-swap="none"`). The `render(request, "requisicoes/partials/requisicao_row.html", ...)` response is thrown away. The `window.location.href` redirect then navigates correctly. This wastes a DB query and a template render, but more importantly: if `hx-swap` is `none`, HTMX marks the request as "successful" based on status code. A 409 from the view causes `event.detail.successful` to be `false`, so the redirect doesn't happen — the user sees no feedback at all (the `HttpResponse(str(exc), status=409)` body is discarded by `hx-swap="none"`).

**Fix:** On the detail page, change the HTMX pattern so errors are surfaced. Alternatively, return an `HttpResponseClientRedirect` for HTMX requests and let the browser redirect handle both success and error cases uniformly via Django messages.

---

### WR-04: `StatusBadgeView` polling replaces its own container — loses `hx-get` attribute after first poll

**File:** `apps/requisicoes/templates/requisicoes/requisicao_detail.html:29-33`

**Issue:** The polling span:
```html
<span id="status-badge-container"
      hx-get="{% url 'requisicoes:status' requisicao.pk %}"
      hx-trigger="every 15s"
      hx-swap="outerHTML">
```
uses `hx-swap="outerHTML"`. The `StatusBadgeView` returns `partials/status_badge.html`, which renders a `<span class="badge ...">` with **no** `hx-get`, `hx-trigger`, or `id` attributes. After the first poll fires, the entire polling `<span id="status-badge-container" ...>` is replaced by a bare badge `<span>`. Subsequent polls never happen — the 15-second polling silently stops after one cycle.

**Fix:** Change to `hx-swap="innerHTML"` so the outer `<span>` (with the polling attributes) is preserved:
```html
<span id="status-badge-container"
      hx-get="{% url 'requisicoes:status' requisicao.pk %}"
      hx-trigger="every 15s"
      hx-swap="innerHTML">
  {% include "requisicoes/partials/status_badge.html" %}
</span>
```

---

### WR-05: `CopiarDadosView.get` does not restrict access by role — any authenticated user (including Gestor/Diretor) can prefill a create form using any requisição `criado_por` themselves

**File:** `apps/requisicoes/views.py:281-304`

**Issue:** The ownership check on line 285-287 filters `Requisicao.objects.get(pk=origem_pk, criado_por=request.user)`. This correctly prevents a user from copying another user's requisição data. However, because `SolicitanteRequiredMixin` allows all authenticated users (line 46), a Gestor or Diretor who happens to have created a requisição themselves (before being promoted, or via admin) can also access this endpoint and copy data into a new requisição form. This is a minor policy concern, but the ownership filter (`criado_por=request.user`) is a sufficient guard — the concern is only that Gestores and Diretores reaching the create form at all is not documented as intentional. No code change required if the intent is "all roles can create requisições." Document the intent.

Additionally, `origem_pk` comes from `request.GET` and is passed directly to a queryset filter. It is not validated as an integer before use. If a non-integer is passed, Django will raise a `ValueError` ("invalid literal for int()...") in the ORM call, which `get_object_or_404` does not catch — it will propagate as an unhandled 500.

**Fix:**
```python
origem_pk = request.GET.get("requisicao_origem")
if origem_pk:
    try:
        origem_pk_int = int(origem_pk)
    except (ValueError, TypeError):
        form = RequisicaoForm(user=request.user)
    else:
        origem = get_object_or_404(Requisicao, pk=origem_pk_int, criado_por=request.user)
        # ... build initial_data
```

---

### WR-06: `_notificar_gestores` sends unescaped user-controlled content in email subject line — header injection risk

**File:** `apps/aprovacoes/services.py:235`

**Issue:**
```python
assunto = f"[ComprasNexos] Nova requisicao aguardando aprovacao -- {req.descricao[:50]}"
```
`req.descricao` is a free-text field entered by the Solicitante. A malicious Solicitante can include newline characters (`\n`) in the description to inject additional email headers (e.g., `\nBcc: attacker@example.com`). While Django's `send_mail` uses the `email.message` module which sanitizes headers in Python 3, the standard library's `Header` class will raise `BadHeaderError` if the subject contains a newline — this turns into an unhandled exception inside the `on_commit` callback (after the transaction has committed), silently failing email delivery for legitimate requisições whose descriptions happen to contain a literal `\n`.

The `fail_silently=True` on line 254 swallows the exception at the SMTP layer but not at the `BadHeaderError` / subject construction stage, which happens before `send_mail` is called.

**Fix:** Strip or replace newlines in the subject:
```python
descricao_safe = req.descricao[:50].replace('\n', ' ').replace('\r', ' ')
assunto = f"[ComprasNexos] Nova requisicao aguardando aprovacao -- {descricao_safe}"
```

---

### WR-07: `AprovacaoLog.evento` field `max_length=20` is too short for the longest choice value

**File:** `apps/aprovacoes/models.py:40`

**Issue:** `evento = models.CharField(max_length=20, choices=Evento.choices)`. The longest `Evento` value is `"APROVACAO_GESTOR"` (16 chars) — currently within 20. However, `"APROVACAO_FINAL"` is 15 chars and `"CANCELAMENTO"` is 12. This is fine today, but `max_length=20` provides only 4 characters of headroom. More importantly, Django does **not** enforce `max_length` at the database level for `CharField` with `choices` in all backends, but a future migration that adds a longer event name will silently truncate data on PostgreSQL if the column is not altered. The correct practice is to set `max_length` to the actual maximum of the choices.

`max(len(v) for v in [e.value for e in AprovacaoLog.Evento])` = `len("APROVACAO_GESTOR")` = 16. Setting `max_length=20` is safe, but should be documented or set to exactly 20 if future extensibility is intended. This is a low-severity robustness issue, not a current bug.

**Fix:** Explicit and self-documenting — either keep 20 and add a comment, or derive it:
```python
evento = models.CharField(
    max_length=20,  # longest current value: APROVACAO_GESTOR (16)
    choices=Evento.choices,
)
```
No migration needed.

---

## Info

### IN-01: `SolicitanteRequiredMixin` allows all authenticated users — name is misleading and docstring is inaccurate

**File:** `apps/requisicoes/views.py:33-46`

**Issue:** The mixin is named `SolicitanteRequiredMixin` but the `dispatch` method (line 42-46) allows every authenticated user through with no role check. The docstring says "Gestores e Diretores também podem acessar" — but so can Compradores, which is not mentioned. If the intent is "any authenticated user can reach these views", the mixin should either be renamed `LoginRequiredMixin` (or just inherit from it directly) or the docstring should be corrected to match. The name will mislead the next developer into thinking a role filter exists.

**Fix:** Rename to `AnyAuthenticatedMixin` or remove the class and use `LoginRequiredMixin` directly. Update docstring.

---

### IN-02: `base.html` navigation link active-state logic for `aprovacoes` is fragile — false positive on all `/aprovacoes/*` sub-paths

**File:** `templates/base.html:41`

**Issue:** The "Aprovações" (Gestor) nav item uses:
```django
{% if 'aprovacoes' in request.path and request.resolver_match.url_name != 'fila-diretor' %}is-active{% endif %}
```
This marks the Gestor fila as active for **all** `aprovacoes/` paths that are not exactly `fila-diretor` — including `aprovacoes/<pk>/aprovar/`, `aprovacoes/<pk>/reprovar/`, and `aprovacoes/<pk>/modal-reprovar/`. These routes don't render full pages (they return HTMX partials) so the nav is never shown in those responses. Currently benign, but the condition is semantically wrong and will mislead any developer checking nav logic.

**Fix:** Use `request.resolver_match.url_name == 'fila-gestor'` for precise matching.

---

### IN-03: `campos_requisicao.html` inline `<script>` runs `querySelectorAll` before form fields are in the DOM on initial page load

**File:** `apps/requisicoes/templates/requisicoes/partials/campos_requisicao.html:26-29`

**Issue:** The script:
```javascript
document.querySelectorAll('#form-container input, #form-container select, #form-container textarea').forEach(function(el) {
  el.classList.add(el.tagName.toLowerCase() === 'select' ? 'form-select' : 'form-input');
});
```
is placed at the end of the partial, which is included via `{% include %}` inside `#campos-requisicao` → `#form-container`. On initial page load, `DOMContentLoaded` has already fired by the time HTMX loads and swaps in the partial — so the script runs after insertion and finds the elements correctly. However, when this partial is returned as an HTMX swap target (`hx-target="#form-container"`) on form validation error, the script is re-injected and re-executes — adding duplicate CSS classes each time the form is re-submitted with errors. Duplicate `form-input form-input` classes cause no visual harm but are semantically wrong and indicate the pattern is fragile.

**Fix:** Change the script to use `classList.add` only if the class is not already present, or (better) remove the script and apply the CSS classes server-side via Django widget `attrs`:
```python
# In RequisicaoForm.__init__:
for field_name, field in self.fields.items():
    if isinstance(field.widget, forms.Select):
        field.widget.attrs.setdefault('class', 'form-select')
    else:
        field.widget.attrs.setdefault('class', 'form-input')
```

---

_Reviewed: 2026-06-10T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
