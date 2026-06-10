---
phase: 01-foundation
plan: "02"
subsystem: authentication
tags: [django, auth, password-reset, pytest, testing]
dependency_graph:
  requires:
    - accounts.User (AUTH_USER_MODEL) — Plan 01-01
    - accounts.UnidadeOrganizacional — Plan 01-01
    - Django 5 Groups (5 roles) — Plan 01-01
    - login_view — Plan 01-01
    - CSS design system (static/css/main.css) — Plan 01-01
  provides:
    - Password reset templates (request, done, confirm, email)
    - pytest test suite for AUTH-01/02/03/05/06 and UNIT-03
    - Root conftest.py with static storage override for tests
    - accounts/tests/ package with conftest, test_auth, test_models
  affects:
    - CI gate — all Phase 1 requirements now have automated coverage
    - Phase 2+ tests — conftest.py fixtures (admin_user, solicitante_user, gestor_user, test_unit) are reusable
tech_stack:
  added: []
  patterns:
    - "@override_settings(EMAIL_BACKEND=locmem) on mail.outbox tests when dev uses console backend"
    - "Root conftest.py with autouse fixture for STORAGES override (CompressedManifest → StaticFiles for tests)"
    - "pytest fixtures scoped with db parameter for DB access"
key_files:
  created:
    - apps/accounts/templates/accounts/email/password_reset_subject.txt
    - apps/accounts/tests/__init__.py
    - apps/accounts/tests/conftest.py
    - apps/accounts/tests/test_auth.py
    - apps/accounts/tests/test_models.py
    - apps/core/tests/__init__.py
    - conftest.py
  modified:
    - apps/accounts/templates/accounts/password_reset.html
    - apps/accounts/templates/accounts/password_reset_done.html
    - apps/accounts/templates/accounts/password_reset_confirm.html
    - apps/accounts/templates/accounts/email/password_reset.html
decisions:
  - "Use @override_settings(EMAIL_BACKEND=locmem) per-test rather than a test-specific settings file — avoids a new settings module for a single fixture"
  - "Root conftest.py autouse fixture for STORAGES override — fixes missing staticfiles manifest error without modifying base/dev settings"
  - "TDD cycle applied: RED (test files with no implementation), GREEN (implementation already exists from Plan 01, fixed @override_settings), REFACTOR (root conftest.py)"
metrics:
  duration_minutes: 11
  completed_date: "2026-06-10"
  tasks_completed: 2
  tasks_total: 2
  files_created: 7
  files_modified: 5
---

# Phase 01 Plan 02: Password Reset Templates + Test Scaffold Summary

Password reset template suite (request, done, confirm, email) updated to match UI-SPEC copywriting contract, plus a full pytest test scaffold covering AUTH-01, AUTH-02, AUTH-03, AUTH-05, AUTH-06, and UNIT-03 — all 11 tests passing via Docker.

## What Was Built

### Task 1: Password Reset Templates

Updated all password reset templates to match the Plan 02 spec and UI-SPEC copywriting contract:

- `password_reset.html`: Added instruction paragraph ("Informe seu e-mail..."), added `form.non_field_errors` block, added explicit `action="{% url 'accounts:password-reset' %}"`, correct title "Redefinir Senha"
- `password_reset_done.html`: Changed banner class to `banner-success`, added expiry explanation paragraph ("Verifique sua caixa de entrada... O link expira em 3 dias."), exact copywriting from UI-SPEC
- `password_reset_confirm.html`: Added generic `form.errors.values` error block, correct title "Nova Senha", correct subtitle "Criar nova senha"
- `email/password_reset.html`: Changed to plain-text-readable body matching spec (includes 3-day validity note, "Equipe ComprasNexos" sign-off)
- `email/password_reset_subject.txt`: Already correct — "Redefinição de senha — ComprasNexos"
- `apps/accounts/views.py`: Already had `email_template_name` and `subject_template_name` correctly wired from Plan 01

### Task 2: Test Scaffold (TDD)

Created the complete pytest test scaffold with TDD RED/GREEN/REFACTOR cycle:

**RED phase (commit e4629d1):**
- `apps/accounts/tests/__init__.py` — package marker
- `apps/accounts/tests/conftest.py` — shared fixtures: `test_unit`, `admin_user`, `solicitante_user`, `gestor_user`
- `apps/accounts/tests/test_auth.py` — 5 integration tests: login success/wrong password/inactive, password reset email, session persistence
- `apps/accounts/tests/test_models.py` — 6 unit tests: groups exist, default_unit FK, role choices, nullable unit, email USERNAME_FIELD, `__str__`
- `apps/core/tests/__init__.py` — package marker

**GREEN phase (commit d31bdd6):**
- Added `@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")` to `test_password_reset_sends_email` so `mail.outbox` is populated (dev settings use console backend)
- Implementation from Plan 01 covers all test requirements

**REFACTOR phase (commit 21e9b55):**
- `conftest.py` (root): autouse fixture overrides STORAGES to `StaticFilesStorage` — prevents "Missing staticfiles manifest" error from `CompressedManifestStaticFilesStorage` during tests that render templates

## Verification Results

All acceptance criteria passed:

| Check | Result |
|-------|--------|
| `password_reset.html` contains "Enviar link de redefinição" | 1 match — PASS |
| `password_reset_done.html` contains "Se esse e-mail estiver cadastrado" | 1 match — PASS |
| `email/password_reset_subject.txt` contains "ComprasNexos" | 1 match — PASS |
| `password_reset_confirm.html` contains "Este link expirou" | 1 match — PASS |
| `password_reset_confirm.html` contains "Redefinir senha" | 1 match — PASS |
| `views.py` contains `email_template_name` wired to correct template | confirmed PASS |
| `pytest apps/accounts/tests/ -x -q` (11 tests) | 11 passed — PASS |
| `test_groups_exist` — 5 Groups confirmed | PASS |
| `test_user_default_unit` — FK round-trip | PASS |
| `test_login_success` — 302 redirect | PASS |
| `test_password_reset_sends_email` — mail.outbox has 1 item | PASS |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] test_password_reset_sends_email would fail with console.EmailBackend**
- **Found during:** Task 2 GREEN phase
- **Issue:** `mail.outbox` only works with `locmem.EmailBackend`. Dev settings use `console.EmailBackend`. Without an override, the email test would always fail with `len(mail.outbox) == 0`.
- **Fix:** Added `@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")` decorator on the specific test function. This is the correct targeted fix — no global settings change needed.
- **Files modified:** `apps/accounts/tests/test_auth.py`
- **Commit:** d31bdd6

**2. [Rule 2 - Missing Critical Functionality] Template rendering fails with CompressedManifestStaticFilesStorage**
- **Found during:** Task 2 verification (test run)
- **Issue:** `CompressedManifestStaticFilesStorage` (in base.py STORAGES) requires `collectstatic` to generate a manifest file. Without it, any test that renders a template with `{% static %}` tags raises `ValueError: Missing staticfiles manifest entry for 'css/main.css'`.
- **Fix:** Created root `conftest.py` with an autouse `settings` fixture that overrides STORAGES to use `StaticFilesStorage` (non-hashing, no manifest required) for all tests.
- **Files created:** `conftest.py`
- **Commit:** 21e9b55

## TDD Gate Compliance

| Gate | Commit | Message |
|------|--------|---------|
| RED | e4629d1 | `test(01-02): add failing test scaffold for AUTH-01/02/03/05/06 and UNIT-03` |
| GREEN | d31bdd6 | `feat(01-02): wire test scaffold to implementation — green phase` |
| REFACTOR | 21e9b55 | `refactor(01-02): add root conftest.py to fix staticfiles manifest in tests` |

All three TDD gate commits present in correct sequence.

## Known Stubs

None introduced in this plan.

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes introduced. All threat mitigations from the plan's threat model are covered by Django's built-in `PasswordResetView`:

| Threat ID | Status |
|-----------|--------|
| T-01-09 Elevation — token reuse | Mitigated by Django PasswordResetConfirmView (auto-invalidates after first use) |
| T-01-10 Information Disclosure — user enumeration | Mitigated: done page always shows regardless of email existence |
| T-01-11 Spoofing — email link | Mitigated: HMAC token tied to password hash |

## Self-Check: PASSED

Files verified to exist:
- `apps/accounts/templates/accounts/password_reset.html` — FOUND
- `apps/accounts/templates/accounts/password_reset_done.html` — FOUND
- `apps/accounts/templates/accounts/password_reset_confirm.html` — FOUND
- `apps/accounts/templates/accounts/email/password_reset_subject.txt` — FOUND
- `apps/accounts/templates/accounts/email/password_reset.html` — FOUND
- `apps/accounts/tests/__init__.py` — FOUND
- `apps/accounts/tests/conftest.py` — FOUND
- `apps/accounts/tests/test_auth.py` — FOUND
- `apps/accounts/tests/test_models.py` — FOUND
- `apps/core/tests/__init__.py` — FOUND
- `conftest.py` — FOUND

Commits verified:
- 074184d (Task 1: password reset templates) — FOUND
- e4629d1 (Task 2 RED: test scaffold) — FOUND
- d31bdd6 (Task 2 GREEN: implementation wired) — FOUND
- 21e9b55 (Task 2 REFACTOR: root conftest.py) — FOUND
