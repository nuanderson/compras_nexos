# Architecture Patterns

**Domain:** Procurement management system (gestão de compras)
**Project:** ComprasNexos
**Stack:** Django 5.x + HTMX + PostgreSQL
**Scale:** ~20 internal users
**Researched:** 2026-06-10

---

## Recommended Architecture

### Overview

A classic Django monolith structured by domain app, with server-rendered HTML enhanced by HTMX partials. No SPA, no API layer (v1), no async workers. The entire lifecycle — requisição → aprovação → RFQ → cotação → seleção — lives in a single Django project with clean app boundaries.

```
compras_nexos/          # Django project root
├── config/             # settings, urls, wsgi
├── apps/
│   ├── accounts/       # Auth, User model extension, roles
│   ├── core/           # Abstract base models, shared utilities
│   ├── requisicoes/    # Purchase requisitions + state machine
│   ├── aprovacoes/     # Approval chain, rules, history
│   ├── fornecedores/   # Suppliers, categories, ratings
│   ├── cotacoes/       # RFQ, quotation entries, winner selection
│   └── relatorios/     # Dashboard, reports, PDF export
└── templates/
    ├── base.html
    ├── partials/       # HTMX-rendered fragments
    └── [app]/          # Per-app templates
```

---

## App Boundaries

### `accounts` — Authentication and Roles

**Owns:** Custom User model, Group-based roles, login/logout views, user management (Admin only).

**What belongs here:**
- `CustomUser` extending `AbstractUser` (email as username field, optional department field)
- Data migration that creates the 5 named Groups: Solicitante, Gestor, Comprador, Diretor, Admin
- `UserAdmin` registration in Django admin for Admin-only user management
- Login/logout views (can use Django's built-in `django.contrib.auth.views`)

**What does NOT belong here:** Business logic about what roles can do — that lives in the app that owns the action (e.g., approval permission check lives in `aprovacoes`).

**Seam:** Other apps import `settings.AUTH_USER_MODEL`, never `accounts.CustomUser` directly.

---

### `core` — Shared Abstractions

**Owns:** Abstract base models, common mixins, shared template tags.

**What belongs here:**
```python
class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class AuditedModel(TimestampedModel):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="%(app_label)s_%(class)s_created",
    )

    class Meta:
        abstract = True
```

**What does NOT belong here:** Any concrete model, any business logic, any view. Core is a utility layer only.

---

### `requisicoes` — Purchase Requisitions

**Owns:** The `Requisicao` model, its state machine, forms for creation/editing, views for Solicitante and Comprador, status dashboard for Solicitantes.

**What belongs here:**
- `Requisicao` model with `TextChoices` status field (state machine)
- Category model (or import from `fornecedores` — see coupling decision below)
- Forms: `RequisicaoForm` for Solicitante creation
- Views: create, detail, list (Solicitante sees own; Gestor/Diretor sees pending)
- Business rule: only Solicitante can create; only owner can edit if still RASCUNHO

**Seam with `aprovacoes`:** `Requisicao` exports its status. `aprovacoes` reads and writes that status via explicit service calls, not direct ORM access from within `aprovacoes`. The state transition methods live on the `Requisicao` model itself.

**Seam with `cotacoes`:** `cotacoes` has a `ForeignKey` to `Requisicao`. `requisicoes` does not import from `cotacoes`.

---

### `aprovacoes` — Approval Chain

**Owns:** `RegraDeAlcada` (configurable threshold rules), `AprovacaoRegistro` (approval/rejection history), approval views, and the routing logic that determines which approver receives a requisition.

**What belongs here:**
- `RegraDeAlcada` model: value thresholds → required approver role
- `AprovacaoRegistro` model: who approved/rejected, when, with notes
- `AprovacaoConfig` singleton model: Admin-configurable settings (registered in Django admin)
- Service function: `rotear_requisicao(requisicao)` — determines next approver group based on current rules and value
- Views: Gestor approval queue, Diretor approval queue, approve/reject actions

**What does NOT belong here:** The `Requisicao` model itself. `aprovacoes` reads `Requisicao` and calls state transition methods on it.

**Seam with `requisicoes`:** `aprovacoes` imports `Requisicao` from `requisicoes`. Dependency direction: `aprovacoes` → `requisicoes`. Never reversed.

---

### `fornecedores` — Suppliers and Categories

**Owns:** `Fornecedor`, `Categoria`, `AvaliacaoFornecedor` models, supplier CRUD (Comprador only), category management.

**What belongs here:**
- `Categoria` model (used by both `requisicoes` and `fornecedores` — see below)
- `Fornecedor` model with M2M to `Categoria`
- `AvaliacaoFornecedor` model (linked to a cotação outcome)
- CNPJ validation (either python-stdnum or a simple regex validator)
- Views: supplier list, detail, create/edit, ratings history

**Coupling decision — Categoria:** `Categoria` lives in `fornecedores` because suppliers are categorized by what they sell. `Requisicao` has a ForeignKey to `fornecedores.Categoria`. This is a one-way dependency: `requisicoes` → `fornecedores`. Acceptable and explicit. Alternative (separate `categorias` app) is over-engineering for this scale.

---

### `cotacoes` — RFQ and Quotations

**Owns:** `RFQ` (Request for Quotation), `EntradaCotacao` (individual supplier quote), winner selection logic, price comparison view.

**What belongs here:**
- `RFQ` model: linked to approved `Requisicao`, opened by Comprador
- `EntradaCotacao` model: one row per supplier per RFQ (price, lead time, notes)
- `VencedorSelecionado` model or `winner` FK on `RFQ` with justification
- Views: create RFQ from requisition, add/edit quotation entries, price comparison table, select winner
- Business rule: only Comprador can manage; RFQ only creatable from APROVADA requisitions

**Seam with `fornecedores`:** `EntradaCotacao` has a ForeignKey to `Fornecedor`. One-way dependency: `cotacoes` → `fornecedores`.

**Seam with `aprovacoes`:** None direct. `cotacoes` checks `requisicao.status == APROVADA`.

---

### `relatorios` — Reports and Dashboard

**Owns:** Dashboard KPI views, spending-by-category report, requisition status panel, quotation comparison report, PDF export.

**What belongs here:**
- Views that aggregate data across multiple apps via ORM queries
- PDF generation with ReportLab
- No models — this app is read-only, query-only

**Note:** `relatorios` is the only app that intentionally imports from all other apps. That is its purpose. All other apps must not import from `relatorios`.

---

## Dependency Direction (enforced)

```
accounts   ← (imported by all apps for AUTH_USER_MODEL)
core       ← (imported by all apps for abstract models)
fornecedores ← requisicoes, cotacoes
requisicoes  ← aprovacoes, cotacoes, relatorios
aprovacoes   ← cotacoes (only to read RFQ completion), relatorios
cotacoes     ← relatorios
relatorios   (imports all — intentional)
```

No circular imports. If you find yourself needing `from requisicoes.models import X` inside `aprovacoes/models.py` at module level, you have a circular import risk — use `apps.get_model()` or restructure.

---

## Model Design Patterns

### Requisicao State Machine

Use `TextChoices` for the status field. State transition methods live directly on the model. Never transition state outside these methods.

```python
class Requisicao(AuditedModel):

    class Status(models.TextChoices):
        RASCUNHO   = "RASCUNHO",   "Rascunho"
        PENDENTE   = "PENDENTE",   "Aguardando aprovação"
        EM_APROVACAO = "EM_APROVACAO", "Em aprovação (2º nível)"
        APROVADA   = "APROVADA",   "Aprovada"
        REPROVADA  = "REPROVADA",  "Reprovada"
        CANCELADA  = "CANCELADA",  "Cancelada"

    status = models.CharField(
        max_length=20,
        choices=Status,
        default=Status.RASCUNHO,
        db_index=True,
    )
    descricao      = models.TextField()
    categoria      = models.ForeignKey("fornecedores.Categoria", on_delete=models.PROTECT)
    valor_estimado = models.DecimalField(max_digits=12, decimal_places=2)
    justificativa  = models.TextField()
    solicitante    = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requisicoes",
    )

    # State transition methods — all transition logic here, nowhere else
    def submeter(self):
        if self.status != self.Status.RASCUNHO:
            raise ValueError("Apenas rascunhos podem ser submetidos.")
        self.status = self.Status.PENDENTE
        self.save(update_fields=["status", "updated_at"])

    def aprovar_nivel1(self, aprovador):
        if self.status != self.Status.PENDENTE:
            raise ValueError("Requisição não está aguardando aprovação de 1º nível.")
        # Routing logic determines if goes to APROVADA or EM_APROVACAO
        # (done by aprovacoes service, not here)
        ...

    def reprovar(self, reprovador, motivo):
        if self.status not in (self.Status.PENDENTE, self.Status.EM_APROVACAO):
            raise ValueError("Não é possível reprovar neste status.")
        self.status = self.Status.REPROVADA
        self.save(update_fields=["status", "updated_at"])
```

**Valid transitions:**

```
RASCUNHO → PENDENTE        (Solicitante submits)
PENDENTE → EM_APROVACAO    (Gestor approves, value > threshold requiring Diretor)
PENDENTE → APROVADA        (Gestor approves, value within Gestor threshold)
PENDENTE → REPROVADA       (Gestor rejects)
EM_APROVACAO → APROVADA    (Diretor approves)
EM_APROVACAO → REPROVADA   (Diretor rejects)
RASCUNHO → CANCELADA       (Solicitante cancels own draft)
PENDENTE → CANCELADA       (Solicitante cancels before decision)
```

---

### Approval Chain Data Model

```python
# In aprovacoes/models.py

class RegraDeAlcada(models.Model):
    """Admin-configurable threshold rules. Evaluated in order by valor_maximo."""
    valor_minimo   = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    valor_maximo   = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                         help_text="Deixe em branco para sem limite.")
    requer_gestor  = models.BooleanField(default=True)
    requer_diretor = models.BooleanField(default=False)
    descricao      = models.CharField(max_length=200, blank=True,
                                      help_text="Ex: Compras acima de R$10.000 exigem Diretor")

    class Meta:
        ordering = ["valor_minimo"]
        verbose_name = "Regra de Alçada"
        verbose_name_plural = "Regras de Alçadas"


class AprovacaoRegistro(TimestampedModel):
    """Immutable audit log of each approval/rejection action."""

    class Decisao(models.TextChoices):
        APROVADO  = "APROVADO",  "Aprovado"
        REPROVADO = "REPROVADO", "Reprovado"

    requisicao = models.ForeignKey(
        "requisicoes.Requisicao",
        on_delete=models.CASCADE,
        related_name="aprovacoes",
    )
    aprovador  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="aprovacoes_realizadas",
    )
    decisao    = models.CharField(max_length=10, choices=Decisao)
    nivel      = models.PositiveSmallIntegerField(help_text="1 = Gestor, 2 = Diretor")
    motivo     = models.TextField(blank=True)
    # Never delete AprovacaoRegistro — it is audit evidence
```

**Routing service (aprovacoes/services.py):**

```python
def determinar_nivel_aprovacao(requisicao):
    """
    Reads RegraDeAlcada table (set by Admin) and returns
    (requer_gestor, requer_diretor) for the given requisicao.valor_estimado.
    """
    regra = RegraDeAlcada.objects.filter(
        valor_minimo__lte=requisicao.valor_estimado
    ).filter(
        models.Q(valor_maximo__isnull=True) |
        models.Q(valor_maximo__gte=requisicao.valor_estimado)
    ).first()

    if regra is None:
        return (True, False)  # Default: Gestor only

    return (regra.requer_gestor, regra.requer_diretor)
```

---

### Supplier Data Model

```python
# In fornecedores/models.py

class Categoria(models.Model):
    nome      = models.CharField(max_length=100, unique=True)
    descricao = models.TextField(blank=True)

    def __str__(self):
        return self.nome


class Fornecedor(AuditedModel):
    razao_social   = models.CharField(max_length=200)
    cnpj           = models.CharField(max_length=18, unique=True)  # "XX.XXX.XXX/XXXX-XX"
    email_contato  = models.EmailField()
    telefone       = models.CharField(max_length=20, blank=True)
    categorias     = models.ManyToManyField(Categoria, blank=True, related_name="fornecedores")
    ativo          = models.BooleanField(default=True)

    def __str__(self):
        return self.razao_social


class AvaliacaoFornecedor(TimestampedModel):
    fornecedor  = models.ForeignKey(Fornecedor, on_delete=models.CASCADE, related_name="avaliacoes")
    avaliador   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    nota        = models.PositiveSmallIntegerField(
        help_text="1 a 5",
        choices=[(i, str(i)) for i in range(1, 6)]
    )
    comentario  = models.TextField(blank=True)
    cotacao_ref = models.ForeignKey(
        "cotacoes.RFQ", on_delete=models.SET_NULL, null=True, blank=True
    )  # Optional reference to the purchase that prompted the rating
```

**Note on CNPJ:** The Supplier-Category relationship uses a plain `ManyToManyField` (no extra data on the relationship), so no `through` model is needed. If per-category contract data is needed in v2, add a `through` model then.

---

### RFQ / Quotation Data Model

```python
# In cotacoes/models.py

class RFQ(AuditedModel):

    class Status(models.TextChoices):
        ABERTA    = "ABERTA",    "Aberta"
        ENCERRADA = "ENCERRADA", "Encerrada"
        CANCELADA = "CANCELADA", "Cancelada"

    requisicao    = models.OneToOneField(
        "requisicoes.Requisicao",
        on_delete=models.PROTECT,
        related_name="rfq",
    )
    comprador     = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="rfqs_gerenciadas",
    )
    status        = models.CharField(max_length=10, choices=Status, default=Status.ABERTA)
    observacoes   = models.TextField(blank=True)
    vencedor      = models.ForeignKey(
        "fornecedores.Fornecedor",
        null=True, blank=True,
        on_delete=models.PROTECT,
        related_name="rfqs_vencidas",
    )
    justificativa_selecao = models.TextField(blank=True)

    # OneToOneField enforces: one RFQ per approved requisition


class EntradaCotacao(TimestampedModel):
    rfq           = models.ForeignKey(RFQ, on_delete=models.CASCADE, related_name="entradas")
    fornecedor    = models.ForeignKey(
        "fornecedores.Fornecedor",
        on_delete=models.PROTECT,
        related_name="cotacoes",
    )
    preco_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    prazo_entrega  = models.PositiveIntegerField(help_text="Dias úteis", null=True, blank=True)
    condicoes      = models.TextField(blank=True)

    class Meta:
        unique_together = [("rfq", "fornecedor")]  # One entry per supplier per RFQ
```

---

## Data Flow: End-to-End

```
1. Solicitante creates Requisicao (status=RASCUNHO)
   └─ View calls requisicao.submeter() → status=PENDENTE
   └─ transaction.on_commit() triggers email to Gestores

2. Gestor opens approval queue → sees PENDENTE requisitions
   └─ Gestor approves → aprovacoes service:
       a. determinar_nivel_aprovacao(requisicao)
       b. If requer_diretor=True: status=EM_APROVACAO, email to Diretores
       c. If requer_diretor=False: status=APROVADA, email to Comprador
       d. AprovacaoRegistro created (nivel=1, decisao=APROVADO)
   └─ Gestor rejects → status=REPROVADA, AprovacaoRegistro created

3. Diretor opens EM_APROVACAO queue (only if threshold requires it)
   └─ Same pattern: AprovacaoRegistro (nivel=2)
   └─ APROVADA or REPROVADA

4. Comprador sees APROVADA requisitions without RFQ
   └─ Creates RFQ (OneToOneField enforces uniqueness)
   └─ Adds EntradaCotacao entries (one per contacted supplier)

5. Comprador views price comparison table
   └─ EntradaCotacao.objects.filter(rfq=rfq).order_by("preco_unitario")
   └─ Selects winner → rfq.vencedor = fornecedor, justificativa saved
   └─ rfq.status = ENCERRADA
   └─ AvaliacaoFornecedor can be created at this point

6. relatorios reads across all models for dashboard KPIs and reports
```

**Direction is strictly one-way.** No step refers back to a previous step's app model except through legitimate ForeignKey reads.

---

## Permission System

### Approach: Django Groups as Roles

Use Django's built-in `Group` model as the role system. Do not build a custom permission model. The 5 Groups are created in a data migration in `accounts`.

**Why Groups not custom:** For 20 users with stable roles, Django Groups + custom permissions cover all cases without extra complexity. A custom role model (separate `Papel` table) adds no value at this scale.

### Group Setup (data migration)

```python
GRUPOS = ["Solicitante", "Gestor", "Comprador", "Diretor", "Admin"]

# Create custom permissions per model as needed
# Assign permissions to groups in migration
# One user can belong to multiple groups (e.g., Admin is also in all groups)
```

### Custom Permissions on Models

```python
class Requisicao(AuditedModel):
    class Meta:
        permissions = [
            ("pode_aprovar_nivel1", "Pode aprovar requisições (1º nível)"),
            ("pode_aprovar_nivel2", "Pode aprovar requisições (2º nível)"),
            ("pode_ver_todas", "Pode ver todas as requisições"),
        ]
```

### View Protection Pattern

Use `PermissionRequiredMixin` for CBVs and `@permission_required` for function-based views:

```python
class AprovarRequisicaoView(PermissionRequiredMixin, UpdateView):
    permission_required = "requisicoes.pode_aprovar_nivel1"
    raise_exception = True  # Return 403, not redirect to login
```

For role-check shortcuts, a utility function avoids repeated `user.groups.filter(name=...)` calls:

```python
# accounts/utils.py
def is_gestor(user):
    return user.groups.filter(name="Gestor").exists()

def is_comprador(user):
    return user.groups.filter(name="Comprador").exists()
```

**Permission caching note (HIGH confidence):** Django caches permissions per request. After assigning a user to a group, refresh the user object from the DB before checking permissions in the same request.

### Role → Permission Matrix

| Action | Solicitante | Gestor | Comprador | Diretor | Admin |
|--------|-------------|--------|-----------|---------|-------|
| Criar requisição | yes | - | - | - | yes |
| Ver próprias requisições | yes | yes | yes | yes | yes |
| Ver todas requisições | - | yes | yes | yes | yes |
| Aprovar 1º nível | - | yes | - | - | yes |
| Aprovar 2º nível | - | - | - | yes | yes |
| Gerenciar fornecedores | - | - | yes | - | yes |
| Criar/gerenciar RFQ | - | - | yes | - | yes |
| Ver relatórios | - | yes | yes | yes | yes |
| Configurar alçadas | - | - | - | - | yes |
| Gerenciar usuários | - | - | - | - | yes |

---

## Approval Threshold Configuration

### Admin-Configurable via Django Admin (no code deploy needed)

`RegraDeAlcada` is registered in Django admin with `AdminSite` restricted to Admin group users. The Comprador/Gestor/Diretor never see this section.

Example rules the Admin might create:

| Valor mínimo | Valor máximo | Requer Gestor | Requer Diretor |
|---|---|---|---|
| R$0 | R$5.000 | Sim | Não |
| R$5.001 | R$50.000 | Sim | Não |
| R$50.001 | (sem limite) | Sim | Sim |

The routing service reads these at approval time — no caching needed at 20-user scale. If the Admin changes a rule, the next approval routes correctly without restart.

**Singleton consideration:** `RegraDeAlcada` is a list (many rows), not a single settings record. Use `ordering = ["valor_minimo"]` and the service queries the correct row for each requisition value.

---

## HTMX Integration Patterns

### Install and Configure

```python
# settings.py
INSTALLED_APPS = [..., "django_htmx"]
MIDDLEWARE = [..., "django_htmx.middleware.HtmxMiddleware"]
```

The middleware attaches `request.htmx` (falsy for non-HTMX requests).

### Pattern 1: Swap Base Template (Preferred for ComprasNexos)

Single view, single template, conditional base:

```python
# views.py
def aprovacao_fila_view(request):
    if request.htmx:
        base_template = "partials/_base.html"  # No <html>, just the fragment
    else:
        base_template = "_base.html"           # Full page with nav, header

    requisicoes = Requisicao.objects.filter(status="PENDENTE")
    return render(request, "aprovacoes/fila.html", {
        "base_template": base_template,
        "requisicoes": requisicoes,
    })
```

```html
<!-- aprovacoes/fila.html -->
{% extends base_template %}
{% block content %}
  ... list content ...
{% endblock %}
```

### Pattern 2: django-template-partials (for inline partial updates)

For updating a table row or a status badge without a full section refresh:

```python
# In views.py — returns only the status badge partial for HTMX
def atualizar_status_badge(request, pk):
    requisicao = get_object_or_404(Requisicao, pk=pk)
    template = "requisicoes/requisicao_detail.html"
    if request.htmx:
        template += "#status-badge"  # django-template-partials named section
    return render(request, template, {"requisicao": requisicao})
```

### Where to Use HTMX vs Full Page

| Interaction | Approach | Reason |
|-------------|----------|--------|
| Navigation between sections | Full page (hx-boost OR links) | Browser history, URL bar update |
| Approve/reject action → update status | HTMX partial (hx-post, hx-target) | No page reload, instant feedback |
| Add cotação entry to RFQ table | HTMX partial | Row appended inline, no full reload |
| Search/filter requisition list | HTMX GET → full list partial | Filter updates table, URL not required |
| Select winner | HTMX post → confirmation + status | In-page confirmation without new page |
| Dashboard KPI numbers (live) | Full page load only | Not real-time enough to need polling |
| Form validation feedback | HTMX (hx-post on blur or submit) | Inline error display |
| PDF download | Full page link | Browser handles file download |

### CSRF with HTMX

HTMX 1.x requires CSRF token in every POST. Include in base template:

```html
<script>
  document.body.addEventListener('htmx:configRequest', function(evt) {
    evt.detail.headers['X-CSRFToken'] = '{{ csrf_token }}';
  });
</script>
```

---

## Notification Architecture

### Recommendation: `transaction.on_commit()` + Django's `send_mail`, No Celery

At 20 users with infrequent email triggers (requisition submitted, approved, rejected), Celery adds operational complexity that is not justified. The risk of a blocking SMTP call is minimal.

**Pattern: on_commit hook (HIGH confidence)**

Send email after the DB transaction commits. If the transaction rolls back, no email is sent (avoids ghost notifications).

```python
# In the approval service
from django.db import transaction
from django.core.mail import send_mail

def aprovar_requisicao(requisicao, aprovador, motivo=""):
    with transaction.atomic():
        # State transition
        requisicao.status = Requisicao.Status.APROVADA
        requisicao.save(update_fields=["status", "updated_at"])

        # Audit record
        AprovacaoRegistro.objects.create(
            requisicao=requisicao,
            aprovador=aprovador,
            decisao=AprovacaoRegistro.Decisao.APROVADO,
            nivel=1,
        )

        # Email fires only after successful commit
        transaction.on_commit(
            lambda: _notificar_aprovacao(requisicao)
        )


def _notificar_aprovacao(requisicao):
    compradores = User.objects.filter(groups__name="Comprador")
    send_mail(
        subject=f"Requisição #{requisicao.pk} aprovada",
        message=f"A requisição '{requisicao.descricao}' foi aprovada e está pronta para cotação.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[u.email for u in compradores if u.email],
        fail_silently=True,  # Don't crash the request if email fails
    )
```

**When to reconsider Celery:** If email failures become noticeable, if the business requests retry logic, or if new notification types (WhatsApp, SMS) are added. Add `django-rq` (Redis-backed, simpler than Celery) at that point.

**Email backend for development:**
```python
# settings/development.py
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
```

---

## Build Order

Dependencies drive the order. Build what other things depend on first.

### Phase 1 — Foundation (everything else depends on this)
1. **Project scaffold:** `config/`, `apps/` directory structure, Docker setup, PostgreSQL connection
2. **`core` app:** `TimestampedModel`, `AuditedModel` abstract bases
3. **`accounts` app:** Custom User model, Group creation migration, login/logout views, Admin user management
4. **Base templates:** `base.html`, nav skeleton, HTMX configured, CSRF script

**Why first:** Custom User model must be in place before first migration. All other models depend on `AUTH_USER_MODEL`. Groups must exist before business logic is tested.

### Phase 2 — Requisição Core (the primary workflow starts here)
5. **`fornecedores` app — Categoria only:** Create `Categoria` model first (referenced by `Requisicao`)
6. **`requisicoes` app:** `Requisicao` model, state machine methods, Solicitante views (create, list, detail)
7. **Basic permission guards:** `PermissionRequiredMixin` on all views, 403 handling

**Why second:** Everything downstream (approval, RFQ) depends on `Requisicao` existing with correct status choices.

### Phase 3 — Approval Chain
8. **`aprovacoes` app:** `RegraDeAlcada`, `AprovacaoRegistro`, routing service, Gestor queue, Diretor queue
9. **Admin registration of `RegraDeAlcada`:** So thresholds can be set before going live
10. **Email notifications:** `on_commit()` hooks for new requisition → Gestor, approved → Comprador

**Why third:** Requires `Requisicao` status machine to be complete and testable end-to-end.

### Phase 4 — Suppliers and Quotations
11. **`fornecedores` app — full:** `Fornecedor`, `AvaliacaoFornecedor`, Comprador CRUD views, category M2M
12. **`cotacoes` app:** `RFQ`, `EntradaCotacao`, winner selection, price comparison view

**Why fourth:** Quotation requires approved requisitions (Phase 3) and suppliers (Phase 4 start).

### Phase 5 — Reports and PDF
13. **`relatorios` app:** Dashboard KPIs, spending report, requisition status panel, PDF export with ReportLab

**Why last:** Reports are read-only aggregations over all prior data. No other app depends on `relatorios`.

---

## Scalability Considerations (at 20 users)

| Concern | At 20 users | At 200 users | At 2,000 users |
|---------|-------------|--------------|----------------|
| DB queries per page | Raw ORM, `select_related` as needed | Add `prefetch_related`, indexes | Query caching (Redis), read replicas |
| Email sending | `on_commit()` + `send_mail` synchronous | Remains fine | Add `django-rq` or Celery |
| Session storage | Default DB sessions | Switch to cached DB sessions | Redis sessions |
| File uploads (attachments) | S3 via `django-storages` from day 1 | Same | Same |
| Background reports | Run synchronously | Add Celery for PDF generation | Same |
| Caching | None required | Per-view `cache_page` for reports | Full caching strategy |

**Recommendation for v1:** Add `select_related` and `prefetch_related` to list views from the start (zero cost, prevents N+1). Everything else is premature optimization for 20 users.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Fat Views
**What goes wrong:** Approval routing logic, email dispatch, and state transitions all written inside the view function.
**Why bad:** Untestable, duplicated across views, impossible to call from management commands or admin actions.
**Instead:** Service functions in `aprovacoes/services.py`. Views call services, not ORM directly for business operations.

### Anti-Pattern 2: State Transitions Outside the Model
**What goes wrong:** `requisicao.status = "APROVADA"; requisicao.save()` written in views or services.
**Why bad:** Skips validation, bypasses transition guards, creates inconsistent state.
**Instead:** All state transitions go through model methods (`requisicao.aprovar_nivel1()`). Methods enforce preconditions.

### Anti-Pattern 3: Using Signals for Business Logic
**What goes wrong:** Approval notification sent via `post_save` signal on `Requisicao`.
**Why bad:** Implicit, fires on every save including admin edits, hard to debug, hard to test.
**Instead:** Explicit call in service function, wrapped in `transaction.on_commit()`.

### Anti-Pattern 4: Approval Logic in Template Layer
**What goes wrong:** Approval buttons shown/hidden with `{% if user.groups.filter(name="Gestor").exists %}` in templates.
**Why bad:** Security theater — template checks don't protect the POST endpoint.
**Instead:** Template checks + `PermissionRequiredMixin` on the view. Both, not either.

### Anti-Pattern 5: Circular App Imports
**What goes wrong:** `aprovacoes/models.py` imports `from requisicoes.models import Requisicao` at module level, and `requisicoes/models.py` imports something from `aprovacoes`.
**Why bad:** `ImportError` at startup, or subtle bugs if resolved with `apps.get_model()`.
**Instead:** Enforce one-way dependency direction (see Dependency Direction section above).

---

## Sources

- Django 5.2 official documentation: permissions/groups — https://docs.djangoproject.com/en/5.2/topics/auth/default/
- Django 5.2 official documentation: transactions / on_commit — https://docs.djangoproject.com/en/5.2/topics/db/transactions/
- Django 5.2 official documentation: signals (with warning against overuse) — https://docs.djangoproject.com/en/5.2/topics/signals/
- Django 5.2 official documentation: email sending — https://docs.djangoproject.com/en/5.2/topics/email/
- Django 5.2 official documentation: model relationships (ForeignKey, M2M, through) — https://docs.djangoproject.com/en/5.2/ref/models/fields/
- django-htmx docs (Context7 /adamchainz/django-htmx): HtmxMiddleware, HtmxDetails, partial rendering patterns — HIGH confidence
- Django admin customization for non-technical users — https://docs.djangoproject.com/en/5.2/ref/contrib/admin/
