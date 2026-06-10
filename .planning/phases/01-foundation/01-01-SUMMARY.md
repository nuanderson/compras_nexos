---
phase: 01-foundation
plan: "01"
subsystem: foundation
tags: [django, docker, auth, htmx, postgresql, css]
dependency_graph:
  requires: []
  provides:
    - accounts.User (AUTH_USER_MODEL)
    - accounts.UnidadeOrganizacional
    - core.TimestampedModel
    - core.AuditedModel
    - Django 5 Groups (5 roles)
    - CSS design system (static/css/main.css)
    - Base layout template (templates/base.html)
    - Login view (/accounts/login/)
    - Docker dev and prod environments
  affects:
    - All subsequent plans (AUTH_USER_MODEL dependency)
    - Phase 2-5 templates (inherit base.html and main.css)
tech_stack:
  added:
    - Django==5.2.15 (LTS, pinned)
    - psycopg2-binary==2.9.12
    - django-htmx==1.27.0
    - whitenoise==6.12.0
    - gunicorn==26.0.0
    - python-decouple==3.8
    - django-anymail==15.0 (SES backend)
    - django-debug-toolbar==6.3.0 (dev only)
    - pytest==9.0.3 + pytest-django==4.12.0
    - HTMX 2.0.4 (vendored)
  patterns:
    - AbstractUser extension with email as USERNAME_FIELD
    - Split settings (base/dev/prod) via python-decouple
    - WhiteNoise static serving via new-style STORAGES dict
    - htmx:configRequest event listener for CSRF on all HTMX requests
    - Data migration for 5 Django Groups (Solicitante/Gestor/Comprador/Diretor/Admin)
    - TrigramExtension + UnaccentExtension in 0001_initial migration
    - Thin views + services.py business logic separation
key_files:
  created:
    - config/settings/base.py
    - config/settings/dev.py
    - config/settings/prod.py
    - config/urls.py
    - config/wsgi.py
    - apps/accounts/models.py
    - apps/accounts/migrations/0001_initial.py
    - apps/accounts/migrations/0002_create_groups.py
    - apps/accounts/admin.py
    - apps/accounts/views.py
    - apps/accounts/forms.py
    - apps/accounts/services.py
    - apps/accounts/urls.py
    - apps/accounts/templates/accounts/login.html
    - apps/accounts/templates/accounts/password_reset.html
    - apps/accounts/templates/accounts/password_reset_done.html
    - apps/accounts/templates/accounts/password_reset_confirm.html
    - apps/core/models.py
    - apps/core/views.py
    - apps/core/urls.py
    - apps/core/templates/core/dashboard.html
    - templates/base.html
    - static/css/main.css
    - static/htmx/htmx.min.js
    - Dockerfile
    - Dockerfile.dev
    - docker-compose.yml
    - docker-compose.prod.yml
    - requirements.txt
    - requirements-dev.txt
    - pytest.ini
    - manage.py
    - .env.example
    - .gitignore
  modified: []
decisions:
  - "Dockerfile.dev created for dev environment — installs requirements-dev.txt (includes debug_toolbar); Dockerfile (prod) installs requirements.txt only"
  - "docker-compose.yml uses Dockerfile.dev for web service; docker-compose.prod.yml uses Dockerfile (prod)"
  - "Port mapped to 8002 in docker-compose.yml to avoid conflict with existing containers on host port 8000"
  - "collectstatic in Dockerfile uses prod settings with build-time placeholder env vars to avoid requiring DB at build time"
metrics:
  duration_minutes: 32
  completed_date: "2026-06-10"
  tasks_completed: 3
  tasks_total: 3
  files_created: 34
  files_modified: 1
---

# Phase 01 Plan 01: Walking Skeleton — Project Scaffold Summary

Django 5.2 LTS + PostgreSQL 15 + HTMX 2.0 walking skeleton with custom User model (email login), 5 role Groups via data migration, pg_trgm/unaccent extensions, dark-theme CSS design system, and functional login page at /accounts/login/.

## What Was Built

### Task 1: Project Scaffold
Complete Django project scaffold:
- `Dockerfile` (prod): python:3.12-slim, non-root `app` user, collectstatic at build time
- `Dockerfile.dev`: separate dev image installing requirements-dev.txt (includes debug_toolbar)
- `docker-compose.yml`: dev with volume mount, Dockerfile.dev build
- `docker-compose.prod.yml`: restart: unless-stopped on both web and db
- `config/settings/{base,dev,prod}.py`: split settings with AUTH_USER_MODEL, STORAGES dict, HTMX middleware
- `requirements.txt`: Django==5.2.*, psycopg2-binary==2.9.*, django-htmx, whitenoise, gunicorn, python-decouple, django-anymail[amazon_ses]
- `requirements-dev.txt`: adds debug_toolbar, pytest, pytest-django
- `pytest.ini`, `manage.py`, `.env.example`, `.gitignore`
- Django 5.2.15 confirmed inside container

### Task 2: Core App
- `apps/core/models.py`: TimestampedModel + AuditedModel abstract bases with `# Monetary fields: DecimalField` rule documented
- `apps/core/views.py`: DashboardView with LoginRequiredMixin
- `apps/core/urls.py`: app_name="core", root `/` → dashboard
- `apps/core/templates/core/dashboard.html`: 4 KPI card placeholders with — values, "Dashboard em construção" note

### Task 3: Accounts App + Static Assets
- `apps/accounts/models.py`: User(AbstractUser) with email USERNAME_FIELD, 5-role TextChoices, default_unit FK; UnidadeOrganizacional model
- `apps/accounts/migrations/0001_initial.py`: TrigramExtension() + UnaccentExtension() first operations, then CreateModel for Unidade and User
- `apps/accounts/migrations/0002_create_groups.py`: data migration creating 5 Django Groups
- `apps/accounts/views.py`: login_view with correct error messages per UI-SPEC, logout, password reset delegates to Django built-ins
- `apps/accounts/forms.py`: UserCreateForm, UserEditForm, UnidadeForm
- `apps/accounts/services.py`: create_user(), deactivate_user(), assign_unit()
- `apps/accounts/admin.py`: UserAdmin with role/default_unit fieldsets, UnidadeOrganizacionalAdmin
- `templates/base.html`: full authenticated layout with sidebar (role-based nav), topbar, htmx:configRequest CSRF config
- `static/css/main.css`: complete design system — all color tokens (--color-bg: #1a1a2e, --color-accent: #e94560), layout, components, badges, banners
- `static/htmx/htmx.min.js`: HTMX 2.0.4 vendored (50,917 bytes)

## Verification Results

All success criteria passed:

| Check | Result |
|-------|--------|
| `docker compose build` | Exit 0 |
| Django version inside container | 5.2.15 |
| `manage.py check` | 0 issues, 0 warnings |
| `manage.py migrate --check` | Exit 0 (all applied) |
| `accounts_user` table exists | True |
| `auth_user` table does NOT exist | True |
| 5 Django Groups created | Solicitante/Gestor/Comprador/Diretor/Admin |
| `User.USERNAME_FIELD` | "email" |
| GET /accounts/login/ | HTTP 200, contains "Entrar na conta" |
| POST /accounts/login/ with valid credentials | HTTP 302 → / |
| Dashboard renders after login | Title "Dashboard — ComprasNexos" confirmed |
| base.html contains htmx:configRequest | True |
| 0001_initial.py contains TrigramExtension | True |
| main.css contains --color-bg: #1a1a2e | True |
| main.css contains --color-accent: #e94560 | True |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Dockerfile collectstatic used default (dev) settings**
- **Found during:** Task 1 Docker build
- **Issue:** Dockerfile runs `manage.py collectstatic` which uses `DJANGO_SETTINGS_MODULE=config.settings.dev` by default. Dev settings include `debug_toolbar` but `requirements.txt` doesn't install it — build failed.
- **Fix:** Added explicit `DJANGO_SETTINGS_MODULE=config.settings.prod` with build-time placeholder env vars for SECRET_KEY, DB_PASSWORD, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS
- **Files modified:** `Dockerfile`
- **Commit:** ecd2a50

**2. [Rule 3 - Blocking] Dev Docker container couldn't install debug_toolbar**
- **Found during:** Task 2 verification
- **Issue:** The prod Dockerfile creates a non-root `app` user. When dev containers run `pip install`, they fail with permission errors. Debug_toolbar in dev.py INSTALLED_APPS requires the package in the container.
- **Fix:** Created `Dockerfile.dev` that installs `requirements-dev.txt` as root during build, without the non-root user constraint. Updated `docker-compose.yml` to use `Dockerfile.dev` for dev.
- **Files created/modified:** `Dockerfile.dev`, `docker-compose.yml`
- **Commit:** c018459

**3. [Rule 3 - Blocking] Host port 8000 already allocated by existing container**
- **Found during:** Task 3 — `docker compose up -d`
- **Issue:** Another project's container (`sn_backend`) was already using port 8000 on the host.
- **Fix:** Updated `docker-compose.yml` to map host port 8002 → container port 8000. This is dev-only (prod docker-compose.prod.yml unaffected).
- **Files modified:** `docker-compose.yml`
- **Commit:** 8286acd (same commit as Task 3)

## Known Stubs

| Stub | File | Line | Reason |
|------|------|------|--------|
| Dashboard KPI values "—" | `apps/core/templates/core/dashboard.html` | 6-18 | Intentional placeholder — real data wired in Phase 5 per plan |
| Requisições nav link `href="#"` | `templates/base.html` | 36-38 | Intentional — Requisições app built in Phase 2 |
| Cotações nav link `href="#"` | `templates/base.html` | 41-45 | Intentional — Cotações app built in Phase 4 |
| Fornecedores nav link `href="#"` | `templates/base.html` | 48-52 | Intentional — Fornecedores app built in Phase 3 |
| Relatórios nav link `href="#"` | `templates/base.html` | 55-59 | Intentional — Relatórios app built in Phase 5 |
| Admin/Config nav link `href="#"` | `templates/base.html` | 63-67 | Intentional — Admin panel CRUD in Plan 03 |

All stubs are intentional per the Walking Skeleton design — Phase 1 delivers the foundational shell, content is filled in Phase 2-5.

## Threat Surface Scan

No new security surfaces beyond those in the plan's threat model. The implementation directly addresses all mitigations in the threat register:

| Threat ID | Status |
|-----------|--------|
| T-01-01 Spoofing — login view | Mitigated: Django authenticate() with PBKDF2 |
| T-01-02 Tampering — HTMX CSRF | Mitigated: htmx:configRequest in base.html |
| T-01-03 Elevation — inactive user | Mitigated: is_active check in login_view |
| T-01-04 Elevation — open redirect | Mitigated: Django validates next= parameter |
| T-01-06 Elevation — session fixation | Mitigated: Django cycle_key() automatic |
| T-01-07 Elevation — SECRET_KEY | Mitigated: python-decouple reads from .env |

## Self-Check: PASSED

Files verified to exist:
- `apps/accounts/models.py` — FOUND
- `apps/accounts/migrations/0001_initial.py` — FOUND
- `apps/accounts/migrations/0002_create_groups.py` — FOUND
- `config/settings/base.py` — FOUND
- `templates/base.html` — FOUND
- `static/css/main.css` — FOUND
- `static/htmx/htmx.min.js` — FOUND
- `Dockerfile` — FOUND
- `Dockerfile.dev` — FOUND
- `docker-compose.yml` — FOUND
- `docker-compose.prod.yml` — FOUND

Commits verified:
- ecd2a50 (Task 1: project scaffold) — FOUND
- c018459 (Task 2: core app) — FOUND
- 8286acd (Task 3: accounts app) — FOUND
