# Phase 1: Foundation - Research

**Researched:** 2026-06-10
**Domain:** Django project scaffold, custom auth, organizational units, Docker dev/prod setup
**Confidence:** HIGH

---

## Summary

Phase 1 establishes the irreversible foundation for all subsequent phases. The single most critical constraint is that the custom User model (`accounts.User` extending `AbstractUser`) and the PostgreSQL extensions (`pg_trgm`, `unaccent`) must be in place before the first `migrate` command. Every other model in every other phase will reference `AUTH_USER_MODEL`, making any retroactive change catastrophic.

The phase delivers a Working Skeleton: a running Django + PostgreSQL + Docker environment where a real user can log in via email/password, the Admin can create/edit/deactivate accounts with one of five roles (Solicitante, Gestor, Comprador, Diretor, Admin), and the Admin can create organizational units and link users to them. The base HTMX layout with CSRF configured globally on `<body>` must also be live before Phase 2 can begin any interactive work.

**Key version alert for planning:** The current latest Django on PyPI is 6.0.6 (NOT LTS). The project requires Django **5.2 LTS** (`Django==5.2.*`), which must be pinned explicitly in `requirements.txt` to prevent `pip install Django` from pulling 6.0. Django 5.2 is confirmed LTS supported until April 2028. [VERIFIED: djangoproject.com/download/]

**Primary recommendation:** Build the entire foundation in a strict order — scaffold → `core` → `accounts` model + migration → groups data migration → login views → unit CRUD → Docker — never inverting any step. The custom User model is the load-bearing keystone.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUTH-01 | Usuário faz login com e-mail e senha | Django built-in `LoginView` with `USERNAME_FIELD = 'email'` on custom User. Uses `authenticate()` + `login()` + session. No external library needed. |
| AUTH-02 | Usuário recupera senha via link por e-mail | Django built-in password reset views (`PasswordResetView`, `PasswordResetConfirmView`). Requires email backend configured (console in dev, SES/SMTP in prod). |
| AUTH-03 | Sessão permanece ativa entre atualizações do navegador | Django sessions (`django.contrib.sessions`) + `SESSION_COOKIE_AGE` setting. Default persistent session cookie behavior. No extra work beyond correct settings. |
| AUTH-04 | Admin cria, edita e desativa contas de usuários | Custom admin panel views at `/admin-panel/usuarios/`. Uses Django `UserAdmin` for the Django admin site, plus custom views for the app admin panel. Deactivate maps to `user.is_active = False`. |
| AUTH-05 | Sistema suporta 5 perfis: Solicitante, Gestor, Comprador, Diretor, Admin | `role = CharField(choices=Role.choices)` on custom User model + 5 Django Groups created via data migration in `accounts`. Role drives template visibility; Groups drive `PermissionRequiredMixin`. |
| AUTH-06 | Cada usuário está vinculado a uma unidade padrão | `default_unit = ForeignKey('accounts.UnidadeOrganizacional', null=True, blank=True, on_delete=SET_NULL)` on User model. User form shows unit selector. Phase 1 must deliver this FK even if units are sparse. |
| UNIT-01 | Admin cadastra unidades (nome, descrição, status ativo/inativo) | `UnidadeOrganizacional` model: `nome CharField`, `descricao TextField`, `ativo BooleanField(default=True)`. CRUD views at `/admin-panel/unidades/`. |
| UNIT-02 | Admin vincula usuários a unidades | User edit form includes `default_unit` ForeignKey selector. Admin sets when creating/editing user. Also `unidades = ManyToManyField(UnidadeOrganizacional)` on User for multi-unit membership if needed (see open question). |
| UNIT-03 | Usuário tem unidade padrão pré-selecionada ao abrir requisição, mas pode alterá-la | `user.default_unit` FK provides the pre-selection value. Phase 2 requisition form reads it as `initial={'unidade': request.user.default_unit}`. No Phase 1 implementation needed beyond the FK on User model. |
</phase_requirements>

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Login / auth session | Django Backend (API/app tier) | Browser (session cookie) | Credentials must be validated server-side. Session cookie is managed by browser, established by server. |
| Password reset email | Django Backend | Email provider (SES) | Reset link generation and token validation are server-side security operations. Email delivery is delegated to SES. |
| User management CRUD | Django Backend | Browser (HTMX partial update) | Business rules (role assignment, deactivation guard) belong server-side. HTMX provides inline feedback only. |
| Unit management CRUD | Django Backend | Browser (HTMX partial update) | Same pattern as user management. |
| Role-based nav visibility | Django Templates (server-rendered) | — | No client-side JS involved. Django template `{% if %}` on `request.user.role` or group membership. |
| Static file serving | WhiteNoise (middleware on Django) | — | Phase 1 uses WhiteNoise, not Nginx. CDN/S3 is a later concern. |
| CSS design system | Browser | — | Pure CSS custom properties in `static/css/main.css`. No build step, no JS framework. |
| CSRF protection | Django Middleware | HTMX config script | Django's `CsrfViewMiddleware` + HTMX `htmx:configRequest` event in base template. Both are required. |
| PostgreSQL extensions | Database tier | Django migration | Extensions (`pg_trgm`, `unaccent`) enabled via `TrigramExtension()` / `UnaccentExtension()` in first migration. |
| Docker/container orchestration | Infrastructure | — | Dev: `docker-compose.yml` with PostgreSQL + web. Prod: `docker-compose.prod.yml` with restart policy. |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12.x | Runtime | Client-mandated. Stable, supported through 2028. [VERIFIED: python.org] |
| Django | 5.2.15 (LTS) | Web framework | Current LTS. **Do NOT use 6.0** — it is NOT LTS. Pin as `Django==5.2.*` in requirements.txt. [VERIFIED: djangoproject.com/download/] |
| django-htmx | 1.27.0 | HTMX middleware + `request.htmx` | Adam Johnson's library; adds `HtmxMiddleware` and response helpers. Essential. [VERIFIED: PyPI] |
| PostgreSQL | 15-alpine (Docker) | Primary database | AWS RDS 15 is safe for production. Use everywhere (dev + prod) — never SQLite. [ASSUMED: AWS RDS 15 availability confirmed in prior research] |
| psycopg2-binary | 2.9.12 | PostgreSQL adapter | Binary for Docker avoids C build deps. [VERIFIED: PyPI] |
| HTMX | 2.0.x | Frontend interactivity | Client decision. Vendor as `static/htmx/htmx.min.js` or serve from CDN. [CITED: htmx.org] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| whitenoise | 6.12.0 | Static file serving | Phase 1 — eliminates Nginx in dev/prod at this scale. [VERIFIED: PyPI] |
| gunicorn | 26.0.0 | WSGI production server | Production Dockerfile CMD. 3 workers on t3.small. [VERIFIED: PyPI] |
| python-decouple | 3.8 | Env var / `.env` management | All settings read from `.env` via `config()`. [VERIFIED: PyPI] |
| django-debug-toolbar | 6.3.0 | Dev query inspection | `requirements-dev.txt` only. Essential for catching N+1 from day one. [VERIFIED: PyPI] |
| django-anymail | 15.0 | Email backend abstraction (SES) | Password reset in Phase 1 uses console backend in dev; prod uses SES. `django-anymail[amazon_ses]`. [VERIFIED: PyPI] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom `AbstractUser` + role field | django-allauth | django-allauth designed for social auth / self-registration — zero benefit for admin-managed internal system. Never use. |
| Django Groups for RBAC | django-guardian (object-level) | Object-level permissions unneeded for 20 users with 5 stable roles. Adds migration complexity with no benefit. |
| Django built-in auth views | Custom login views | Built-in views cover all Phase 1 needs. Override templates only. |
| WhiteNoise | Nginx reverse proxy | Nginx adds container complexity not justified for Phase 1. Switch to django-storages + S3 if CDN needed later. |
| `python-decouple` | `django-environ` | Both work; `python-decouple` has simpler API for this scale. [ASSUMED: functional equivalence] |

**Installation (requirements.txt):**
```
# Core — Phase 1
Django==5.2.*
psycopg2-binary==2.9.*
django-htmx
whitenoise
gunicorn
python-decouple
django-anymail[amazon_ses]
```

**Installation (requirements-dev.txt):**
```
-r requirements.txt
django-debug-toolbar
```

**Version pin note:** `Django==5.2.*` is mandatory. Without the pin, `pip install Django` resolves to 6.0.6 (not LTS). Always pin. [VERIFIED: PyPI confirms 6.0.6 as current latest]

---

## Package Legitimacy Audit

> slopcheck 0.6.1 run on 2026-06-10 against all Phase 1 packages.

| Package | Registry | Age | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|
| Django | PyPI | ~20 yrs | [OK] | Approved |
| django-htmx | PyPI | ~5 yrs | [OK] | Approved |
| psycopg2-binary | PyPI | ~15 yrs | [OK] | Approved |
| whitenoise | PyPI | ~10 yrs | [OK] | Approved |
| gunicorn | PyPI | ~15 yrs | [OK] | Approved |
| python-decouple | PyPI | ~10 yrs | [OK] — noted "python-" prefix is LLM bait pattern, but package is established | Approved |
| django-anymail | PyPI | ~8 yrs | [OK] | Approved |
| django-debug-toolbar | PyPI | ~15 yrs | [OK] | Approved |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

All 8 packages passed slopcheck verification.

---

## Architecture Patterns

### System Architecture Diagram

```
Browser
  |
  | HTTP request (GET full page / HTMX partial)
  v
Django (Gunicorn WSGI)
  |  ├── CsrfViewMiddleware
  |  ├── SessionMiddleware
  |  ├── HtmxMiddleware (request.htmx flag)
  |  └── WhiteNoiseMiddleware (static files)
  |
  |── URL router → accounts.urls / core.urls
  |
  |── Views (thin: validate → call service → render)
  |     ├── auth views (login/logout/password-reset)
  |     ├── user CRUD views (admin-panel/usuarios/)
  |     └── unit CRUD views (admin-panel/unidades/)
  |
  |── Services (business logic)
  |     └── accounts/services.py (create_user, deactivate_user)
  |
  |── Models
  |     ├── accounts.User (AbstractUser + role FK + default_unit FK)
  |     ├── accounts.UnidadeOrganizacional (name, desc, active)
  |     └── Django Groups (5 groups via data migration)
  |
  v
PostgreSQL 15
  └── pg_trgm + unaccent extensions (enabled in 0001 migration)

Email (password reset only in Phase 1)
  └── Dev: console backend
  └── Prod: django-anymail → Amazon SES
```

### Recommended Project Structure

```
compras_nexos/
├── config/
│   ├── settings/
│   │   ├── base.py          # Shared settings (AUTH_USER_MODEL, INSTALLED_APPS, etc.)
│   │   ├── dev.py           # EMAIL_BACKEND=console, DEBUG=True, DEBUG_TOOLBAR
│   │   └── prod.py          # EMAIL_BACKEND=anymail, SECURE_*, ALLOWED_HOSTS from env
│   ├── urls.py              # Root URL conf (includes apps.accounts.urls, apps.core.urls)
│   └── wsgi.py
├── apps/
│   ├── accounts/
│   │   ├── migrations/
│   │   │   ├── 0001_initial.py      # User + UnidadeOrganizacional + pg extensions
│   │   │   └── 0002_create_groups.py # Data migration: 5 Groups
│   │   ├── models.py        # User(AbstractUser), UnidadeOrganizacional
│   │   ├── services.py      # create_user(), deactivate_user(), assign_unit()
│   │   ├── views.py         # UserListView, UserCreateView, UserUpdateView,
│   │   │                    # UnitListView, UnitCreateView, UnitUpdateView
│   │   ├── forms.py         # UserCreateForm, UserEditForm, UnidadeForm
│   │   ├── urls.py          # /admin-panel/usuarios/ + /admin-panel/unidades/
│   │   ├── admin.py         # UserAdmin registered on Django admin site
│   │   └── templates/
│   │       └── accounts/
│   │           ├── login.html
│   │           ├── password_reset.html
│   │           ├── password_reset_confirm.html
│   │           ├── password_reset_done.html
│   │           ├── user_list.html
│   │           ├── user_form.html
│   │           ├── unit_list.html
│   │           └── unit_form.html
│   └── core/
│       ├── migrations/
│       ├── models.py        # TimestampedModel, AuditedModel (abstract)
│       ├── views.py         # DashboardView (stub)
│       ├── urls.py          # / → dashboard stub
│       └── templates/
│           └── core/
│               └── dashboard.html   # Empty KPI skeleton
├── templates/
│   └── base.html            # Layout, sidebar, topbar, HTMX CSRF config, django messages
├── static/
│   ├── css/
│   │   └── main.css         # Full design system (CSS custom properties, all components)
│   └── htmx/
│       └── htmx.min.js      # Vendored HTMX 2.0.x
├── Dockerfile               # Production image (python:3.12-slim, non-root, collectstatic)
├── docker-compose.yml       # Dev: web + db services, volume mounts, healthcheck
├── docker-compose.prod.yml  # Prod: restart: unless-stopped, no volume mounts
├── .env.example             # Template for required env vars
├── requirements.txt
└── requirements-dev.txt
```

### Pattern 1: Custom AbstractUser with Role + Default Unit

**What:** Extend `AbstractUser` with `role` CharField (5 TextChoices) and `default_unit` FK at project start.

**When to use:** Always — this is the Phase 1 core deliverable.

```python
# apps/accounts/models.py
# Source: Django official docs https://docs.djangoproject.com/en/5.2/topics/auth/customizing/
from django.contrib.auth.models import AbstractUser
from django.db import models


class UnidadeOrganizacional(models.Model):
    nome = models.CharField(max_length=150)
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Unidade Organizacional"
        verbose_name_plural = "Unidades Organizacionais"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class User(AbstractUser):
    class Role(models.TextChoices):
        SOLICITANTE = "solicitante", "Solicitante"
        GESTOR = "gestor", "Gestor"
        COMPRADOR = "comprador", "Comprador"
        DIRETOR = "diretor", "Diretor"
        ADMIN = "admin", "Admin"

    # Email as the login field
    email = models.EmailField(unique=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]  # kept for createsuperuser compat

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.SOLICITANTE,
    )
    default_unit = models.ForeignKey(
        UnidadeOrganizacional,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="default_users",
    )
```

```python
# config/settings/base.py
AUTH_USER_MODEL = "accounts.User"  # Must be set before first migrate
```

### Pattern 2: PostgreSQL Extensions in First Migration

**What:** Enable `pg_trgm` and `unaccent` in the `accounts` app's first migration.

**When to use:** Always — do it in `accounts/migrations/0001_initial.py` before any other migration depends on these.

```python
# apps/accounts/migrations/0001_initial.py
# Source: https://docs.djangoproject.com/en/5.2/ref/contrib/postgres/operations/
from django.contrib.postgres.operations import TrigramExtension, UnaccentExtension
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = []

    operations = [
        TrigramExtension(),
        UnaccentExtension(),
        # ... CreateModel for User and UnidadeOrganizacional follow
    ]
```

### Pattern 3: Groups Data Migration (5 Roles)

**What:** Create the 5 Django Groups via a data migration, not in fixtures or management commands.

**When to use:** Always — runs automatically with `manage.py migrate`, no manual step.

```python
# apps/accounts/migrations/0002_create_groups.py
from django.db import migrations

GRUPOS = ["Solicitante", "Gestor", "Comprador", "Diretor", "Admin"]


def create_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for nome in GRUPOS:
        Group.objects.get_or_create(name=nome)


def delete_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=GRUPOS).delete()


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]
    operations = [migrations.RunPython(create_groups, delete_groups)]
```

### Pattern 4: HTMX CSRF in base.html

**What:** Configure HTMX to send the CSRF token on every non-GET request via a JavaScript event listener.

**When to use:** Must be in `base.html` before any HTMX interaction is built. Set it once, never think about it again.

```html
<!-- templates/base.html -->
<!-- Source: django-htmx docs https://django-htmx.readthedocs.io/ -->
{% load django_htmx %}
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="csrf-token" content="{{ csrf_token }}">
  <link rel="stylesheet" href="{% static 'css/main.css' %}">
</head>
<body>
  {% htmx_script %}
  <script>
    document.body.addEventListener('htmx:configRequest', function(evt) {
      evt.detail.headers['X-CSRFToken'] = document.querySelector(
        'meta[name="csrf-token"]'
      ).content;
    });
  </script>
  ...
</body>
</html>
```

**Note:** The UI-SPEC also specifies `hx-headers` on `<body>` as the method. Both approaches are valid. The `htmx:configRequest` event approach is more explicit and easier to debug. Use whichever the planner chooses, but use exactly one — not both.

### Pattern 5: HTMX Partial Swap for Admin Forms

**What:** Admin forms (create/edit user, create/edit unit) use HTMX to provide inline validation feedback without full page reload.

**When to use:** All admin panel forms in Phase 1.

```html
<!-- accounts/user_form.html (partial usage) -->
<form hx-post="{% url 'accounts:user-create' %}"
      hx-target="#form-container"
      hx-swap="innerHTML">
  {% csrf_token %}
  {{ form.as_p }}
  <button type="submit" class="btn btn-primary">Criar usuário</button>
</form>
```

```python
# accounts/views.py
def user_create_view(request):
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            services.create_user(form.cleaned_data)
            if request.htmx:
                # Redirect to list — HTMX handles via HX-Redirect header
                from django_htmx.http import HttpResponseClientRedirect
                return HttpResponseClientRedirect(reverse("accounts:user-list"))
            return redirect("accounts:user-list")
        # Re-render form with errors — HTMX swaps it back in
        return render(request, "accounts/partials/user_form.html", {"form": form})
    form = UserCreateForm()
    return render(request, "accounts/user_form.html", {"form": form})
```

### Pattern 6: Deactivation with Inline Confirmation

**What:** Clicking "Desativar" loads a confirmation card via HTMX before executing the destructive action. No `window.confirm()`.

**When to use:** User deactivation, unit deactivation.

```html
<!-- In user_list.html — action column cell -->
<td>
  <a href="{% url 'accounts:user-edit' user.pk %}" class="action-link">Editar</a> ·
  <button hx-get="{% url 'accounts:user-deactivate-confirm' user.pk %}"
          hx-target="#confirm-container"
          hx-swap="innerHTML"
          class="btn btn-ghost btn-destructive">Desativar</button>
</td>
<div id="confirm-container"></div>
```

### Pattern 7: hx-boost on Sidebar Navigation

**What:** Enable `hx-boost` on the sidebar `<nav>` so navigation links act as AJAX page transitions (replaces only the content area, keeps sidebar stable).

```html
<nav class="sidebar" hx-boost="true">
  <a href="{% url 'core:dashboard' %}">Dashboard</a>
  ...
</nav>
```

**Caveat:** Any view that uses `hx-boost` navigation MUST serve a full page on direct URL access (`request.htmx` check is NOT needed for navigation — boost handles it). Partial-only views (those that check `if request.htmx`) should not be boosted.

### Anti-Patterns to Avoid

- **Starting with `python manage.py migrate` before creating the custom User model:** Generates `auth_user` table that conflicts with later custom model. Recovery requires painful manual migration.
- **Setting `INSTALLED_APPS = ['accounts']` vs `['apps.accounts']`:** Must match the Python module path exactly. If apps live in an `apps/` subdirectory, use `apps.accounts`.
- **Using `models.FloatField` for any monetary value:** Never. `DecimalField(max_digits=12, decimal_places=2)` only. Phase 1 has no monetary fields, but the `core/models.py` abstract base should document this rule.
- **Hardcoding `SECRET_KEY` in `settings/base.py`:** Always read from environment via `python-decouple`.
- **Running `collectstatic` before `STATIC_ROOT` and `STATICFILES_STORAGE` are configured:** Will fail silently or write to wrong directory. Configure in `base.py`, override in `prod.py`.
- **Using Django admin site for the application's admin panel:** Django's `/admin/` is for developer use. The custom admin panel at `/admin-panel/` is the user-facing interface. Both can coexist but must be distinct.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Session-based authentication | Custom session logic | Django's `authenticate()` + `login()` + `SessionMiddleware` | Handles session fixation, CSRF, cookie security out of the box |
| Password reset tokens | Custom token generation + email | Django `PasswordResetView` + `PasswordResetConfirmView` | Built-in views use HMAC tokens with expiry. Rolling your own creates security vulnerabilities. |
| CSRF protection | Manual token management | Django `CsrfViewMiddleware` + HTMX `htmx:configRequest` config | Django's implementation follows the Double Submit Cookie pattern. |
| Password hashing | Custom hashing | Django's built-in `PBKDF2PasswordHasher` | Django 5.2 defaults are PBKDF2 with SHA-256. Secure by default. |
| User model fields for profile | Separate `UserProfile` 1-to-1 model | `AbstractUser` extension with fields directly | 1-to-1 generates N+1 queries in templates everywhere. Direct extension is the official recommendation. |
| Role system | Custom permission tables, django-guardian | Django Groups + role CharField + `PermissionRequiredMixin` | Stable 5-role system. Object-level permissions unneeded. Group-based RBAC is simpler and fully sufficient. |
| Static file serving (dev) | Nginx or CDN configuration | WhiteNoise | Zero-dependency, zero-config static file serving from Django. Remove when adding CDN later. |
| Environment config | OS env vars or hardcoded values | `python-decouple` with `.env` file | Handles type coercion, defaults, and test isolation cleanly. |

**Key insight:** Django's built-in auth is mature, secure, and extensible enough for all Phase 1 auth requirements. The temptation to add third-party auth libraries for a 20-user internal system should be firmly resisted.

---

## Common Pitfalls

### Pitfall 1: Custom User Model After First Migration (CRITICAL)

**What goes wrong:** `manage.py migrate` runs before `accounts.User` exists. Django creates `auth_user` table. Later adding `AUTH_USER_MODEL = 'accounts.User'` causes `ValueError: Dependency on app with no migrations: accounts` and requires either schema surgery or project restart.

**Why it happens:** Developers scaffold the project quickly to "see it run" before doing the "boring" model work.

**How to avoid:** The very first thing after `django-admin startproject` — before any `migrate` — create `apps/accounts/models.py` with `User(AbstractUser)`, set `AUTH_USER_MODEL`, and create the migration. Only then run `migrate`.

**Warning signs:** Any discussion of "let's get the app running first and add the custom User later."

### Pitfall 2: Django 6.0 Installed Instead of 5.2 LTS

**What goes wrong:** `pip install Django` (without version pin) installs Django 6.0.6. Phase 1 code written against Django 5.2 APIs may have subtle incompatibilities. More critically, 6.0 is not LTS and EOLs in April 2027.

**Why it happens:** PyPI always resolves to the latest version without a pin. [VERIFIED: pip index versions Django shows 6.0.6 as current latest as of 2026-06-10]

**How to avoid:** `requirements.txt` must contain `Django==5.2.*`, not just `Django`. Verify with `python -c "import django; print(django.__version__)"` in the container.

**Warning signs:** Any `requirements.txt` that contains only `Django` without a version specifier.

### Pitfall 3: HTMX CSRF 403 on All POST Requests

**What goes wrong:** All HTMX form submissions and hx-post/hx-delete requests return 403 Forbidden. The developer sees the 403 in Network DevTools but the form appears correct because it has `{% csrf_token %}`.

**Why it happens:** `{% csrf_token %}` inside a `<form>` provides the token in the form body, but HTMX POSTs don't include the form body token unless using `hx-include`. The token must be in the `X-CSRFToken` HTTP header.

**How to avoid:** Configure the `htmx:configRequest` event listener in `base.html` before writing any HTMX interaction. [CITED: django-htmx.readthedocs.io]

**Warning signs:** Any HTMX form POST returning 403; the browser Network tab showing no `X-CSRFToken` header on the request.

### Pitfall 4: Docker Container Without Restart Policy

**What goes wrong:** EC2 instance reboots for patching. Docker container does not restart. System is down until someone SSH's in.

**How to avoid:** `restart: unless-stopped` on both `web` and `db` services in `docker-compose.prod.yml`. [CITED: PITFALLS.md L4]

**Warning signs:** Any `docker-compose.yml` service block without a `restart:` directive.

### Pitfall 5: ALLOWED_HOSTS / CSRF_TRUSTED_ORIGINS Not Set for Production

**What goes wrong:** The production Django container behind a load balancer gets CSRF errors on all POST forms because `CSRF_TRUSTED_ORIGINS` only has `http://localhost`. Or `ALLOWED_HOSTS = ['*']` is used as a "fix" creating a security risk.

**How to avoid:** Both settings must be read from environment variables:
```python
# config/settings/prod.py
ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=lambda v: [s.strip() for s in v.split(",")])
CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", cast=lambda v: [s.strip() for s in v.split(",")])
```

### Pitfall 6: INSTALLED_APPS Path Mismatch

**What goes wrong:** Apps live in `compras_nexos/apps/accounts/` but `INSTALLED_APPS` contains `'accounts'`. Django cannot find the app. Or worse: Django finds a differently-named package on the Python path.

**How to avoid:** `INSTALLED_APPS` must use the full dotted path matching the module hierarchy: `'apps.accounts'`, `'apps.core'`. Verify with `python manage.py check`.

---

## Code Examples

### settings/base.py (core sections)

```python
# Source: Django 5.2 official docs https://docs.djangoproject.com/en/5.2/ref/settings/
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)

AUTH_USER_MODEL = "accounts.User"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    # Third-party
    "django_htmx",
    # Local apps
    "apps.core",
    "apps.accounts",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {
        "context_processors": [
            "django.template.context_processors.debug",
            "django.template.context_processors.request",
            "django.contrib.auth.context_processors.auth",
            "django.contrib.messages.context_processors.messages",
        ],
    },
}]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="compras_nexos"),
        "USER": config("DB_USER", default="compras"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST", default="db"),
        "PORT": config("DB_PORT", default="5432"),
    }
}

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_L10N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
```

### Abstract Base Models (core/models.py)

```python
# Source: Django 5.2 official docs https://docs.djangoproject.com/en/5.2/topics/db/models/
from django.conf import settings
from django.db import models


class TimestampedModel(models.Model):
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditedModel(TimestampedModel):
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="%(app_label)s_%(class)s_criado",
    )

    class Meta:
        abstract = True
```

### Docker dev setup

```yaml
# docker-compose.yml
# Source: STACK.md verified pattern
version: "3.9"
services:
  web:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.dev
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data/
    environment:
      - POSTGRES_DB=compras_nexos
      - POSTGRES_USER=compras
      - POSTGRES_PASSWORD=dev_password
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U compras"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

### Production Dockerfile

```dockerfile
# Source: STACK.md verified pattern + Django deployment docs
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

RUN useradd --no-create-home --no-log-init app && chown -R app /app
USER app

EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "60", \
     "--log-level", "info"]
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact for Phase 1 |
|--------------|------------------|--------------|-------------------|
| `UserProfile` 1-to-1 model for extra fields | `AbstractUser` direct extension | Django 1.5+ | Direct extension avoids N+1 everywhere. Use `AbstractUser`, never 1-to-1. |
| `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_USE_TLS` settings for email | `MAILERS` dict config | Django 5.x (legacy settings deprecated in Django 7.0) | Use `MAILERS` in new projects to avoid deprecation warning. [CITED: PITFALLS.md M5] |
| `STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'` | `STORAGES = {"staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"}}` | Django 4.2+ | Both work in Django 5.2. New-style `STORAGES` dict preferred for new projects to avoid future deprecation. [ASSUMED: exact deprecation timeline — verify at implementation] |
| `django.contrib.auth.views.LoginView` with `template_name` override | Same — still current | — | No change. Built-in LoginView still the right choice. |

**Deprecated/outdated:**
- `django-allauth` for internal admin-managed user systems: Not deprecated, but wrong tool. Never use for this project.
- `Celery` for Phase 1 email: Not needed. `transaction.on_commit()` + synchronous send is correct for password reset at 20-user scale.

---

## UI Contract Summary (from 01-UI-SPEC.md)

The UI-SPEC is a binding contract for Phase 1 implementation. Key implementation requirements:

**Design system:**
- Single CSS file: `static/css/main.css`
- All colors as CSS custom properties: `--color-bg: #1a1a2e`, `--color-surface: #16213e`, `--color-accent: #e94560`
- No Bootstrap, no Tailwind, no utility frameworks
- System font stack only — no HTTP font requests

**Pages required (11 total):**
- `/accounts/login/` — full-viewport centered card, no sidebar
- `/accounts/password-reset/` — same card layout
- `/accounts/password-reset-confirm/<uid>/<token>/` — same card layout
- `/accounts/password-reset/done/` — same card layout
- `/` — dashboard stub (empty KPI skeleton with sidebar)
- `/admin-panel/usuarios/` — user list table
- `/admin-panel/usuarios/novo/` — user create form
- `/admin-panel/usuarios/<id>/editar/` — user edit form
- `/admin-panel/unidades/` — unit list table
- `/admin-panel/unidades/nova/` — unit create form
- `/admin-panel/unidades/<id>/editar/` — unit edit form

**HTMX patterns (Phase 1 only):**
- Admin form submit: `hx-post` → `#form-container` → `innerHTML`
- Deactivate confirmation: `hx-get` → `#confirm-container` → `innerHTML`
- Execute deactivation: `hx-post` → `#user-row-{id}` → `outerHTML`
- `hx-boost` on `<nav class="sidebar">` for navigation

**All copy in pt-BR** (formal register). Key strings defined verbatim in UI-SPEC copywriting contract.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | AWS RDS PostgreSQL 15 is available in the target AWS region | Standard Stack | Low — 15 is supported in all major AWS regions; worst case use 16 |
| A2 | `STORAGES` dict is the new-style API in Django 5.2 for WhiteNoise | State of the Art | Low — both old and new style work in 5.2; old style is safe until Django 7.0 |
| A3 | EC2 vs ECS deployment decision is still unresolved | Architecture | Low for Phase 1 code; affects prod docker-compose vs ECS task definition |
| A4 | The `MAILERS` dict config is the non-deprecated path for email in Django 5.2 | Code Examples | Low — legacy `EMAIL_*` settings still work in 5.2; `MAILERS` preferred for forward compatibility |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed.
*(Table is not empty — 4 low-risk assumptions documented above.)*

---

## Open Questions (RESOLVED)

1. **Single `default_unit` FK vs multi-unit membership (ManyToManyField)**
   - What we know: UNIT-02 says "Admin vincula usuários a unidades" and UNIT-03 says "usuário tem unidade padrão." AUTH-06 says "cada usuário está vinculado a uma unidade padrão."
   - What's unclear: Can a user belong to multiple units (e.g., a Comprador covering 3 units) while having one default? Or is it strictly one user = one unit?
   - Recommendation: Implement `default_unit = ForeignKey(UnidadeOrganizacional, null=True)` on User for Phase 1. Do NOT add ManyToManyField without explicit client requirement — it complicates filtering in every downstream query. Phase 2+ can add M2M if the business need is confirmed.
   - **RESOLVED:** Use `default_unit = ForeignKey(UnidadeOrganizacional, null=True, blank=True, on_delete=SET_NULL)` only. No ManyToManyField in Phase 1. Decision: single FK is sufficient for all Phase 1 requirements (AUTH-06, UNIT-02, UNIT-03). M2M deferred to Phase 2+ pending confirmed business need.

2. **Django admin site (`/admin/`) alongside custom admin panel (`/admin-panel/`)**
   - What we know: The custom admin panel is the user-facing interface. Django's `/admin/` can be retained for developer/superuser use.
   - What's unclear: Should `/admin/` be disabled in production or kept?
   - Recommendation: Keep `/admin/` enabled but accessible only to `is_superuser=True` users (Django default). Document this in `.env.example`. Do not remove it — it's valuable for debugging.
   - **RESOLVED:** Keep `/admin/` enabled. Access restricted to `is_superuser=True` by Django default. No configuration change needed. Document in `.env.example` that superuser is created via `manage.py createsuperuser` inside Docker.

3. **Password reset email backend in Phase 1**
   - What we know: AUTH-02 requires password reset via email. SES + DKIM setup is listed as a Phase 2 blocker in STATE.md.
   - What's unclear: Should Phase 1 complete AUTH-02 end-to-end with real email, or deliver the flow with console backend only?
   - Recommendation: Implement the full Django password reset flow. In dev, use `console` backend (email prints to stdout). In prod, the `django-anymail` SES backend is configured via env vars. The code is complete — SES domain verification is an operations task, not a code task. Do not block Phase 1 completion on SES DNS records.
   - **RESOLVED:** Phase 1 delivers the full password reset code flow using `console` backend in dev (`EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'`). Production SES wiring via `django-anymail` is configured via env vars but not tested until SES domain verification is complete (operations task, not a code blocker for Phase 1 acceptance).

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | Runtime | ✗ (3.14.5 installed) | 3.14.5 | Docker container uses `python:3.12-slim` — dev runs inside Docker |
| Docker | Container runtime | ✓ | 29.5.2 | — |
| Docker Compose | Dev environment | ✓ | v5.1.3 | — |
| PostgreSQL | Database | ✗ (no local install) | — | Runs via Docker (`postgres:15-alpine`) |
| pip | Package manager | ✓ | 26.1.1 | — |

**Missing dependencies with no fallback:**
- Python 3.12 locally: Resolved by running everything inside Docker. The dev workflow is `docker compose up`, not `python manage.py runserver` directly on the host.

**Missing dependencies with fallback:**
- None. Docker covers all runtime dependencies.

**Note on Python 3.14:** The host machine has Python 3.14.5. The project must run on 3.12 inside Docker. The `FROM python:3.12-slim` Dockerfile declaration enforces this. Local Python version is irrelevant when developing inside containers.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-django (to be installed) |
| Config file | `pytest.ini` or `pyproject.toml [tool.pytest.ini_options]` — Wave 0 creates this |
| Quick run command | `docker compose run --rm web pytest apps/accounts/ -x -q` |
| Full suite command | `docker compose run --rm web pytest -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-01 | Login with valid email/password returns 200 + session | Integration | `pytest apps/accounts/tests/test_auth.py::test_login_success -x` | ❌ Wave 0 |
| AUTH-01 | Login with wrong password returns 200 with error message | Integration | `pytest apps/accounts/tests/test_auth.py::test_login_wrong_password -x` | ❌ Wave 0 |
| AUTH-02 | Password reset request with valid email sends email | Integration | `pytest apps/accounts/tests/test_auth.py::test_password_reset_sends_email -x` | ❌ Wave 0 |
| AUTH-03 | Session cookie persists across requests | Integration | `pytest apps/accounts/tests/test_auth.py::test_session_persists -x` | ❌ Wave 0 |
| AUTH-04 | Admin can create user with all required fields | Integration | `pytest apps/accounts/tests/test_user_mgmt.py::test_admin_create_user -x` | ❌ Wave 0 |
| AUTH-04 | Admin can deactivate user (is_active=False) | Integration | `pytest apps/accounts/tests/test_user_mgmt.py::test_admin_deactivate_user -x` | ❌ Wave 0 |
| AUTH-05 | All 5 Groups exist after migration | Unit | `pytest apps/accounts/tests/test_models.py::test_groups_exist -x` | ❌ Wave 0 |
| AUTH-06 | User.default_unit FK saves and reads correctly | Unit | `pytest apps/accounts/tests/test_models.py::test_user_default_unit -x` | ❌ Wave 0 |
| UNIT-01 | Admin can create unit with name, description, active status | Integration | `pytest apps/accounts/tests/test_unit_mgmt.py::test_create_unit -x` | ❌ Wave 0 |
| UNIT-02 | Admin can assign unit to user via edit form | Integration | `pytest apps/accounts/tests/test_unit_mgmt.py::test_assign_unit_to_user -x` | ❌ Wave 0 |
| UNIT-03 | User.default_unit available as initial value for requisition form (model check) | Unit | `pytest apps/accounts/tests/test_models.py::test_default_unit_available -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `docker compose run --rm web pytest apps/accounts/ -x -q`
- **Per wave merge:** `docker compose run --rm web pytest -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `apps/accounts/tests/__init__.py` — test package
- [ ] `apps/accounts/tests/test_auth.py` — login, password reset, session tests
- [ ] `apps/accounts/tests/test_user_mgmt.py` — create/edit/deactivate user tests
- [ ] `apps/accounts/tests/test_unit_mgmt.py` — unit CRUD tests
- [ ] `apps/accounts/tests/test_models.py` — model unit tests (groups, FK, etc.)
- [ ] `apps/core/tests/__init__.py` — core test package
- [ ] `pytest.ini` or `pyproject.toml [tool.pytest.ini_options]` — test config
- [ ] `requirements-dev.txt` additions: `pytest`, `pytest-django`

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes | Django `authenticate()` + `login()`, `AbstractUser`, PBKDF2 password hashing by default |
| V3 Session Management | Yes | `django.contrib.sessions` — DB-backed sessions, `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SECURE=True` in prod |
| V4 Access Control | Yes | `LoginRequiredMixin` on all authenticated views, custom `@role_required` decorator for role-gated views |
| V5 Input Validation | Yes | Django forms (`UserCreateForm`, `UnidadeForm`) — `clean_*` methods, ModelForm field validation |
| V6 Cryptography | Partial | Django built-in password hashing (PBKDF2/SHA-256). Password reset uses HMAC tokens. Never hand-roll. |

### Known Threat Patterns for Django Auth

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Session fixation | Elevation of Privilege | Django calls `cycle_key()` after login automatically |
| CSRF on state-changing views | Tampering | `CsrfViewMiddleware` + `htmx:configRequest` header injection |
| Inactive user login | Elevation of Privilege | Django `authenticate()` checks `is_active` before returning a user |
| Open redirect on LOGIN_REDIRECT_URL | Spoofing | Django validates `next=` parameter against safe URL list; never pass untrusted `next` |
| Admin panel access by non-Admin role | Elevation of Privilege | `PermissionRequiredMixin` on all `/admin-panel/` views; check `user.role == 'admin'` |
| Password reset token reuse | Elevation of Privilege | Django invalidates token after first use and applies `PASSWORD_RESET_TIMEOUT` (default 3 days) |

---

## Sources

### Primary (HIGH confidence)
- Django 5.2 LTS status: djangoproject.com/download/ — confirmed LTS, supported through April 2028
- Django 5.2 custom user model: https://docs.djangoproject.com/en/5.2/topics/auth/customizing/
- Django 5.2 built-in auth views: https://docs.djangoproject.com/en/5.2/topics/auth/default/
- Django 5.2 transactions (on_commit): https://docs.djangoproject.com/en/5.2/topics/db/transactions/
- Django 5.2 settings reference (AUTH_USER_MODEL, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS): https://docs.djangoproject.com/en/5.2/ref/settings/
- PostgreSQL extensions (TrigramExtension, UnaccentExtension): https://docs.djangoproject.com/en/5.2/ref/contrib/postgres/operations/
- django-htmx docs: https://django-htmx.readthedocs.io/
- Project research files: STACK.md, ARCHITECTURE.md, PITFALLS.md, SUMMARY.md (all HIGH confidence, synthesized from official sources)

### Secondary (MEDIUM confidence)
- PyPI package version verification (all 8 packages): pip index versions — current as of 2026-06-10
- slopcheck 0.6.1 legitimacy scan: all 8 packages returned [OK]
- UI-SPEC contract: `01-UI-SPEC.md` — design system tokens, component specs, pages list

### Tertiary (LOW confidence)
- `STORAGES` dict deprecation timeline for old-style whitenoise config — not confirmed with exact Django version, check at implementation

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified on PyPI, slopcheck clean, Django 5.2 LTS confirmed
- Architecture: HIGH — derived from official Django docs and prior project research
- Pitfalls: HIGH — C1, C2, C4 are documented Django gotchas from official docs; L4, L7 from production deployment docs
- UI contract: HIGH — read directly from 01-UI-SPEC.md

**Research date:** 2026-06-10
**Valid until:** 2026-07-10 (stable stack — Django LTS, stable library versions)

**Critical action for planner:** Ensure `requirements.txt` pins `Django==5.2.*`. pip resolves to 6.0.6 without the pin. This is a breaking constraint.
