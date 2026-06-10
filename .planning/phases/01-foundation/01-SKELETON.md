# Walking Skeleton — ComprasNexos

**Phase:** 1 — Foundation
**Created:** 2026-06-10
**Purpose:** Record the thinnest possible end-to-end working slice. Decisions recorded here are the architectural foundation all subsequent phases build on without renegotiating.

---

## What the Skeleton Proves

When `docker compose up` completes and a browser opens `http://localhost:8000/accounts/login/`:

1. Django 5.2 LTS is running on Python 3.12 inside a container
2. PostgreSQL 15 (with `pg_trgm` and `unaccent` extensions) is connected and migrated
3. The custom `accounts.User` model exists — `AUTH_USER_MODEL = 'accounts.User'` — before any other app runs migrations
4. Five Django Groups (`Solicitante`, `Gestor`, `Comprador`, `Diretor`, `Admin`) exist from a data migration
5. A real User record can be read from PostgreSQL via `authenticate(email=..., password=...)`
6. POST `/accounts/login/` authenticates, creates a session, and redirects to `/`
7. The dark-theme base layout renders with HTMX CSRF configured globally on `<body>`

This is NOT complete auth — it is the thinnest slice that proves the project works end-to-end.

---

## Architectural Decisions (Locked)

These decisions are set in stone. Subsequent phases build on them. They are NOT revisited.

| Decision | Value | Rationale |
|----------|-------|-----------|
| Language runtime | Python 3.12 (inside Docker) | Client-mandated. Host has 3.14.5 — irrelevant, everything runs inside Docker. |
| Web framework | Django 5.2 LTS (`Django==5.2.*` pinned) | LTS until April 2028. Pin mandatory — pip resolves to 6.0.6 without it. |
| Frontend interactivity | HTMX 2.0.x (vendored as `static/htmx/htmx.min.js`) | Client-mandated. No React, Vue, Alpine. HTMX only. |
| Database | PostgreSQL 15-alpine (Docker service `db`) | AWS RDS 15 target. Never SQLite anywhere. |
| Auth model | `accounts.User(AbstractUser)` with email as `USERNAME_FIELD` | Must be created before first `migrate`. `AUTH_USER_MODEL = 'accounts.User'`. |
| RBAC | Django Groups (5 groups) + `role = CharField(choices=Role.choices)` on User | 5 stable roles. No django-guardian. No django-allauth. |
| Org unit FK | `User.default_unit = ForeignKey('accounts.UnidadeOrganizacional')` | Nullable. Set by Admin. Provides Phase 2 pre-selection. |
| Settings structure | `config/settings/base.py`, `config/settings/dev.py`, `config/settings/prod.py` | Split settings from day one. `DJANGO_SETTINGS_MODULE=config.settings.dev` in Docker. |
| Static files | WhiteNoise (`whitenoise.middleware.WhiteNoiseMiddleware`) | No Nginx in Phase 1. WhiteNoise serves from Django. |
| Email (dev) | Console backend (`django.core.mail.backends.console.EmailBackend`) | Prints to stdout. SES wired in prod via `django-anymail`. |
| Email (prod) | `django-anymail[amazon_ses]` | Backend configured via env vars. SES domain setup is operations, not code. |
| Container dev command | `python manage.py runserver 0.0.0.0:8000` | Dev only. Prod uses gunicorn. |
| Container prod command | `gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3` | 3 workers on t3.small (2 vCPU). |
| Restart policy | `restart: unless-stopped` on all services | EC2 instance reboot safety. Mandatory in docker-compose.prod.yml. |
| Monetary fields | `DecimalField(max_digits=12, decimal_places=2)` everywhere | Never FloatField. Phase 1 has no monetary fields but abstract base must document the rule. |
| CSS approach | Single file `static/css/main.css` with CSS custom properties | No Tailwind, no Bootstrap, no utility framework. System font stack only. |
| Dark theme tokens | `--color-bg: #1a1a2e`, `--color-surface: #16213e`, `--color-accent: #e94560` | Locked. All phases inherit. No light mode in v1. |
| HTMX CSRF method | `htmx:configRequest` event listener in `base.html` reads `<meta name="csrf-token">` | Explicit and debuggable. Prevents 403 on all HTMX POSTs. |
| HTMX boost | `hx-boost="true"` on `<nav class="sidebar">` | Navigation links act as AJAX transitions. |
| Service layer | Business logic in `{app}/services.py`; views are thin (validate → call service → render) | Views never contain business logic. |
| Test framework | pytest + pytest-django | `docker compose run --rm web pytest -x -q` |

---

## Directory Layout

```
compras_nexos/              ← git root / working directory
├── config/
│   ├── settings/
│   │   ├── base.py         ← AUTH_USER_MODEL, INSTALLED_APPS, MIDDLEWARE, DATABASES, etc.
│   │   ├── dev.py          ← DEBUG=True, EMAIL=console, DEBUG_TOOLBAR
│   │   └── prod.py         ← SECURE_*, ALLOWED_HOSTS from env, EMAIL=anymail/SES
│   ├── urls.py             ← root URL conf
│   └── wsgi.py
├── apps/
│   ├── accounts/
│   │   ├── migrations/
│   │   │   ├── 0001_initial.py      ← TrigramExtension + UnaccentExtension + User + Unidade
│   │   │   └── 0002_create_groups.py ← data migration: 5 Groups
│   │   ├── models.py       ← User(AbstractUser) + UnidadeOrganizacional
│   │   ├── services.py     ← create_user(), deactivate_user(), assign_unit()
│   │   ├── views.py        ← login, logout, password reset, user CRUD, unit CRUD
│   │   ├── forms.py        ← UserCreateForm, UserEditForm, UnidadeForm
│   │   ├── urls.py         ← /accounts/* + /admin-panel/*
│   │   ├── admin.py        ← UserAdmin (Django admin site — developer use)
│   │   └── templates/accounts/
│   │       ├── login.html
│   │       ├── password_reset.html
│   │       ├── password_reset_confirm.html
│   │       ├── password_reset_done.html
│   │       ├── user_list.html
│   │       ├── user_form.html
│   │       ├── unit_list.html
│   │       └── unit_form.html
│   └── core/
│       ├── migrations/
│       ├── models.py       ← TimestampedModel, AuditedModel (abstract bases)
│       ├── views.py        ← DashboardView (stub)
│       ├── urls.py         ← / → dashboard
│       └── templates/core/
│           └── dashboard.html
├── templates/
│   └── base.html           ← layout, sidebar, topbar, HTMX CSRF, messages
├── static/
│   ├── css/main.css        ← full design system (CSS custom properties)
│   └── htmx/htmx.min.js   ← vendored HTMX 2.0.x
├── Dockerfile
├── docker-compose.yml      ← dev: web + db, volume mounts, healthcheck
├── docker-compose.prod.yml ← prod: restart: unless-stopped, no volume mounts
├── .env.example
├── requirements.txt        ← Django==5.2.*, psycopg2-binary, django-htmx, whitenoise, gunicorn, python-decouple, django-anymail[amazon_ses]
├── requirements-dev.txt    ← -r requirements.txt + django-debug-toolbar + pytest + pytest-django
├── pytest.ini
└── manage.py
```

---

## App Dependency Graph (All Phases)

```
accounts, core  ←  all other apps reference AUTH_USER_MODEL
fornecedores    ←  requisicoes, cotacoes (FK to Fornecedor)
requisicoes     ←  aprovacoes, cotacoes, relatorios
aprovacoes      ←  cotacoes (completion check), relatorios
cotacoes        ←  relatorios
relatorios      ←  imports from all apps (intentional — no models of its own)
```

**Rule:** No reverse imports. `accounts` and `core` must never import from feature apps.

---

## Environment Variables

All read from `.env` via `python-decouple`. Never hardcoded.

```
SECRET_KEY=
DEBUG=True
DB_NAME=compras_nexos
DB_USER=compras
DB_PASSWORD=dev_password
DB_HOST=db
DB_PORT=5432
DJANGO_SETTINGS_MODULE=config.settings.dev
# Production only (not in dev .env):
# ALLOWED_HOSTS=
# CSRF_TRUSTED_ORIGINS=
# AWS_ACCESS_KEY_ID=
# AWS_SECRET_ACCESS_KEY=
# ANYMAIL_AMAZON_SES_CLIENT_PARAMS={}
```

---

## Walking Skeleton Completion Gate

The skeleton is complete when ALL of these pass:

- [ ] `docker compose up` starts without errors
- [ ] `docker compose run --rm web python manage.py check` returns no issues
- [ ] `docker compose run --rm web python manage.py showmigrations` shows all migrations applied (accounts 0001 + 0002, core)
- [ ] `curl http://localhost:8000/accounts/login/` returns HTTP 200 with `<title>` containing "ComprasNexos"
- [ ] POST to `/accounts/login/` with valid superuser credentials returns HTTP 302 redirect to `/`
- [ ] `docker compose run --rm web python manage.py shell -c "import django; print(django.__version__)"` prints `5.2.x`
- [ ] `docker compose run --rm web python manage.py shell -c "from django.contrib.auth.models import Group; print(Group.objects.count())"` prints `5`
- [ ] `docker compose run --rm web python manage.py shell -c "from apps.accounts.models import User; print(User._meta.label)"` prints `accounts.User`

---

*Walking Skeleton defined: 2026-06-10*
*Architectural decisions locked — do not renegotiate in subsequent phases*
