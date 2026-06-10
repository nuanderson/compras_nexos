---
phase: 01-foundation
plan: "03"
subsystem: accounts-admin
tags: [django, htmx, admin-panel, user-management, unit-management, tests]
dependency_graph:
  requires:
    - accounts.User (AUTH_USER_MODEL) — from Plan 01
    - accounts.UnidadeOrganizacional — from Plan 01
    - apps/accounts/services.py (create_user, deactivate_user) — from Plan 01
    - apps/accounts/forms.py (UserCreateForm, UserEditForm, UnidadeForm) — from Plan 01
    - templates/base.html + static/css/main.css — from Plan 01
  provides:
    - AdminRequiredMixin (role=admin or is_superuser check → HTTP 403)
    - UserListView, UserCreateView, UserUpdateView, UserDeactivateConfirmView, UserDeactivateView
    - UnitListView, UnitCreateView, UnitUpdateView, UnitDeactivateConfirmView, UnitDeactivateView
    - /admin-panel/usuarios/* URL patterns
    - /admin-panel/unidades/* URL patterns
    - HTMX inline deactivation confirmation (no window.confirm())
    - User and unit management test suite (9 tests)
  affects:
    - Phase 2-5 admin panel views (import and reuse AdminRequiredMixin)
    - base.html Admin/Config sidebar link (now wired to accounts:user-list)
tech_stack:
  added: []
  patterns:
    - AdminRequiredMixin with role check (admin or superuser → PermissionDenied)
    - HTMX inline deactivation confirmation via hx-get + outerHTML swap
    - Thin views calling services.py (no business logic in views)
    - Partial templates for HTMX swaps (partials/user_row.html, partials/unit_row.html)
    - pytest fixtures (admin_user, solicitante_user, test_unit) in conftest.py
key_files:
  created:
    - apps/accounts/templates/accounts/user_list.html
    - apps/accounts/templates/accounts/user_form.html
    - apps/accounts/templates/accounts/user_confirm_deactivate.html
    - apps/accounts/templates/accounts/unit_list.html
    - apps/accounts/templates/accounts/unit_form.html
    - apps/accounts/templates/accounts/unit_confirm_deactivate.html
    - apps/accounts/templates/accounts/partials/user_row.html
    - apps/accounts/templates/accounts/partials/user_form.html
    - apps/accounts/templates/accounts/partials/unit_row.html
    - apps/accounts/templates/accounts/partials/unit_form.html
    - apps/accounts/tests/__init__.py
    - apps/accounts/tests/conftest.py
    - apps/accounts/tests/test_user_mgmt.py
    - apps/accounts/tests/test_unit_mgmt.py
  modified:
    - apps/accounts/views.py (added AdminRequiredMixin + 9 admin panel view classes)
    - apps/accounts/urls.py (added 10 admin panel URL patterns)
    - templates/base.html (wired Admin/Config nav link to accounts:user-list)
    - config/settings/dev.py (override STORAGES to StaticFilesStorage for tests)
decisions:
  - "AdminRequiredMixin uses role='admin' OR is_superuser to allow Django superusers (created via createsuperuser) access without needing role field set"
  - "HTMX deactivation flow: hx-get loads confirm card into #confirm-container; confirm button hx-post deactivates and swaps outerHTML of the specific row — zero page reloads"
  - "dev.py overrides STORAGES to StaticFilesStorage — CompressedManifestStaticFilesStorage belongs only in prod (requires collectstatic manifest)"
  - "conftest.py provides admin_user (is_superuser=True), solicitante_user, gestor_user, test_unit fixtures shared across all accounts test files"
metrics:
  duration_minutes: 18
  completed_date: "2026-06-10"
  tasks_completed: 2
  tasks_total: 2
  files_created: 14
  files_modified: 4
---

# Phase 01 Plan 03: Admin Panel — User + Unit CRUD Summary

HTMX-powered admin panel with full user and unit management CRUD, AdminRequiredMixin enforcing role-based access (HTTP 403 for non-admins), and inline deactivation confirmation via HTMX partial swap — no window.confirm() or page reload.

## What Was Built

### Task 1: Admin Panel Views, URL Patterns, Templates

**views.py additions (AdminRequiredMixin + 9 view classes):**
- `AdminRequiredMixin(LoginRequiredMixin)`: Checks `role == "admin" or is_superuser` → raises `PermissionDenied` (HTTP 403) for non-admin users
- `UserListView`, `UserCreateView`, `UserUpdateView`, `UserDeactivateConfirmView`, `UserDeactivateView`
- `UnitListView`, `UnitCreateView`, `UnitUpdateView`, `UnitDeactivateConfirmView`, `UnitDeactivateView`
- All views use `select_related("default_unit")` and `annotate(user_count=Count("default_users"))` for efficient queries
- Create/update views delegate to `services.create_user()` — no business logic in views
- HTMX requests return `HttpResponseClientRedirect` (from django-htmx) for redirect after success

**urls.py additions (10 new URL patterns):**
- `/admin-panel/usuarios/` — list
- `/admin-panel/usuarios/novo/` — create
- `/admin-panel/usuarios/<int:pk>/editar/` — edit
- `/admin-panel/usuarios/<int:pk>/desativar/confirmar/` — GET confirmation partial
- `/admin-panel/usuarios/<int:pk>/desativar/` — POST deactivate
- Same pattern for `/admin-panel/unidades/`

**Templates (10 new files):**
- Full-page templates extend `base.html`, contain `{% block content %}` with data table or form card
- Partial templates (no `extends`) are HTMX swap targets
- `user_confirm_deactivate.html` / `unit_confirm_deactivate.html` — inline confirmation cards with `btn-destructive` confirm + `btn-secondary` cancel (exact UI-SPEC text)
- `partials/user_row.html` — HTMX `outerHTML` swap target on deactivation; shows Ativo/Inativo badge
- `partials/unit_row.html` — same pattern, includes `user_count` annotation
- Form partials inject `.form-input` / `.form-select` CSS classes via inline `<script>` after render

**base.html update:**
- Admin/Config sidebar nav link wired from `href="#"` to `{% url 'accounts:user-list' %}`

### Task 2: Tests — User CRUD + Unit CRUD (9 tests)

**conftest.py fixtures:**
- `test_unit` — creates `UnidadeOrganizacional` with `nome="Unidade Teste"`
- `admin_user` — `role=ADMIN`, `is_superuser=True`, `is_staff=True`
- `solicitante_user` — `role=SOLICITANTE`, non-admin
- `gestor_user` — `role=GESTOR`

**test_user_mgmt.py (5 tests — AUTH-04, AUTH-05, AUTH-06):**
- `test_admin_can_access_user_list` — admin gets 200
- `test_non_admin_blocked_from_user_list` — solicitante gets 403
- `test_admin_create_user` — POST to user-create → 302 + User row in DB
- `test_admin_deactivate_user` — POST to user-deactivate → 200 (partial) + `is_active=False`
- `test_deactivate_confirm_renders` — GET confirm URL → 200 + "Confirmar desativação" in content

**test_unit_mgmt.py (4 tests — UNIT-01, UNIT-02):**
- `test_admin_can_access_unit_list` — admin gets 200
- `test_admin_create_unit` — POST to unit-create → 302 + unit in DB
- `test_admin_assign_unit_to_user` — POST to user-edit with new unit → user.default_unit_id updated
- `test_unit_deactivate` — POST to unit-deactivate → 200 + `ativo=False`

## Verification Results

All tests pass:

| Check | Result |
|-------|--------|
| `manage.py check` | 0 issues (0 silenced) |
| `pytest test_user_mgmt.py test_unit_mgmt.py -x -v` | 9 passed |
| `test_admin_can_access_user_list` | PASSED |
| `test_non_admin_blocked_from_user_list` | PASSED (HTTP 403) |
| `test_admin_create_user` | PASSED (HTTP 302 + DB row) |
| `test_admin_deactivate_user` | PASSED (HTTP 200 + is_active=False) |
| `test_deactivate_confirm_renders` | PASSED |
| `test_admin_can_access_unit_list` | PASSED |
| `test_admin_create_unit` | PASSED (HTTP 302 + DB row) |
| `test_admin_assign_unit_to_user` | PASSED (default_unit_id updated) |
| `test_unit_deactivate` | PASSED (ativo=False) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] CompressedManifestStaticFilesStorage fails during tests**
- **Found during:** Task 2 — first pytest run
- **Issue:** `config/settings/base.py` sets `STORAGES["staticfiles"] = "whitenoise.storage.CompressedManifestStaticFilesStorage"` which requires a pre-generated staticfiles manifest. During tests, `collectstatic` has not been run, so any view that renders a template with `{% static %}` tags raises `ValueError: Missing staticfiles manifest entry for 'css/main.css'`.
- **Fix:** Added `STORAGES` override in `config/settings/dev.py` to use `django.contrib.staticfiles.storage.StaticFilesStorage` (no manifest needed). The base settings' `CompressedManifestStaticFilesStorage` is correct for production — this fix scopes it to dev/tests only.
- **Files modified:** `config/settings/dev.py`
- **Commit:** 6e8dc98

### Plan Adjustments

- `admin_user` fixture uses `is_superuser=True` (not just `role="admin"`) to match `AdminRequiredMixin` which accepts either — this enables the Django superuser (created via `createsuperuser`) to access the admin panel without needing the `role` field set.
- `conftest.py` is included in this plan because it is required by both test files in Task 2. The parallel agent (Plan 02) will produce an identical `conftest.py` — the merge will resolve to one canonical file.

## Known Stubs

None — all admin panel functionality is fully implemented and wired. No placeholder data or TODO values.

## Threat Surface Scan

All threats from the plan's threat model are addressed:

| Threat ID | Status | Implementation |
|-----------|--------|----------------|
| T-01-12: Elevation — non-admin accessing /admin-panel/* | Mitigated | `AdminRequiredMixin.dispatch()` checks role + superuser → HTTP 403 |
| T-01-13: CSRF on HTMX deactivation POST | Mitigated | `CsrfViewMiddleware` active; `htmx:configRequest` in base.html injects X-CSRFToken |
| T-01-14: Admin deactivating own account | Accepted | No guard in Phase 1 (superuser bypasses is_active check) |
| T-01-15: Mass assignment via ModelForm | Mitigated | `UserEditForm` and `UserCreateForm` explicitly list allowed fields (no `__all__`) |
| T-01-16: User list exposes emails | Accepted | Admin panel restricted to Admin role; internal system by design |

No new security surfaces introduced beyond the plan's threat model.

## Self-Check: PASSED

Files verified to exist:
- `apps/accounts/views.py` — FOUND (AdminRequiredMixin, UserListView, UnitListView, etc.)
- `apps/accounts/urls.py` — FOUND (10 new URL patterns)
- `apps/accounts/templates/accounts/user_list.html` — FOUND
- `apps/accounts/templates/accounts/user_form.html` — FOUND
- `apps/accounts/templates/accounts/user_confirm_deactivate.html` — FOUND
- `apps/accounts/templates/accounts/unit_list.html` — FOUND
- `apps/accounts/templates/accounts/unit_form.html` — FOUND
- `apps/accounts/templates/accounts/unit_confirm_deactivate.html` — FOUND
- `apps/accounts/templates/accounts/partials/user_row.html` — FOUND
- `apps/accounts/templates/accounts/partials/user_form.html` — FOUND
- `apps/accounts/templates/accounts/partials/unit_row.html` — FOUND
- `apps/accounts/templates/accounts/partials/unit_form.html` — FOUND
- `apps/accounts/tests/conftest.py` — FOUND
- `apps/accounts/tests/test_user_mgmt.py` — FOUND
- `apps/accounts/tests/test_unit_mgmt.py` — FOUND

Commits verified:
- 8da7480 (Task 1: admin panel views) — FOUND
- 6e8dc98 (Task 2: admin panel tests) — FOUND
