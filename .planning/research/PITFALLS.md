# Domain Pitfalls: ComprasNexos

**Domain:** Procurement management system (Django + HTMX)
**Researched:** 2026-06-10
**Confidence:** HIGH (Django/HTMX from official docs + Context7), MEDIUM (deployment, Brazil-specific)

---

## Critical Pitfalls

Mistakes that cause rewrites, data corruption, or complete feature abandonment.

---

### Pitfall C1: Not Setting a Custom User Model Before the First Migration

**What goes wrong:** The project starts with Django's default `auth.User` and later someone wants to add a `department` or `cost_center` field to the user profile. Changing `AUTH_USER_MODEL` after `0001_initial` migrations have run is not automatic — it requires manual schema surgery, data migration from the old user table, and fixing every `ForeignKey` and `ManyToManyField` that referenced the old user throughout the project.

**Why it happens:** Default `auth.User` works for the first sprint. The need for profile fields only becomes obvious once real users start enrolling.

**Consequences:** Either a painful manual migration with downtime risk, or a permanent workaround (separate `UserProfile` model with a 1-to-1 link). The 1-to-1 workaround always generates N+1 queries in templates unless `select_related('profile')` is remembered everywhere.

**Warning signs:**
- The project's `accounts` app has no `0001_initial` migration yet and there's still discussion about user fields.
- Anyone says "let's just add a OneToOneField to profile later."

**Prevention:**
- Create `accounts/models.py` with `class User(AbstractUser): pass` and set `AUTH_USER_MODEL = "accounts.User"` before running ANY migration.
- Add `department` and `centro_de_custo` directly on the custom user model from day one, even as optional nullable fields.
- The model referenced by `AUTH_USER_MODEL` must be created in the first migration of its app (`0001_initial`) — this is a hard Django constraint.

**Source:** Django 5.2 official docs — https://docs.djangoproject.com/en/5.2/topics/auth/customizing/

**Phase:** Phase 1 (Accounts). No exceptions — must be resolved before any other model references `User`.

---

### Pitfall C2: Approval State Transitions Without Database-Level Locks

**What goes wrong:** A requisition is in `status='aguardando_gestor'`. The Gestor clicks "Aprovar" twice rapidly (double-click), or two browser tabs are open. Both requests read `status='aguardando_gestor'`, both pass the permission check, and both write `status='aguardando_diretor'`. The approval log records two entries for the same transition. Worse: with concurrent approvals at different levels, a requisition can reach `aprovada` without Director approval.

**Why it happens:** Django ORM reads stale state into Python, performs conditional logic there, then writes back. Without a transaction lock, the window between read and write allows a second request through.

**Consequences:** Audit trail corruption, bypassed approval levels, financial controls broken — exactly the problem the system is supposed to prevent.

**Warning signs:**
- Status transitions are implemented as: `if req.status == 'X': req.status = 'Y'; req.save()`
- No `select_for_update()` anywhere in the approval view.
- No `transaction.atomic()` wrapping the status check + transition.

**Prevention:**
```python
from django.db import transaction

def aprovar_requisicao(request, pk):
    with transaction.atomic():
        req = Requisicao.objects.select_for_update().get(pk=pk)
        if req.status != ESTADO_ESPERADO:
            return HttpResponse("Conflito de estado", status=409)
        req.status = PROXIMO_ESTADO
        req.save()
        HistoricoAprovacao.objects.create(...)
```
- Wrap every state transition in `transaction.atomic()` with `select_for_update()`.
- Return a 409 (Conflict) if the pre-condition fails — HTMX can handle this with `hx-on::htmx:responseError`.

**Source:** Django docs — `select_for_update()`, `transaction.atomic()`

**Phase:** Phase 2 (Requisitions + Approvals). Address before any approval UI is shown to users.

---

### Pitfall C3: CNPJ Field Stored as CharField Without Format Normalization — and New Alphanumeric Format (July 2026)

**What goes wrong:** Two versions of the same CNPJ exist in the supplier table: `16.727.230/0001-97` and `16727230000197`. Lookups fail, duplicates slip through, deduplication queries become regex hell. Additionally, from July 2026 the Brazilian Receita Federal is introducing an alphanumeric CNPJ format (e.g., `12.ABC.345/01DE-35`). Any validation that assumes CNPJ is purely numeric will reject valid new suppliers.

**Why it happens:** CNPJ is displayed formatted but often pasted without formatting. Old validation regexes (`\d{14}`) reject the new alphanumeric format.

**Consequences:** Duplicate suppliers for the same company, failed validation for new-format CNPJs registered from July 2026 onward, data quality degradation in supplier reports.

**Warning signs:**
- CNPJ stored in different formats in the same table.
- Validation uses `\d{14}` regex instead of a proper library.
- No unique constraint on the compacted CNPJ.

**Prevention:**
- Use `python-stdnum` (`pip install python-stdnum`) — it already supports the new alphanumeric format as of its latest release.
- Store CNPJ in compacted form (14 chars, no separators): `stdnum.br.cnpj.compact(value)`.
- Validate with `stdnum.br.cnpj.validate(value)` — handles both old numeric and new alphanumeric formats.
- Apply a `unique=True` constraint on the compacted CNPJ field.
- Display formatted using `stdnum.br.cnpj.format(value)` in templates only.

```python
from stdnum.br.cnpj import validate, compact, InvalidFormat, InvalidChecksum

class FornecedorForm(forms.ModelForm):
    def clean_cnpj(self):
        raw = self.cleaned_data['cnpj']
        try:
            validate(raw)
        except (InvalidFormat, InvalidChecksum):
            raise forms.ValidationError("CNPJ inválido.")
        return compact(raw)  # always store compacted
```

**Source:** python-stdnum official docs — https://arthurdejong.org/python-stdnum/stdnum.br.cnpj; new alphanumeric format confirmed in library docs for July 2026.

**Phase:** Phase 3 (Suppliers). Critical: do not store a single CNPJ before this is in place.

---

### Pitfall C4: BRL Amounts Stored as FloatField

**What goes wrong:** `valor_estimado = models.FloatField()` causes floating-point rounding errors in financial totals. A requisition for R$1,234.56 + R$0.01 might total R$1,234.5699999998 in aggregate queries. Reports show wrong totals. Comparisons like `valor == 1234.56` fail silently.

**Why it happens:** `FloatField` maps to Python `float`, which uses IEEE 754 binary floating-point. BRL amounts in centavos are base-10 decimals, not representable exactly in binary.

**Consequences:** Financial reports are wrong. "Gasto do mês" dashboard KPI shows incorrect totals. Auditors reject the data.

**Warning signs:**
- Any model field for prices or estimated values uses `FloatField`.
- `SUM()` aggregations show values with many decimal places.

**Prevention:**
- Always use `DecimalField(max_digits=12, decimal_places=2)` for every monetary field.
- Use `Decimal('0.00')` literals, never `float` in Python code paths that touch money.
- In templates, use `|floatformat:2` filter and Django's `LANGUAGE_CODE = 'pt-br'` with `USE_L10N = True` for correct BRL formatting (e.g., `R$ 1.234,56`).

**Source:** Django docs — `DecimalField` vs `FloatField` (official porting guide and field reference)

**Phase:** Phase 1 (Data models). Fix before any monetary field is saved to the database.

---

## Moderate Pitfalls

Mistakes that degrade UX, create support burden, or block specific features — but don't require rewrites.

---

### Pitfall M1: N+1 Queries in Requisition List Views

**What goes wrong:** The requisition list loads `Requisicao.objects.all()` and the template accesses `req.solicitante.get_full_name()`, `req.categoria.nome`, and `req.historico_set.last()` for each row. With 50 requisitions, this becomes 150+ queries per page load.

**Why it happens:** Django lazy-loads ForeignKey and reverse relations by default. Template-level attribute access silently issues database queries.

**Consequences:** List views become noticeably slow (500ms+) as data grows. The solicitante accesses the requisition list in real time and perceives the system as slow.

**Warning signs:**
- Django Debug Toolbar shows 30+ queries on a list view.
- Query count scales linearly with the number of rows displayed.
- `req.aprovador.first_name` or similar ForeignKey traversal appears in templates.

**Prevention:**
```python
# Correct pattern for all list views
Requisicao.objects.select_related(
    'solicitante', 'categoria', 'centro_de_custo'
).prefetch_related(
    'historicoaprovacao_set'
).filter(status__in=[...])
```
- Use `select_related()` for every ForeignKey accessed in list templates.
- Use `prefetch_related()` for reverse relations and M2M.
- Install Django Debug Toolbar in development — make it a project dependency from day one.
- Write a test that asserts query count for list views: `with self.assertNumQueries(3): response = self.client.get(url)`.

**Phase:** Phase 2 (Requisitions). Set the pattern once and apply to all subsequent list views.

---

### Pitfall M2: HTMX CSRF Rejection on All Non-GET Requests

**What goes wrong:** HTMX forms submit via AJAX but don't include the CSRF token in the request header. Django's CSRF middleware rejects all POST/PUT/DELETE requests with 403 Forbidden. The developer sees a 403 and doesn't understand why — the form looks correct.

**Why it happens:** Standard HTML forms include the CSRF token in POST body via `{% csrf_token %}`. HTMX sends AJAX requests without this unless explicitly configured. The `hx-headers` attribute on `<body>` is the canonical fix, but it's easy to forget.

**Consequences:** Every approval action, form submission, and delete action silently fails with a 403. If HTMX is configured to swap on any response, users see nothing — the form just resets.

**Warning signs:**
- 403 responses in the browser network tab after clicking any HTMX-driven button.
- `{% csrf_token %}` is in the template but HTMX requests still fail.

**Prevention:**
Put this in `base.html` once and never think about it again:
```html
{% load django_htmx %}
<body hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'>
  {% htmx_script %}
  ...
</body>
```
This injects the CSRF token as a header on every HTMX request globally. The `django-htmx` package's `{% htmx_script %}` tag loads the library correctly.

**Source:** django-htmx official docs — https://django-htmx.readthedocs.io/

**Phase:** Phase 1 (Base template setup). Set once in the base template before any HTMX interaction is built.

---

### Pitfall M3: Partial Template Responses That Re-Render the Entire Page

**What goes wrong:** An HTMX approval button triggers a POST. The view returns `render(request, 'requisicoes/list.html', context)` — the full page template. HTMX replaces the target div with the entire HTML document, including `<head>`, `<body>`, and nav. The page breaks visually. Or worse: the developer checks `if request.htmx:` but forgets to pass the `request` attribute because `django-htmx` middleware is not installed.

**Why it happens:** Without `django-htmx` middleware, `request.htmx` does not exist. Without partial templates, every HTMX response is a full page.

**Consequences:** Broken UI on partial updates, flash of unstyled content, nested `<html>` tags in the DOM.

**Warning signs:**
- HTMX swaps show the navigation bar inside a content area.
- `request.htmx` throws `AttributeError`.
- Partial updates reload scripts and stylesheets.

**Prevention:**
1. Add `django_htmx.middleware.HtmxMiddleware` to `MIDDLEWARE` — this adds `request.htmx`.
2. Use `django-template-partials` for inline partial definitions:
```python
def aprovar(request, pk):
    # ... approval logic
    template = "requisicoes/list.html"
    if request.htmx:
        template += "#requisicao-row"  # django-template-partials syntax
    return render(request, template, context)
```
3. Alternatively, keep a dedicated `_partial.html` base template that extends nothing.

**Source:** django-htmx docs — Partial Rendering section.

**Phase:** Phase 2 (first HTMX interaction). Establish the pattern before building the approval UI.

---

### Pitfall M4: Approval Workflow Users Learn to Bypass

**What goes wrong:** Gestores discover they can approve requisitions above their alçada threshold because the validation only happens client-side (the "Aprovar" button is hidden, but the POST endpoint is unprotected). Or: the Diretor approval is skipped because the Comprador starts an RFQ on a requisition still in `aguardando_diretor` status.

**Why it happens:** Permission checks are added to templates (button visibility) but not to views (server-side enforcement). Status preconditions are checked in the UI but not in the RFQ creation endpoint.

**Consequences:** Financial controls are bypassed. The system becomes as unreliable as the spreadsheet it replaced. The client loses trust.

**Warning signs:**
- Approval buttons are hidden in templates but the POST URL is unprotected.
- RFQ creation view does not assert `requisicao.status == 'aprovada'`.
- Alçada (approval threshold by value) is checked in JavaScript or template only.

**Prevention:**
- Every state-changing view must start with an explicit precondition guard:
```python
def criar_rfq(request, requisicao_pk):
    req = get_object_or_404(Requisicao, pk=requisicao_pk)
    if req.status != 'aprovada':
        return HttpResponseForbidden("Requisição não aprovada.")
    if request.user.profile.role != 'comprador':
        return HttpResponseForbidden()
    ...
```
- Alçada validation: check `req.valor_estimado <= current_user.threshold` server-side, every time.
- Write one test per permission boundary — they're fast and catch regressions.

**Phase:** Phase 2 (Approvals). Every view that transitions state needs a server-side guard.

---

### Pitfall M5: Email Delivery Ends Up in Spam (or Fails Silently)

**What goes wrong:** The system sends email to the Gestor when a new requisition is created. The emails land in spam or are silently dropped because: (a) the EC2 instance sends email directly on port 25, which most ISPs and corporate mail servers block; (b) SPF record for the sending domain does not include the EC2 IP; (c) no DKIM signing; (d) Django is configured with `EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'` in production because the developer forgot to change it.

**Why it happens:** Email is easy to set up locally (console backend) and easy to overlook in production. SPF/DKIM are infrastructure concerns often left for "later."

**Consequences:** Gestores never get notified, requisitions sit unreviewed, the client says the system "doesn't work." Discovery happens weeks into production.

**Warning signs:**
- `EMAIL_BACKEND` not overridden per environment via environment variables.
- No SES or transactional email service configured.
- No test email sent during deploy verification.

**Prevention:**
- Use **Amazon SES** (same AWS account, simplest integration): configure SMTP credentials, set `EMAIL_HOST = 'email-smtp.us-east-1.amazonaws.com'`, port 587, TLS.
- Verify the sending domain in SES; this generates SPF and DKIM records automatically.
- Use environment variables for all email settings — never hardcode in `settings.py`.
- Add a deploy checklist step: send a test email to a real inbox and check headers for DKIM pass.
- Django 5.x uses `MAILERS` dict config; migrate from legacy `EMAIL_*` settings to avoid the deprecation warning in Django 7.0.

**Source:** Django 5.2 email docs (MAILERS setting, SMTP backend).

**Phase:** Phase 2 (Notifications). Configure SES before shipping any approval notification.

---

### Pitfall M6: RFQ Process Friction Causes Abandonment

**What goes wrong:** The Comprador must open the RFQ, add suppliers one by one, enter each price manually, save, then come back to compare. If the form is multi-step and loses state on validation error, the Comprador gives up and goes back to their spreadsheet. The system ends up with RFQs in `rascunho` (draft) that are never completed.

**Why it happens:** Multi-step forms in Django without server-side session state lose data on browser back. Form validation errors that clear file inputs or dynamic rows are especially frustrating.

**Consequences:** Low RFQ completion rate. The procurement cycle data is incomplete. Reports become useless. The core value proposition of the system disappears.

**Warning signs:**
- RFQ form is built as a single monolithic page with many required fields.
- Validation errors reset the supplier list the Comprador already entered.
- No draft/save functionality.

**Prevention:**
- Allow saving an RFQ as `rascunho` from the start — one button, no required fields validation.
- Use HTMX to add supplier quote rows dynamically (inline `hx-post` to add a row, `hx-delete` to remove one) without a page reload.
- Server-side: save each quote line immediately when added (auto-save pattern) rather than on final submit.
- File inputs inside HTMX-swapped forms lose their value on re-render — use `hx-preserve` on file inputs or keep them outside the swapped region.

**Source:** HTMX docs — `hx-preserve` for file inputs.

**Phase:** Phase 4 (RFQ/Quotations). Design the UX flow before building forms.

---

### Pitfall M7: Supplier Data Becomes Stale and Unmanaged

**What goes wrong:** Suppliers are created once and never updated. Phone numbers and email contacts become stale within 6 months. The rating system (`avaliacao_fornecedor`) is never used because there is no prompt or reminder. A supplier is marked "ativo" but has not been used in 2 years.

**Why it happens:** Supplier management is treated as a one-time data entry task. No workflow drives ongoing data quality.

**Consequences:** Comprador calls old phone numbers, emails bounce, rating history is empty, the "fornecedores ativos" KPI is meaningless.

**Warning signs:**
- Supplier form has no `data_ultima_atualizacao` field.
- No prompt to rate a supplier after an RFQ is closed.
- All suppliers are `status='ativo'` regardless of activity.

**Prevention:**
- Add `ultima_atualizacao = models.DateTimeField(auto_now=True)` to `Fornecedor`.
- Add a `status` field: `ativo`, `inativo`, `bloqueado` — and surface it in the supplier list.
- After RFQ winner selection, redirect to or surface a supplier rating prompt (one-click, 1–5 stars + optional comment). Make it part of the "close RFQ" flow, not a separate task.
- Dashboard KPI: flag suppliers not updated in 180 days.

**Phase:** Phase 3 (Suppliers) for the model; Phase 4 (RFQ) for the post-RFQ rating prompt.

---

### Pitfall M8: Dashboard Reports Nobody Uses (Data Quality Problem)

**What goes wrong:** The "Gasto por categoria" report shows categories like `None` or `Outros` for 60% of requisitions because solicitantes left the category field blank or selected the default. The "comparativo de cotações" shows nothing because RFQs were never completed. The dashboard looks busy but contains no actionable information.

**Why it happens:** Reports are built before data quality constraints are enforced. Optional fields in the requisition form produce null-heavy datasets.

**Consequences:** Client opens the dashboard once, sees garbage, closes it, and never returns. The reporting feature is delivered but has zero adoption.

**Warning signs:**
- `categoria` is nullable in the Requisicao model.
- RFQ is not required before a purchase is recorded.
- No data in the first week of production (real test of the pipeline).

**Prevention:**
- Make `categoria` and `centro_de_custo` required fields in the requisition form — not nullable at the model level.
- Populate the dashboard KPIs with real data from the first week of use, before the first review meeting with the client.
- "Comparativo de cotações" should only appear once there are at least 2 completed RFQs — otherwise show an empty state with instructions, not a broken chart.
- Build reports after a 2-week real-use period, not before.

**Phase:** Phase 5 (Reports). Define required fields in Phase 2 (Requisitions) — don't defer to report phase.

---

## Minor Pitfalls

Manageable annoyances that create technical debt if ignored.

---

### Pitfall L1: Django Signals for Email Notifications — Hidden Coupling and Test Complexity

**What goes wrong:** Approval notifications are wired via `post_save` signals on the `Requisicao` model. This works initially, but signals fire during test fixtures, during Django Admin bulk operations, and during data migrations — causing spurious emails and test failures. Debugging "why did this email get sent?" becomes a 30-minute investigation.

**Prevention:**
- Use explicit service function calls in views rather than signals for email notifications: `enviar_notificacao_gestor(requisicao)` called explicitly after `req.save()`.
- If signals are used, always check `kwargs['raw']` to skip signal logic during fixture loading.
- Mock the email service in tests, not the signal.

**Phase:** Phase 2 (Notifications). Decide the pattern once at the start.

---

### Pitfall L2: ReportLab PDF Generation Blocks the Request Thread

**What goes wrong:** Generating a "Relatório de gastos" PDF for a 6-month period with 500 requisitions takes 3–8 seconds. During this time, the Django worker thread is blocked. With 3 concurrent PDF requests and Gunicorn's default 2 workers, the server appears unresponsive.

**Prevention:**
- For v1 (20 users, small scale): acceptable if PDF generation stays under 2 seconds for typical queries.
- Add a `?periodo=30` query parameter defaulting to 30-day windows to limit dataset size.
- Use `StreamingHttpResponse` for large reports, or simply bound report date ranges.
- Do NOT use Celery for this at v1 scale — it's over-engineering for 20 users.
- If reports grow slow: generate PDF synchronously but cache the result for 5 minutes with a simple cache key (date range + user).

**Phase:** Phase 5 (Reports). Test with realistic data volume before shipping.

---

### Pitfall L3: HTMX hx-push-url + Browser Back Button Shows Partial HTML

**What goes wrong:** A list view uses `hx-push-url="true"` so the URL updates when filtering. The user hits the browser back button. HTMX restores from its DOM snapshot cache — but if the snapshot is stale or the cache was cleared, the server returns only the partial HTML (because the URL was for a partial), and the full page layout breaks.

**Prevention:**
- Always ensure HTMX-pushed URLs can serve a full page on direct navigation (i.e., the view renders the full template when `request.htmx` is False).
- Test: copy-paste a URL from the address bar into a new tab — it must render the full page correctly.
- Only use `hx-push-url` for navigation-meaningful URLs (list filters, page transitions), not for inline widget updates.

**Phase:** Phase 2+ (any view using hx-push-url). Verify with the browser back button during QA.

---

### Pitfall L4: Docker Container on EC2 Without a Restart Policy

**What goes wrong:** The EC2 instance reboots (patching, spot interruption, kernel update). The Docker container does not restart. The system is down. The client calls saying "o sistema não abre." The developer SSHes in and runs `docker start` manually.

**Prevention:**
- Always run with `--restart=unless-stopped` or equivalent `restart: unless-stopped` in `docker-compose.yml`.
- Run Gunicorn as PID 1 inside the container, not wrapped in shell scripts that can fail silently.
- Configure a CloudWatch alarm on the EC2 instance health check — alerts if the instance is unreachable for > 2 minutes.

**Phase:** Phase 1 (Deployment). Include in the Docker Compose file from the beginning.

---

### Pitfall L5: PostgreSQL on RDS Without Tested Restore Procedure

**What goes wrong:** RDS automated backups are enabled. A data corruption event occurs (or a client accidentally deletes all suppliers). The developer goes to restore from backup and discovers: (a) they have never actually done a restore from RDS snapshots, (b) the restored instance has a different endpoint, which means the Django `DATABASE_URL` environment variable needs updating, (c) the restore takes 20 minutes. The client is down for 45 minutes.

**Prevention:**
- Run a restore drill once, before go-live: restore from RDS snapshot to a test instance, point the staging Django config at it, verify the app works.
- Document the restore steps in a runbook (even a single-page document) — specifically: how to update the `DATABASE_URL` environment variable in the Docker container after pointing to a restored RDS instance.
- RDS automatic backups: set retention to 7 days minimum. Enable deletion protection.
- Run `manage.py migrate --check` as part of the Docker container entrypoint to catch migration mismatches on startup.

**Phase:** Phase 1 (Deployment setup). Tested before go-live.

---

### Pitfall L6: Over-Engineering the Permission System

**What goes wrong:** The developer models permissions using Django's object-level permission system (django-guardian or similar), creates permission groups for every role-action combination, and wires up 20 custom permissions. Two months later, the client says "o Diretor também precisa aprovar cotações." Changing the permission model requires database migrations, permission reassignment, and testing 20 combinations.

**Why it happens:** Five roles (Solicitante, Gestor, Comprador, Diretor, Admin) can look like a complex RBAC problem. It isn't — the roles are simple and the scope is 20 users.

**Prevention:**
- Model roles as a `CharField(choices=...)` on the user profile. Simple role check: `user.profile.role == 'gestor'`.
- Implement permission logic in a single `permissions.py` module per app (plain functions: `pode_aprovar_requisicao(user, requisicao) -> bool`).
- Do NOT use django-guardian for v1. The overhead of object-level permissions is not justified for 20 users with 5 roles.
- The alçada (approval threshold) is the only complexity: store as a configurable model (`AlcadaAprovacao(nivel, valor_minimo, valor_maximo, requer_diretor)`) editable via Django Admin — no code change needed to adjust thresholds.

**Phase:** Phase 1 (Accounts). Keep it simple; model complexity when the client actually asks for it.

---

### Pitfall L7: ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS Not Set for Production Domain

**What goes wrong:** The Docker container runs behind an Application Load Balancer or Nginx reverse proxy. The `Host` header Django sees is the internal container hostname, not the client's domain. `ALLOWED_HOSTS = ['*']` is set temporarily to "fix" this. CSRF validation fails on POST requests because the `Origin` header is `https://comprasnexos.client.com.br` but `CSRF_TRUSTED_ORIGINS` only contains `http://localhost`.

**Consequences:** Either CSRF is broken (403s on all forms) or `ALLOWED_HOSTS = ['*']` is left in production (security risk).

**Prevention:**
```python
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost'])
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=['http://localhost'])
```
- Both must be set via environment variables in the Docker Compose / ECS task definition.
- `CSRF_TRUSTED_ORIGINS` must include the full scheme + domain: `https://compras.clientedomain.com.br`.
- Behind a reverse proxy: set `USE_X_FORWARDED_HOST = True` and trust the `REMOTE_ADDR` from the proxy.

**Source:** Django docs — ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS settings reference.

**Phase:** Phase 1 (Deployment). Must be part of the environment variable spec.

---

## Phase-Specific Warning Matrix

| Phase Topic | Most Likely Pitfall | Mitigation |
|-------------|--------------------|--------------------|
| Phase 1: Accounts & Auth | Custom User Model too late (C1) | Create `accounts.User(AbstractUser)` before any migration |
| Phase 1: Accounts & Auth | Role system over-engineered (L6) | Simple `role` CharField, plain permission functions |
| Phase 1: Data Models | BRL as FloatField (C4) | `DecimalField(max_digits=12, decimal_places=2)` everywhere |
| Phase 1: Deployment | Container restart policy missing (L4) | `restart: unless-stopped` in docker-compose |
| Phase 1: Deployment | ALLOWED_HOSTS / CSRF misconfigured (L7) | Env vars; test with real domain before go-live |
| Phase 2: Requisitions | State transition race condition (C2) | `select_for_update()` + `transaction.atomic()` |
| Phase 2: Requisitions | N+1 on list views (M1) | `select_related` + Debug Toolbar from day one |
| Phase 2: Approvals | Server-side bypass possible (M4) | Guard every view, test every permission boundary |
| Phase 2: Notifications | Email in spam / not sent (M5) | SES, SPF/DKIM, test send on deploy |
| Phase 2: Notifications | Signals cause spurious emails in tests (L1) | Explicit service calls, not post_save signals |
| Phase 2: HTMX | CSRF 403 on all forms (M2) | `hx-headers` on `<body>` in base template |
| Phase 2: HTMX | Full page in partial swap (M3) | `django-htmx` middleware + template partials |
| Phase 3: Suppliers | CNPJ stored unnormalized (C3) | `python-stdnum` validate + compact + unique constraint |
| Phase 3: Suppliers | New alphanumeric CNPJ format rejected (C3) | `stdnum.br.cnpj.validate()` handles new format |
| Phase 3: Suppliers | Supplier data goes stale (M7) | `auto_now=True`, status field, post-RFQ rating prompt |
| Phase 4: RFQ | Form friction causes abandonment (M6) | Auto-save draft, dynamic inline rows via HTMX |
| Phase 4: RFQ | File input lost on HTMX re-render (M6) | `hx-preserve` on file inputs |
| Phase 5: Reports | Data quality makes reports useless (M8) | Required fields at model level; verify data pipeline early |
| Phase 5: Reports | PDF generation blocks thread (L2) | Bound date ranges; cache results; no Celery at this scale |
| Any: Navigation | hx-push-url breaks browser back (L3) | Ensure direct URL access always renders full page |
| Post-go-live | Backup never tested (L5) | Restore drill before go-live, document procedure |

---

## Sources

- Django 5.2 official docs — AUTH_USER_MODEL, select_for_update, DecimalField, CSRF, email (MAILERS): https://docs.djangoproject.com/en/5.2/
- django-htmx official docs — CSRF headers, partial rendering, HtmxMiddleware: https://django-htmx.readthedocs.io/
- HTMX official docs — validation, hx-push-url, hx-preserve, hx-headers: https://htmx.org/docs/
- python-stdnum — CNPJ validation including new alphanumeric format (July 2026): https://arthurdejong.org/python-stdnum/stdnum.br.cnpj
- Django docs — select_related/prefetch_related query optimization: https://docs.djangoproject.com/en/5.2/ref/models/querysets/#select-related
- Django docs — transaction.atomic() and select_for_update(): https://docs.djangoproject.com/en/5.2/topics/db/transactions/
- All Django source verified via Context7 (/django/django) — HIGH confidence
- All HTMX details verified via Context7 (/bigskysoftware/htmx) — HIGH confidence
- Deployment and Brazil-specific pitfalls synthesized from official docs + domain knowledge — MEDIUM confidence
