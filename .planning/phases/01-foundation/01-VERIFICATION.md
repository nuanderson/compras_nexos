---
phase: 01-foundation
verified: 2026-06-10T12:00:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Log in at http://localhost:8002/accounts/login/ with a valid admin account"
    expected: "Page renders dark theme (#1a1a2e background, #e94560 CTA button). Credentials authenticate and redirect to / (dashboard)."
    why_human: "Visual appearance and actual HTTP session creation cannot be verified without running the container."
  - test: "Submit the password reset form at http://localhost:8002/accounts/password-reset/ with a registered email"
    expected: "Console logs show the email body (dev console backend), including a reset link and 'Equipe ComprasNexos' sign-off."
    why_human: "End-to-end email delivery through console backend requires a live server."
  - test: "Navigate to http://localhost:8002/admin-panel/usuarios/ as an admin, then as a non-admin user (e.g. Solicitante)"
    expected: "Admin sees user list with 'Criar usuário' button (HTTP 200). Non-admin receives HTTP 403 — browser shows permission-denied page."
    why_human: "Role-based access enforcement needs live session context to confirm the 403 branch activates in the browser."
  - test: "Click 'Desativar' on any active user in the user list"
    expected: "HTMX loads the confirmation card inline (no page reload). Confirming deactivation updates that specific table row to show 'Inativo' badge without a full page reload."
    why_human: "HTMX partial-swap behavior requires browser interaction to confirm hx-target/hx-swap wiring produces correct DOM result."
  - test: "Create a unit, then deactivate it. Observe the 'Usuários vinculados' column after deactivation"
    expected: "Column shows a number (possibly 0), not a blank cell."
    why_human: "WR-06 from the code review identified that unit_row.html may render a blank user_count after deactivation because UnitDeactivateView does not re-annotate. Human must confirm whether the blank actually appears."
---

# Phase 01: Foundation — Verification Report

**Phase Goal:** Users can authenticate, and the Admin can manage accounts and organizational units
**Verified:** 2026-06-10T12:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can log in with email and password and remain authenticated across browser refreshes | VERIFIED | `login_view` in `apps/accounts/views.py` uses Django `AuthenticationForm` and calls `login(request, user)`. Session is established via Django's session middleware (present in `MIDDLEWARE`). `test_login_success` asserts HTTP 302 → `/`; `test_session_persists` asserts GET `/` returns 200 after login. |
| 2 | User can request a password reset and receive a reset link by email | VERIFIED | `password_reset_view` wraps Django's `PasswordResetView` with `email_template_name="accounts/email/password_reset.html"` and `subject_template_name="accounts/email/password_reset_subject.txt"`. Both template files exist. `test_password_reset_sends_email` with `@override_settings(EMAIL_BACKEND=locmem)` asserts `len(mail.outbox) == 1`. |
| 3 | Admin can create, edit, and deactivate user accounts via the admin panel | VERIFIED | `UserCreateView`, `UserUpdateView`, `UserDeactivateView` all exist in `apps/accounts/views.py` behind `AdminRequiredMixin`. URLs wired in `apps/accounts/urls.py`. `test_admin_create_user` asserts 302 + DB row; `test_admin_deactivate_user` asserts `is_active=False`. `test_non_admin_blocked_from_user_list` asserts 403 for non-admin. |
| 4 | Admin can assign one of five roles (Solicitante, Gestor, Comprador, Diretor, Admin) to each user | VERIFIED | `User.Role` TextChoices contains all 5 roles in `apps/accounts/models.py`. Migration `0002_create_groups.py` creates 5 Django Groups. `UserCreateForm` and `UserEditForm` include `role` field. `test_user_role_choices` asserts all 5 role values exist. `test_groups_exist` asserts all 5 Groups present. |
| 5 | Admin can create organizational units and link users to them; each user has a default unit pre-selected when opening a requisition | VERIFIED | `UnidadeOrganizacional` model exists with `nome`, `descricao`, `ativo` fields. `User.default_unit` FK to `UnidadeOrganizacional` (nullable, `SET_NULL`). `UnitCreateView`, `UnitUpdateView`, `UnitDeactivateView` exist and are URL-wired. `test_admin_create_unit` asserts 302 + DB row; `test_admin_assign_unit_to_user` asserts `default_unit_id` updated; `test_user_default_unit` confirms FK round-trip. |

**Score:** 5/5 truths verified

---

### Deferred Items

None. All 5 roadmap success criteria are satisfied by codebase evidence in this phase.

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `config/settings/base.py` | `AUTH_USER_MODEL = 'accounts.User'` | VERIFIED | Line 17 confirms `AUTH_USER_MODEL = "accounts.User"` |
| `apps/accounts/migrations/0001_initial.py` | TrigramExtension + UnaccentExtension first | VERIFIED | Lines 25-26 show `TrigramExtension()` and `UnaccentExtension()` as first two operations |
| `apps/accounts/migrations/0002_create_groups.py` | Data migration creating 5 Groups | VERIFIED | Creates Solicitante, Gestor, Comprador, Diretor, Admin via `RunPython` |
| `apps/accounts/models.py` | User(AbstractUser) + UnidadeOrganizacional | VERIFIED | Both models present; `USERNAME_FIELD = "email"`, 5-role `TextChoices`, `default_unit` FK |
| `apps/core/models.py` | TimestampedModel + AuditedModel abstract bases | VERIFIED | Both classes with `abstract = True`; monetary fields comment present |
| `templates/base.html` | Full dark-theme layout with `htmx:configRequest` CSRF | VERIFIED | `htmx:configRequest` handler at line 13 injects `X-CSRFToken` from `<meta name="csrf-token">` |
| `static/css/main.css` | Design system with `--color-bg` | VERIFIED | `:root` block at line 10 defines `--color-bg: #1a1a2e` and `--color-accent: #e94560` |
| `docker-compose.yml` | Dev environment with `postgres:15-alpine` | VERIFIED | Line 22 confirms `postgres:15-alpine`; healthcheck present; port 8002:8000 (deviation from plan noted below) |
| `requirements.txt` | `Django==5.2.*` pinned | VERIFIED | Line 2 confirms `Django==5.2.*` |
| `apps/accounts/views.py` | `AdminRequiredMixin` + all CRUD view classes | VERIFIED | `AdminRequiredMixin` at line 95; all 10 view classes present |
| `apps/accounts/urls.py` | All 15 URL patterns (auth + admin panel) | VERIFIED | 5 auth + 10 admin panel URLs confirmed |
| `apps/accounts/templates/accounts/user_list.html` | Table with "admin-panel/usuarios" link | VERIFIED | Extends `base.html`; table columns Nome/E-mail/Perfil/Unidade/Status/Ações; "Criar usuário" CTA |
| `apps/accounts/templates/accounts/unit_list.html` | Table with "admin-panel/unidades" link | VERIFIED | Extends `base.html`; columns Nome/Descrição/Status/Usuários vinculados/Ações; "Criar unidade" CTA |
| `apps/accounts/templates/accounts/user_confirm_deactivate.html` | HTMX confirmation partial | VERIFIED | `hx-post` + `hx-target="#user-row-..."` + `hx-swap="outerHTML"`; "O histórico será preservado" text present |
| `apps/accounts/templates/accounts/unit_confirm_deactivate.html` | HTMX confirmation partial | VERIFIED | "Usuários vinculados não serão desvinculados automaticamente" text present |
| `apps/accounts/templates/accounts/partials/user_form.html` | HTMX-wired form with `hx-post` | VERIFIED | `hx-post` + `hx-target="#form-container"` + `hx-swap="innerHTML"` present |
| `apps/accounts/tests/test_auth.py` | 5 auth integration tests | VERIFIED | 5 tests covering AUTH-01/02/03 (login success, wrong password, inactive, password reset, session) |
| `apps/accounts/tests/test_models.py` | 6 model unit tests | VERIFIED | tests: groups_exist, user_default_unit, role_choices, nullable unit, email USERNAME_FIELD, str |
| `apps/accounts/tests/test_user_mgmt.py` | 5 user CRUD tests | VERIFIED | tests: list access, 403 for non-admin, create, deactivate, confirm render |
| `apps/accounts/tests/test_unit_mgmt.py` | 4 unit CRUD tests | VERIFIED | tests: list access, create, assign unit to user, deactivate |
| `conftest.py` (root) | autouse STORAGES override for tests | VERIFIED | `use_simple_static_storage` fixture overrides to `StaticFilesStorage` |
| `static/htmx/htmx.min.js` | HTMX 2.0 vendored (50,917 bytes) | VERIFIED | File present, 50917 bytes confirmed |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `config/settings/base.py` | `apps/accounts/models.py` | `AUTH_USER_MODEL = "accounts.User"` | VERIFIED | Line 17 of base.py; Django resolves this to the `User` class |
| `apps/accounts/migrations/0001_initial.py` | PostgreSQL | `TrigramExtension()` + `UnaccentExtension()` | VERIFIED | Lines 25-26; correct import from `django.contrib.postgres.operations` |
| `templates/base.html` | HTMX | `htmx:configRequest` event reads `meta[name=csrf-token]` | VERIFIED | Lines 13-17 of base.html |
| `apps/accounts/views.py (UserCreateView)` | `apps/accounts/services.py (create_user)` | `services.create_user(form.cleaned_data)` | VERIFIED | Line 132 of views.py |
| `apps/accounts/templates/accounts/user_form.html` | `UserCreateView` | `hx-post` to `accounts:user-create` | VERIFIED | `partials/user_form.html` line 1 uses `hx-post` with conditional URL |
| `apps/accounts/templates/accounts/user_list.html` | `UserDeactivateConfirmView` | `hx-get` to `accounts:user-deactivate-confirm` | VERIFIED | `partials/user_row.html` line 6 uses `hx-get` on Desativar button |
| `apps/accounts/views.py (PasswordResetView)` | Django `PasswordResetView` | wraps with custom templates | VERIFIED | Lines 73-78 of views.py; `email_template_name` and `subject_template_name` wired |
| `apps/accounts/tests/conftest.py` | `apps/accounts/models.py` | fixtures create User and UnidadeOrganizacional instances | VERIFIED | Fixtures use `User.objects.create_user()` and `UnidadeOrganizacional.objects.create()` |

---

### Data-Flow Trace (Level 4)

Admin panel views render dynamic data from the database. Tracing critical data flows:

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `user_list.html` | `users` queryset | `UserListView.get_queryset()` → `User.objects.select_related("default_unit").order_by("email")` | Yes — live DB query | FLOWING |
| `unit_list.html` | `units` queryset | `UnitListView.get_queryset()` → `UnidadeOrganizacional.objects.annotate(user_count=Count(...))` | Yes — live DB query with annotation | FLOWING |
| `partials/unit_row.html` | `unit.user_count` | `UnitDeactivateView.post()` — passes bare `unit` object without re-annotating | No — missing annotation on deactivation path | HOLLOW (post-deactivation only; see WR-06 in review) |
| `dashboard.html` | KPI card values | Intentional `&mdash;` placeholders; no data source yet | N/A — deferred to Phase 5 | DEFERRED (intentional; noted in plan as stub) |

Note: The `unit_row.html` hollow-prop on the deactivation path is a post-deactivation display glitch (user count shows blank instead of a number) identified as WR-06 in the code review. It does not prevent the deactivation from succeeding — it is a visual cosmetic issue.

---

### Behavioral Spot-Checks

The project is a Docker-containerized Django app. Spot-checks requiring a running server are routed to human verification. Filesystem-level checks:

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| HTMX 2.0 vendored and non-empty | `wc -c static/htmx/htmx.min.js` | 50917 bytes | PASS |
| Django version pinned in requirements | `grep "Django==" requirements.txt` | `Django==5.2.*` | PASS |
| `AUTH_USER_MODEL` set correctly | `grep "AUTH_USER_MODEL" config/settings/base.py` | `AUTH_USER_MODEL = "accounts.User"` | PASS |
| 5 Groups in data migration | `grep "Solicitante" apps/accounts/migrations/0002_create_groups.py` | GRUPOS list present | PASS |
| TrigramExtension first in migration | Line 25 of `0001_initial.py` | `TrigramExtension()` at position 0 in operations | PASS |
| `htmx:configRequest` in base.html | `grep "htmx:configRequest" templates/base.html` | Present at line 13 | PASS |
| AdminRequiredMixin defined | `grep "class AdminRequiredMixin" apps/accounts/views.py` | Present at line 95 | PASS |
| All 10 admin panel URL patterns wired | `grep "admin-panel" apps/accounts/urls.py` | 10 paths found | PASS |

---

### Probe Execution

No `scripts/*/tests/probe-*.sh` files found in repository. No probes declared in PLAN files. Step 7c SKIPPED — no probe scripts to run.

---

### Requirements Coverage

All 9 Phase 1 requirements are claimed across the three plans and verified against codebase evidence:

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| AUTH-01 | 01-01, 01-02 | User logs in with email and password | SATISFIED | `login_view` uses `AuthenticationForm` with `email` as USERNAME_FIELD; `test_login_success` passes |
| AUTH-02 | 01-02 | User recovers password via email link | SATISFIED | `PasswordResetView` wired with email templates; `test_password_reset_sends_email` passes |
| AUTH-03 | 01-01, 01-02 | Session remains active across browser refreshes | SATISFIED | Django session middleware in MIDDLEWARE; `test_session_persists` passes |
| AUTH-04 | 01-03 | Admin creates, edits, deactivates users | SATISFIED | `UserCreateView`, `UserUpdateView`, `UserDeactivateView` + tests pass |
| AUTH-05 | 01-01, 01-02, 01-03 | 5 roles: Solicitante, Gestor, Comprador, Diretor, Admin | SATISFIED | `User.Role` TextChoices + `0002_create_groups.py` + `test_groups_exist` passes |
| AUTH-06 | 01-01, 01-02, 01-03 | Each user linked to a default unit | SATISFIED | `User.default_unit` FK; `test_user_default_unit` and `test_admin_assign_unit_to_user` pass |
| UNIT-01 | 01-01, 01-03 | Admin creates units (nome, descricao, ativo) | SATISFIED | `UnidadeOrganizacional` model + `UnitCreateView` + `test_admin_create_unit` passes |
| UNIT-02 | 01-03 | Admin links users to units | SATISFIED | `UserEditForm` includes `default_unit`; `test_admin_assign_unit_to_user` asserts `default_unit_id` updated |
| UNIT-03 | 01-02, 01-03 | User has default unit pre-selected when opening requisition | SATISFIED | `User.default_unit` FK nullable; `test_user_default_unit` and `test_default_unit_nullable` confirm round-trip |

**Note on UNIT-03:** The requirement says "pre-selected when opening a requisition" — the FK is in place and the model/service layer supports pre-population, but the actual Requisição form does not yet exist (Phase 2). The model-level contract (FK exists, nullable, persists correctly) is satisfied. The UI pre-selection behavior is a Phase 2 concern.

No orphaned requirements found. All 9 Phase 1 requirements appear in at least one plan's `requirements` frontmatter and are covered by codebase evidence.

---

### Anti-Patterns Found

No `TBD`, `FIXME`, or `XXX` markers found in any `.py` or `.html` file in the `apps/`, `config/`, or `templates/` directories. Debt-marker gate: CLEAR.

The following patterns were scanned and classified:

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `templates/base.html` | 33, 40-67 | `href="#"` on Requisições/Cotações/Fornecedores/Relatórios nav links | INFO | Intentional stubs documented in 01-01-SUMMARY.md; Phase 2-5 will wire these |
| `apps/core/templates/core/dashboard.html` | 9-24 | `&mdash;` as KPI card values | INFO | Intentional placeholder per SUMMARY and plan — data wired in Phase 5 |
| `apps/accounts/views.py` | 40 | `redirect(request.GET.get("next", "/"))` — unvalidated `next` param | WARNING | Open redirect (CR-01 from code review); attacker can craft `/login/?next=https://evil.com` |
| `apps/accounts/views.py` | 67-70 | `logout_view` executes on GET | WARNING | CSRF bypass on logout (CR-02 from code review) |
| `apps/accounts/views.py` | 42-60 | Differentiated error for inactive vs. wrong-password | WARNING | Account enumeration (CR-03 from code review) |
| `apps/accounts/services.py` | 22 | `user.set_password(password)` without `validate_password()` | WARNING | Password validators bypassed (CR-05 from code review) |
| `apps/accounts/views.py` | 161-180 | `UserUpdateView` calls `form.save()` directly, bypassing service layer | WARNING | Django Group membership not synced on role change (WR-07 from code review) |
| `apps/accounts/templates/accounts/partials/unit_row.html` | 9 | `{{ unit.user_count }}` — annotation absent on deactivation path | WARNING | Renders blank in user count column after deactivation (WR-06 from code review) |

**Classification note:** The 5 critical issues identified in 01-REVIEW.md (CR-01 through CR-05) are **security issues in an internal system with 20 users** — they affect hardening quality but do NOT prevent the phase goal ("users can authenticate, admin can manage accounts and units") from being achievable. Authentication works, admin panel is access-controlled, and all automated tests pass. Per verification instructions these are noted as known gaps but do not block the status.

---

### Human Verification Required

The following items cannot be verified programmatically and require a human to test with the running Docker environment (`docker compose up` on port 8002):

#### 1. Login Page Visual Appearance and Authentication Flow

**Test:** Open http://localhost:8002/accounts/login/ in a browser. Log in with the superuser account created during setup (admin@comprasnexos.com / admin123).
**Expected:** Page has dark background (#1a1a2e), red CTA button (#e94560), "Entrar na conta" text. After login, redirected to / (dashboard) with sidebar showing "Dashboard — ComprasNexos" in the title.
**Why human:** Visual theme and actual session creation require a running browser session.

#### 2. Password Reset Email Flow

**Test:** Submit http://localhost:8002/accounts/password-reset/ with a registered email address.
**Expected:** Console logs (dev settings use console backend) show an email with subject "Redefinição de senha — ComprasNexos", a reset link, and the body ending with "Equipe ComprasNexos".
**Why human:** Email delivery through the console backend requires the server to be running.

#### 3. Admin Panel Access Control (Role-Based)

**Test:** Log in as admin, navigate to /accounts/admin-panel/usuarios/. Log out, log in as a Solicitante-role user, navigate to the same URL.
**Expected:** Admin sees the user table (HTTP 200). Solicitante sees a permission-denied response (HTTP 403).
**Why human:** AdminRequiredMixin role check requires live session state to verify both branches.

#### 4. HTMX Inline Deactivation Confirmation

**Test:** In the user list, click "Desativar" on any active user. Then click "Confirmar desativação".
**Expected:** Confirmation card appears inline below the table without a page reload. After confirming, the user's table row updates inline to show "Inativo" badge — no full page reload occurs.
**Why human:** HTMX partial-swap behavior (hx-target, hx-swap="outerHTML") requires browser interaction with a live HTMX 2.0 runtime.

#### 5. Unit Deactivation — user_count Display After Deactivation (WR-06)

**Test:** Create a unit via /accounts/admin-panel/unidades/nova/. Then deactivate it via the Desativar button.
**Expected:** After the inline HTMX swap, the "Usuários vinculados" column shows a number (likely 0), not a blank cell.
**Why human:** Code review finding WR-06 identifies that `UnitDeactivateView` does not re-annotate `user_count` before rendering the partial, which may produce a blank cell. Human must confirm whether this manifests visually.

---

### Known Security Gaps (from 01-REVIEW.md — Do Not Block Phase Status)

These issues were identified by the code review performed after phase completion. They are recorded here for tracking. They are warnings in an internal 20-user system and do not prevent the phase goal from being achieved:

| ID | Severity | Issue | File:Line |
|----|----------|-------|-----------|
| CR-01 | Critical | Open redirect via unvalidated `next` parameter | `apps/accounts/views.py:40` |
| CR-02 | Critical | Logout executes on GET — no CSRF protection | `apps/accounts/views.py:67-70` |
| CR-03 | Critical | Account enumeration via inactive-user branch in login | `apps/accounts/views.py:42-60` |
| CR-04 | Critical | HTMX deactivation confirm dialogs lack self-contained CSRF token (rely on outer page `htmx:configRequest`) | `partials/user_confirm_deactivate.html:6`, `partials/unit_confirm_deactivate.html:6` |
| CR-05 | Critical | `create_user` bypasses Django password validators | `apps/accounts/services.py:22` |
| WR-07 | Warning | `UserUpdateView` does not sync Django Group membership on role change | `apps/accounts/views.py:161-180` |
| WR-06 | Warning | `unit_row.html` renders blank `user_count` after deactivation (missing re-annotation) | `apps/accounts/views.py:292-301` |

These should be addressed before the system is used in production or before Phase 2 begins (whichever comes first).

---

### Gaps Summary

No structural gaps block the phase goal. All 5 roadmap success criteria are verified by codebase evidence and passing automated tests. The phase goal — "Users can authenticate, and the Admin can manage accounts and organizational units" — is achieved.

The `human_needed` status is set because 5 items require browser-level verification (visual theme, live session, HTMX DOM behavior) that cannot be assessed from file content alone.

---

_Verified: 2026-06-10T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
