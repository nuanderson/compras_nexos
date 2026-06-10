# Technology Stack — ComprasNexos

**Project:** Sistema de Gestão de Compras (ComprasNexos)
**Researched:** 2026-06-10
**Confidence:** HIGH (core stack confirmed via official Django docs, Context7 resolution, and PyPI verification)

---

## Core Framework

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| Python | 3.12 | Runtime | Client-mandated. 3.12 is stable, well-supported through 2028. Do not use 3.13 yet — ecosystem compatibility still catching up. |
| Django | 5.2 LTS | Web framework | Django 5.2 is the current LTS release (April 2025, supported until April 2028). Supports Python 3.10–3.14. Includes composite PKs, async auth methods, new form widgets. Use this, not 5.1 or 5.0 which are non-LTS. |
| HTMX | 2.0.x | Frontend interactivity | HTMX 2.0 is current stable. Confirmed via Context7 library resolution showing `v1.9.12` and `v2.0.4` as tracked versions. Use 2.0.x — it removes the IE11 compatibility overhead and has cleaner event model than 1.x. Serve via CDN or vendored in `static/`. |
| django-htmx | latest (1.x) | HTMX/Django integration | Adam Johnson's `django-htmx` resolves at `/adamchainz/django-htmx` in Context7 (109 snippets, High reputation). Provides `HtmxMiddleware` that adds `request.htmx` attribute, `HtmxResponseMixin`, and response trigger helpers. Essential — do not implement this manually. |
| PostgreSQL | 15 or 16 | Primary database | 15 is the safe choice on AWS RDS as of 2025. 16 is available but newer. Use `pg_trgm` extension for supplier name fuzzy search. `django.contrib.postgres` provides ORM-level access to all PostgreSQL-specific features. |

---

## Django App Structure

The project follows a **domain-bounded app structure**. Each Django app is a self-contained business subdomain. This matches the architecture decision already logged in PROJECT.md.

```
compras_nexos/          # Django project root
├── config/             # Settings, URLs, WSGI/ASGI
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── accounts/       # Auth, users, roles, permissions
│   ├── requisicoes/    # Purchase requisitions + status tracking
│   ├── aprovacoes/     # Approval workflow engine + thresholds
│   ├── fornecedores/   # Supplier registry + ratings
│   ├── cotacoes/       # RFQ management + price comparison
│   └── relatorios/     # Reports, KPIs, PDF export
├── templates/          # Global base templates
│   └── partials/       # HTMX-specific partial templates
├── static/
│   ├── htmx/           # Vendored htmx.min.js
│   ├── css/
│   └── js/
└── manage.py
```

**Why `apps/` subdirectory:** Keeps project root clean, avoids naming conflicts with third-party packages, makes `INSTALLED_APPS` paths explicit (`apps.accounts`, not `accounts`).

**Each app contains:**
```
app_name/
├── models.py       # Data layer only — no business logic
├── services.py     # Business logic layer (approval transitions, RFQ creation)
├── views.py        # Thin views — delegate to services
├── forms.py        # Django forms for validation
├── urls.py         # App-scoped URL patterns
├── admin.py        # Admin configuration
├── managers.py     # Custom QuerySet managers
└── templates/
    └── app_name/   # Template namespacing
        ├── list.html
        ├── detail.html
        └── partials/   # HTMX partial responses
```

**Service layer pattern:** Business logic (e.g., `aprovar_requisicao()`, `criar_rfq()`) lives in `services.py`, not in models or views. Views are thin: validate input, call service, return response. This is the correct pattern for an approval workflow where state transitions have business rules.

---

## Authentication

**Recommendation: Custom `AbstractUser` + Django's built-in auth. Do NOT use django-allauth.**

**Rationale:**

django-allauth is designed for social login, email verification flows, self-registration, and OAuth. None of these apply here. This is an internal corporate system where:
- Users are created by Admin — no registration form needed
- Login is email + password — no social providers
- No 2FA required (explicitly out of scope)
- No SSO (out of scope)

django-allauth adds ~20 URL patterns, multiple models, configuration surface, and template overrides for features you will not use. It creates friction without value.

**What to use instead:**

```python
# apps/accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    Custom user model — always define this at project start.
    Changing mid-project requires a painful migration reset.
    """
    class Role(models.TextChoices):
        SOLICITANTE = 'solicitante', 'Solicitante'
        GESTOR = 'gestor', 'Gestor'
        COMPRADOR = 'comprador', 'Comprador'
        DIRETOR = 'diretor', 'Diretor'
        ADMIN = 'admin', 'Admin'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.SOLICITANTE,
    )
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

# config/settings/base.py
AUTH_USER_MODEL = 'accounts.User'
```

**Role enforcement:** Use Django's `@login_required` + custom `@role_required` decorator built on `user_passes_test`. Do not use django-guardian (object-level permissions) — the project's permission model is role-based at the view level, not object-level. Guardian adds complexity without corresponding benefit at this scale.

**Critical:** Set `AUTH_USER_MODEL` before the first migration. After that, changing it is a migration nightmare.

---

## Approval Workflow

**Recommendation: Custom state machine in `aprovacoes/services.py` using `select_for_update`. Do NOT use a workflow library.**

**Rationale:** Libraries like `django-fsm`, `viewflow`, or `django-workflow` add abstraction layers that make debugging harder. This system has a well-defined, stable two-level approval flow (Gestor → Diretor). The concurrency concern (two approvers clicking simultaneously) is solved by `select_for_update()`, not by a library.

```python
# apps/aprovacoes/services.py
from django.db import transaction

@transaction.atomic
def aprovar_requisicao(requisicao_id, aprovador):
    req = Requisicao.objects.select_for_update().get(id=requisicao_id)
    # transition logic here — raises exception if invalid state
```

**Configurable thresholds:** Store approval threshold values in a `ConfiguracaoAlcada` model, editable via Django Admin. Admin sets values without code deploy. Use `functools.lru_cache` or a simple `AppConfig.ready()` cache buster on save signal to avoid N+1 DB hits per request.

---

## Email Notifications

**Recommendation: Django's built-in SMTP backend + `transaction.on_commit()`. No Celery for v1.**

**Rationale:** The scale is 20 users. Email volume is low (a few emails per approval event). Adding Celery requires Redis or RabbitMQ as a broker, a separate worker container, monitoring, and operational complexity. For 20 users this is engineering theater.

`transaction.on_commit()` solves the critical correctness problem (don't send email if the DB transaction rolls back):

```python
# In services.py
from django.db import transaction
from django.core import mail

@transaction.atomic
def aprovar_requisicao(req, aprovador):
    req.status = 'aprovado'
    req.save()
    
    transaction.on_commit(
        lambda: mail.send_mail(
            subject='Requisição aprovada',
            message=f'Sua requisição #{req.id} foi aprovada.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[req.solicitante.email],
        )
    )
```

**For the SMTP provider:** Use Amazon SES via `django-anymail`. SES is cheap (first 62,000 emails/month free from EC2), reliable, and integrates with the existing AWS infrastructure. `django-anymail` provides a clean Django `EmailBackend` that wraps SES (and other providers) without changing how you call `send_mail()`. This means you can swap providers later without touching application code.

```bash
pip install django-anymail[amazon_ses]
```

```python
# settings/prod.py
EMAIL_BACKEND = "anymail.backends.amazon_ses.EmailBackend"
ANYMAIL = {
    "AMAZON_SES_CLIENT_PARAMS": {
        "region_name": "us-east-1",
    },
}
DEFAULT_FROM_EMAIL = "compras@suaempresa.com.br"
```

**When to add Celery:** If email sending becomes a user-perceptible bottleneck (e.g., bulk notifications), or if v2 adds background PDF generation for reports. Not in v1.

---

## PDF Generation

**Recommendation: ReportLab via `io.BytesIO` buffer pattern. Django's official docs endorse this approach.**

The Django docs explicitly recommend ReportLab and show the `BytesIO` buffer pattern as the canonical approach:

```python
# apps/relatorios/pdf.py
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from django.http import FileResponse

def gerar_pdf_relatorio_gastos(dados, periodo):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    # build content with Platypus (higher-level than canvas)
    doc.build(elements)
    buffer.seek(0)
    return FileResponse(
        buffer,
        as_attachment=True,
        filename=f'relatorio-gastos-{periodo}.pdf',
        content_type='application/pdf',
    )
```

**Use Platypus (ReportLab's layout engine), not raw `canvas`:** Platypus handles multi-page documents, table pagination, and paragraph flows automatically. Raw `canvas` requires manual coordinate calculation — painful for tabular procurement reports.

**Key ReportLab classes for this domain:**
- `SimpleDocTemplate` — document container
- `Table` + `TableStyle` — price comparison tables, RFQ summaries
- `Paragraph` + `getSampleStyleSheet` — headers, body text
- `KeepTogether` — keep summary rows from splitting across pages

**Do not use WeasyPrint or xhtml2pdf** (client specified ReportLab).

---

## HTMX Patterns for This Project

### Pattern 1: Form submission with inline error feedback

```html
<!-- Template: partials/requisicao_form.html -->
<form hx-post="{% url 'requisicoes:criar' %}"
      hx-target="#form-container"
      hx-swap="innerHTML">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit">Enviar</button>
</form>
```

```python
# View
def criar_requisicao(request):
    if request.method == 'POST':
        form = RequisicaoForm(request.POST)
        if form.is_valid():
            req = services.criar_requisicao(request.user, form.cleaned_data)
            if request.htmx:
                return HttpResponse(headers={'HX-Redirect': req.get_absolute_url()})
            return redirect(req)
        # Re-render form with errors — HTMX swaps it back in
        return render(request, 'requisicoes/partials/form.html', {'form': form})
    form = RequisicaoForm()
    return render(request, 'requisicoes/criar.html', {'form': form})
```

### Pattern 2: Status badge updates (real-time feel without WebSockets)

For a 20-user internal system, polling is the right approach. WebSockets add infrastructure complexity (ASGI, channel layers, Redis pub/sub) that is unwarranted at this scale.

```html
<!-- Status badge that refreshes every 15 seconds -->
<span id="status-req-{{ req.id }}"
      hx-get="{% url 'requisicoes:status' req.id %}"
      hx-trigger="every 15s"
      hx-swap="outerHTML">
    {{ req.get_status_display }}
</span>
```

### Pattern 3: Modal dialogs for approval actions

```html
<!-- Trigger -->
<button hx-get="{% url 'aprovacoes:modal_aprovar' req.id %}"
        hx-target="#modal-container"
        hx-swap="innerHTML">
    Aprovar
</button>

<!-- Modal container in base template -->
<div id="modal-container"></div>
```

```python
# Returns a partial template containing the modal HTML + confirmation form
def modal_aprovar(request, req_id):
    req = get_object_or_404(Requisicao, id=req_id)
    return render(request, 'aprovacoes/partials/modal_aprovar.html', {'req': req})
```

### Pattern 4: Live search for supplier lookup

```html
<input type="search"
       name="q"
       hx-get="{% url 'fornecedores:buscar' %}"
       hx-trigger="keyup changed delay:300ms"
       hx-target="#supplier-results"
       placeholder="Buscar fornecedor...">
<div id="supplier-results"></div>
```

### CSRF with HTMX

django-htmx's `HtmxMiddleware` does not handle CSRF automatically — you must include `{% csrf_token %}` inside `<form>` tags (standard Django behavior). For non-form HTMX requests (e.g., `hx-delete`), add the token via a `<meta>` tag and HTMX config:

```html
<!-- base.html -->
<meta name="csrf-token" content="{{ csrf_token }}">
<script>
  document.body.addEventListener('htmx:configRequest', (event) => {
    event.detail.headers['X-CSRFToken'] = document.querySelector('meta[name="csrf-token"]').content;
  });
</script>
```

### `hx-boost` usage

Enable `hx-boost` on the `<body>` or navigation elements to turn standard links into AJAX navigations (replaces only `<body>`, keeps `<head>`). This gives SPA-like feel for free. However: be deliberate — some pages with complex JS initialization may need `hx-boost="false"` to opt out.

---

## Database: PostgreSQL Extensions and Patterns

### Recommended extensions

| Extension | Purpose | How to Enable |
|-----------|---------|---------------|
| `pg_trgm` | Fuzzy search for supplier names, product descriptions | `TrigramExtension()` in migration |
| `uuid-ossp` | UUID primary keys if needed | Built into PostgreSQL 15+ |
| `unaccent` | Search without accent sensitivity (critical for Brazilian Portuguese) | `UnaccentExtension()` in migration |

```python
# In an early migration (e.g., accounts/0001_initial.py)
from django.contrib.postgres.operations import TrigramExtension, UnaccentExtension

class Migration(migrations.Migration):
    operations = [
        TrigramExtension(),
        UnaccentExtension(),
    ]
```

**`unaccent` is critical for this project.** Searching "fornecedores" when user types "fornecedores" without accent, or searching supplier names that may use "Sao Paulo" vs "São Paulo" — unaccent normalization prevents these mismatches.

### Key ORM patterns

**Use `select_related` and `prefetch_related` aggressively.** The approval workflow views load requisitions with related solicitante, gestor, and status history — N+1 queries will appear immediately without these.

**Use `F()` expressions for atomic counter updates** (e.g., incrementing a `total_cotacoes` counter).

**Use `transaction.on_commit()` for all post-save side effects** (email, audit log writes to separate tables).

### Indexing strategy for procurement queries

```python
class Requisicao(models.Model):
    class Meta:
        indexes = [
            # Frequent filter: "show my pending requisitions"
            models.Index(fields=['solicitante', 'status']),
            # Frequent filter: "show all in date range"
            models.Index(fields=['criado_em']),
            # Dashboard KPI: "count by status"
            models.Index(fields=['status', 'criado_em']),
        ]
```

---

## Supporting Libraries

| Library | Version | Purpose | Install |
|---------|---------|---------|---------|
| `django-htmx` | latest | HTMX request detection + response helpers | `pip install django-htmx` |
| `django-anymail` | latest | SES/SMTP email backend abstraction | `pip install django-anymail[amazon_ses]` |
| `reportlab` | latest | PDF generation | `pip install reportlab` |
| `psycopg2-binary` | 2.9.x | PostgreSQL adapter (binary for Docker) | `pip install psycopg2-binary` |
| `gunicorn` | latest | WSGI server for production | `pip install gunicorn` |
| `whitenoise` | 6.x | Static file serving from Django (no Nginx needed for v1) | `pip install whitenoise` |
| `python-decouple` | 3.x | Environment variable management | `pip install python-decouple` |
| `django-debug-toolbar` | latest | Dev-only query inspection | `pip install django-debug-toolbar` |

**On `whitenoise` for static files:** For a small internal system on EC2, WhiteNoise serving static files from the Django container is perfectly acceptable and eliminates Nginx complexity. If the client moves to ECS with a CDN, switch to django-storages + S3 at that point. Do not over-engineer static file serving for v1.

**On `psycopg2-binary` vs `psycopg2`:** Use binary in Docker (avoids C build dependencies in the container). If you have build tools available, plain `psycopg2` is marginally more reliable in production, but binary works fine.

---

## Docker Setup

### Development

```yaml
# docker-compose.yml
version: '3.9'
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
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application
COPY . .

# Collect static files at build time
RUN python manage.py collectstatic --noinput

# Non-root user
RUN useradd --no-create-home --no-log-init app && chown -R app /app
USER app

EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "60", \
     "--log-level", "info"]
```

**Worker count formula:** `(2 × CPU cores) + 1`. For a t3.small (2 vCPU), 3–5 workers is correct. For 20 users, 3 workers is sufficient.

### Production docker-compose (EC2)

```yaml
# docker-compose.prod.yml
version: '3.9'
services:
  web:
    image: compras_nexos:latest
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.prod
    env_file:
      - .env.prod
    depends_on:
      - db  # Remove if using RDS (recommended)

  db:
    # Only include if NOT using RDS
    # For production, use AWS RDS PostgreSQL instead
    image: postgres:15-alpine
    restart: unless-stopped
    volumes:
      - postgres_data:/var/lib/postgresql/data/
    env_file:
      - .env.prod
```

**AWS recommendation:** Use RDS PostgreSQL instead of a Dockerized database in production. RDS handles backups, point-in-time recovery, and failover. For a client with no internal tech team, RDS is the correct choice. The `db` service in production compose should be removed and replaced with `DATABASE_URL` pointing to the RDS endpoint.

---

## What NOT to Use — and Why

| Package | Why Not |
|---------|---------|
| **django-allauth** | Built for social auth and self-registration. Zero benefit for an admin-managed internal system. Adds complexity without value. |
| **Celery + Redis** | Overkill for 20 users and low email volume. Adds two new infrastructure components (broker + worker container). Use `transaction.on_commit()` for synchronous-but-safe email. Reconsider in v2 if needed. |
| **Django Channels / ASGI** | WebSockets are not needed for a 20-user internal system. HTMX polling every 15s is sufficient for status updates. Channels requires a channel layer (Redis), ASGI server, and stateful connections — all complexity not justified. |
| **django-fsm or viewflow** | The approval workflow is two levels with clear transitions. A custom `services.py` with `select_for_update()` is simpler, debuggable, and sufficient. Workflow libraries are valuable when rules are dynamic or user-configurable; here they're not. |
| **django-guardian** | Object-level permissions are not required. Role-based access (decorator `@role_required`) is sufficient and much simpler. |
| **React / Vue / Alpine.js** | Stack is HTMX — client decision. Alpine.js could supplement HTMX for client-side state (e.g., form toggles) but adds a second JS mental model. Evaluate only if HTMX alone cannot handle a specific interaction. |
| **xhtml2pdf / WeasyPrint** | Client specified ReportLab. Do not introduce alternatives. |
| **Django REST Framework** | No API needed in v1. If external ERP integration is built in a future phase, add DRF then. Do not add it preemptively. |
| **SQLite** | Do not use in any environment. Use PostgreSQL everywhere (dev, CI, prod) to avoid dialect surprises with `pg_trgm`, `unaccent`, and JSON fields. |

---

## Installation: `requirements.txt`

```
# Core
Django==5.2.*
psycopg2-binary==2.9.*

# HTMX integration
django-htmx

# Email
django-anymail[amazon_ses]

# PDF
reportlab

# Static files (production)
whitenoise

# WSGI server
gunicorn

# Config
python-decouple

# Dev only (move to requirements-dev.txt)
django-debug-toolbar
```

---

## Sources

- Django 5.2 release notes: https://docs.djangoproject.com/en/5.2/releases/5.2/ — confirmed LTS, Python 3.10–3.14 support (HIGH confidence)
- Django 5.2 release listing: https://docs.djangoproject.com/en/5.2/releases/ — 5.2.15 confirmed as latest patch (HIGH confidence)
- HTMX version: Context7 library resolution `/bigskysoftware/htmx` shows v1.9.12 and v2.0.4 as tracked versions — 2.0.x is current stable (HIGH confidence)
- django-htmx: Context7 library resolution `/adamchainz/django-htmx`, 109 snippets, High reputation (HIGH confidence)
- Django email docs: https://docs.djangoproject.com/en/5.2/topics/email/ — SMTP backend, `on_commit` pattern confirmed (HIGH confidence)
- Django PDF output: https://docs.djangoproject.com/en/5.2/howto/outputting-pdf/ — BytesIO/ReportLab pattern is official recommendation (HIGH confidence)
- PostgreSQL full-text search + pg_trgm: https://docs.djangoproject.com/en/5.2/ref/contrib/postgres/search/ — TrigramExtension, UnaccentExtension confirmed (HIGH confidence)
- select_for_update: https://docs.djangoproject.com/en/5.2/ref/models/querysets/#select-for-update — confirmed for concurrent approval safety (HIGH confidence)
- Django custom managers: https://docs.djangoproject.com/en/5.2/topics/db/managers/ — service layer pattern confirmed (HIGH confidence)
- Django custom auth: https://docs.djangoproject.com/en/5.2/topics/auth/customizing/ — AbstractUser + role field is the recommended approach (HIGH confidence)
- Django production settings: https://docs.djangoproject.com/en/5.2/ref/settings/ — security settings confirmed (HIGH confidence)
- Gunicorn deployment: https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/gunicorn/ (HIGH confidence)
- django-anymail and WhiteNoise versions: training data + PyPI knowledge (MEDIUM confidence — verify exact version pins at install time)
