<!-- GSD:project-start source:PROJECT.md -->

## Project

**ComprasNexos**

Sistema de gestão de compras para cliente corporativo de pequeno porte (até 20 usuários). Permite que solicitantes abram requisições de compra, gestores e diretores aprovem em dois níveis, compradores gerenciem cotações com fornecedores, e que a empresa tenha visibilidade total dos gastos por categoria. Desenvolvido com Python/Django + HTMX, hospedado na AWS via Docker.

**Core Value:** Dar ao comprador controle total do ciclo de compra — da requisição aprovada até a seleção do fornecedor — eliminando o fluxo manual por e-mail e planilha.

### Constraints

- **Tech Stack**: Python 3.12 + Django 5.x + HTMX + PostgreSQL + Docker — definido pelo cliente, não negociável
- **Escala**: Até 20 usuários simultâneos — não requer sharding, cache agressivo ou filas complexas no v1
- **Deploy**: AWS (configuração EC2 vs ECS a confirmar) — Docker é o contrato de entrega
- **Usuários**: Sistema interno corporativo — sem registro público, usuários criados pelo Admin
- **Relatórios**: ReportLab para PDF — biblioteca definida pelo cliente

<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->

## Technology Stack

## Core Framework

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| Python | 3.12 | Runtime | Client-mandated. 3.12 is stable, well-supported through 2028. Do not use 3.13 yet — ecosystem compatibility still catching up. |
| Django | 5.2 LTS | Web framework | Django 5.2 is the current LTS release (April 2025, supported until April 2028). Supports Python 3.10–3.14. Includes composite PKs, async auth methods, new form widgets. Use this, not 5.1 or 5.0 which are non-LTS. |
| HTMX | 2.0.x | Frontend interactivity | HTMX 2.0 is current stable. Confirmed via Context7 library resolution showing `v1.9.12` and `v2.0.4` as tracked versions. Use 2.0.x — it removes the IE11 compatibility overhead and has cleaner event model than 1.x. Serve via CDN or vendored in `static/`. |
| django-htmx | latest (1.x) | HTMX/Django integration | Adam Johnson's `django-htmx` resolves at `/adamchainz/django-htmx` in Context7 (109 snippets, High reputation). Provides `HtmxMiddleware` that adds `request.htmx` attribute, `HtmxResponseMixin`, and response trigger helpers. Essential — do not implement this manually. |
| PostgreSQL | 15 or 16 | Primary database | 15 is the safe choice on AWS RDS as of 2025. 16 is available but newer. Use `pg_trgm` extension for supplier name fuzzy search. `django.contrib.postgres` provides ORM-level access to all PostgreSQL-specific features. |

## Django App Structure

## Authentication

- Users are created by Admin — no registration form needed
- Login is email + password — no social providers
- No 2FA required (explicitly out of scope)
- No SSO (out of scope)

# apps/accounts/models.py

# config/settings/base.py

## Approval Workflow

# apps/aprovacoes/services.py

## Email Notifications

# In services.py

# settings/prod.py

## PDF Generation

# apps/relatorios/pdf.py

- `SimpleDocTemplate` — document container
- `Table` + `TableStyle` — price comparison tables, RFQ summaries
- `Paragraph` + `getSampleStyleSheet` — headers, body text
- `KeepTogether` — keep summary rows from splitting across pages

## HTMX Patterns for This Project

### Pattern 1: Form submission with inline error feedback

# View

### Pattern 2: Status badge updates (real-time feel without WebSockets)

### Pattern 3: Modal dialogs for approval actions

# Returns a partial template containing the modal HTML + confirmation form

### Pattern 4: Live search for supplier lookup

### CSRF with HTMX

### `hx-boost` usage

## Database: PostgreSQL Extensions and Patterns

### Recommended extensions

| Extension | Purpose | How to Enable |
|-----------|---------|---------------|
| `pg_trgm` | Fuzzy search for supplier names, product descriptions | `TrigramExtension()` in migration |
| `uuid-ossp` | UUID primary keys if needed | Built into PostgreSQL 15+ |
| `unaccent` | Search without accent sensitivity (critical for Brazilian Portuguese) | `UnaccentExtension()` in migration |

# In an early migration (e.g., accounts/0001_initial.py)

### Key ORM patterns

### Indexing strategy for procurement queries

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

## Docker Setup

### Development

# docker-compose.yml

### Production Dockerfile

# System deps

# Python deps

# Application

# Collect static files at build time

# Non-root user

### Production docker-compose (EC2)

# docker-compose.prod.yml

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

## Installation: `requirements.txt`

# Core

# HTMX integration

# Email

# PDF

# Static files (production)

# WSGI server

# Config

# Dev only (move to requirements-dev.txt)

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

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

### Encerramento de fase (obrigatório)

Ao concluir cada fase (após code review e testes verdes), executar obrigatoriamente:

1. **Atualizar README.md** — marcar a fase concluída como ✅ e atualizar qualquer informação relevante de funcionalidades ou setup.
2. **Push para o GitHub** — `git push origin master`. O repositório é `https://github.com/nuanderson/compras_nexos`.

Nenhuma fase é considerada finalizada sem esses dois passos.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
