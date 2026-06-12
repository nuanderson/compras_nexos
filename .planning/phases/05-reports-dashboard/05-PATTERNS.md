# Phase 5: Reports & Dashboard - Pattern Map

**Mapped:** 2026-06-11
**Files analyzed:** 11
**Analogs found:** 10 / 11

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `apps/relatorios/services.py` | service | CRUD / transform | `apps/cotacoes/services.py` | exact |
| `apps/relatorios/views.py` | controller | request-response | `apps/fornecedores/views.py` | exact |
| `apps/relatorios/urls.py` | config | request-response | `apps/cotacoes/urls.py` | exact |
| `apps/relatorios/apps.py` | config | — | `apps/cotacoes/apps.py` (inferred) | role-match |
| `apps/relatorios/templates/relatorios/gastos.html` | component | request-response | `apps/fornecedores/templates/fornecedores/lista.html` | role-match |
| `apps/relatorios/templates/relatorios/requisicoes.html` | component | request-response | `apps/fornecedores/templates/fornecedores/lista.html` | role-match |
| `apps/relatorios/tests/conftest.py` | test | — | `apps/cotacoes/tests/conftest.py` | exact |
| `apps/relatorios/tests/test_services.py` | test | — | `apps/cotacoes/tests/test_services.py` | role-match |
| `apps/relatorios/tests/test_views.py` | test | — | `apps/cotacoes/tests/test_views.py` | exact |
| `apps/core/views.py` | controller | request-response | `apps/core/views.py` (self — enrich) | exact |
| `apps/core/templates/core/dashboard.html` | component | request-response | `apps/core/templates/core/dashboard.html` (self — enrich) | exact |
| `templates/base.html` | component | — | `templates/base.html` (self — patch nav link) | exact |
| `config/urls.py` | config | — | `config/urls.py` (self — add one path) | exact |
| `config/settings/base.py` | config | — | `config/settings/base.py` (self — add to INSTALLED_APPS) | exact |

---

## Pattern Assignments

### `apps/relatorios/services.py` (service, transform / CRUD)

**Analog:** `apps/cotacoes/services.py` and `apps/aprovacoes/services.py`

**Imports pattern** (`apps/cotacoes/services.py` lines 19-24):
```python
from decimal import Decimal
from typing import Any

from django.db import transaction

from .models import CotacaoFornecedor, RFQ
```

**Cross-app imports pattern for relatorios** (adapt from cotacoes pattern):
```python
# apps/relatorios/services.py
from datetime import date
from decimal import Decimal

from django.db.models import Count, F, Sum

from apps.cotacoes.models import CotacaoFornecedor, RFQ
from apps.fornecedores.models import Fornecedor
from apps.requisicoes.models import Requisicao
```

**Core service function signature pattern** (`apps/aprovacoes/services.py` lines 30-64):
```python
def submeter_requisicao(requisicao_pk: int, solicitante) -> Requisicao:
    """
    Transição RASCUNHO → PENDENTE_GESTOR.

    Levanta:
        ValueError       — se a requisição não está em RASCUNHO.
        PermissionError  — se `solicitante` não é o criador da requisição.
    """
```

Pattern: typed parameters, return type hint, docstring listing exceptions, no queries in views.

**Aggregate pattern** (`apps/cotacoes/services.py` lines 70-101):
```python
def calcular_comparativo(rfq: RFQ) -> list[dict[str, Any]]:
    cotacoes = list(
        rfq.cotacoes.select_related("fornecedor").order_by("preco_unitario")
    )
    if not cotacoes:
        return []

    menor = cotacoes[0].preco_unitario
    result = []
    for c in cotacoes:
        if menor and menor > 0:
            delta = (
                (c.preco_unitario - menor) / menor * Decimal("100")
            ).quantize(Decimal("0.1"))
        else:
            delta = Decimal("0")
        result.append({...})
    return result
```

Pattern for relatorios — `Sum()` with `None` fallback (mandatory):
```python
resultado = CotacaoFornecedor.objects.filter(...).aggregate(total=Sum("preco_unitario"))
gasto_mes = resultado["total"] or Decimal("0")
```

**Conditional filter pattern** (from RESEARCH.md §Code Examples, validated against cotacoes pattern):
```python
def get_requisicoes_painel(status=None, unidade_id=None):
    qs = Requisicao.objects.select_related("categoria", "unidade", "criado_por").order_by("-criado_em")
    if status:
        qs = qs.filter(status=status)
    if unidade_id:
        qs = qs.filter(unidade_id=unidade_id)
    return qs
```

---

### `apps/relatorios/views.py` (controller, request-response)

**Analog:** `apps/fornecedores/views.py`

**Imports pattern** (`apps/fornecedores/views.py` lines 13-22):
```python
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.postgres.search import TrigramSimilarity
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.requisicoes.models import CategoriaCompra

from .forms import FornecedorForm
from .models import Fornecedor
```

**Adapt for relatorios views:**
```python
from io import BytesIO
from datetime import date

from django.http import FileResponse
from django.shortcuts import render
from django.views import View
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Table, TableStyle

from apps.fornecedores.views import CompradorRequiredMixin
from . import services
```

**CompradorRequiredMixin reuse** (`apps/fornecedores/views.py` lines 25-41):
```python
class CompradorRequiredMixin(LoginRequiredMixin):
    """
    Restringe acesso a usuários com role='comprador', 'admin' ou is_superuser.
    Lança PermissionDenied (HTTP 403) para papéis não autorizados.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (
            request.user.is_superuser
            or request.user.role in ("comprador", "admin")
        ):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
```

Import this directly: `from apps.fornecedores.views import CompradorRequiredMixin` (same pattern used by `apps/cotacoes/views.py` line 29).

**GET view with context building** (`apps/fornecedores/views.py` lines 91-109):
```python
def get(self, request):
    q = request.GET.get("q", "").strip()
    categoria_pk = request.GET.get("categoria", "")
    mostrar_inativos = request.GET.get("mostrar_inativos", "") == "1"
    qs = get_queryset_fornecedores(
        q=q or None,
        categoria_pk=categoria_pk or None,
        apenas_ativos=not mostrar_inativos,
    )
    ctx = {
        "fornecedores": qs,
        "categorias": CategoriaCompra.objects.filter(ativo=True),
        "q": q,
        "categoria_pk": categoria_pk,
        "mostrar_inativos": mostrar_inativos,
    }
    ...
    return render(request, "fornecedores/lista.html", ctx)
```

Pattern for GastosView: read GET params → call service → build ctx dict → render template.

**PDF view pattern** (from RESEARCH.md §Pattern 3, consistent with CLAUDE.md):
```python
class GastosPDFView(CompradorRequiredMixin, View):
    def get(self, request):
        # Parse same GET params as GastosView
        data_inicio, data_fim, unidade_id = _parse_filtros(request)
        dados = services.get_gastos_por_categoria(data_inicio, data_fim, unidade_id)

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("Relatório de Gastos por Categoria", styles["Heading1"]))
        # ... build table ...
        t = Table(table_data)
        t.setStyle(TableStyle([...]))
        story.append(KeepTogether([t]))

        doc.build(story)
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename="gastos_por_categoria.pdf")
```

---

### `apps/relatorios/urls.py` (config, request-response)

**Analog:** `apps/cotacoes/urls.py`

**Full pattern** (`apps/cotacoes/urls.py` lines 1-49):
```python
from django.urls import path

from .views import (
    AdicionarCotacaoView,
    DetalheRFQView,
    ListaRFQView,
    ...
)

app_name = "cotacoes"

urlpatterns = [
    path("", ListaRFQView.as_view(), name="lista"),
    path("nova/", NovaRFQView.as_view(), name="nova"),
    path("<int:pk>/", DetalheRFQView.as_view(), name="detalhe"),
    ...
]
```

Adapt for relatorios — 4 routes: `gastos/`, `gastos/pdf/`, `requisicoes/`, `requisicoes/pdf/` with `app_name = "relatorios"`.

---

### `apps/relatorios/apps.py` (config)

**Analog:** inferred from project conventions (all apps follow same AppConfig structure)

```python
# apps/relatorios/apps.py
from django.apps import AppConfig

class RelatoriosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.relatorios"
    verbose_name = "Relatórios"
```

---

### `apps/relatorios/templates/relatorios/gastos.html` (component, request-response)

**Analog:** `apps/fornecedores/templates/fornecedores/lista.html` (filter form + table structure)

**Template extension pattern** (`apps/core/templates/core/dashboard.html` lines 1-3):
```html
{% extends "base.html" %}

{% block title %}Relatório de Gastos — ComprasNexos{% endblock %}
{% block page_title %}Gastos por Categoria{% endblock %}
```

**Filter form pattern with GET submit** (from RESEARCH.md §Code Examples):
```html
<form method="get" class="mb-lg">
  <div class="form-group" style="display: flex; gap: 16px; align-items: flex-end;">
    <div>
      <label class="form-label">De</label>
      <input type="date" name="data_inicio" value="{{ data_inicio }}" class="form-input">
    </div>
    <div>
      <label class="form-label">Até</label>
      <input type="date" name="data_fim" value="{{ data_fim }}" class="form-input">
    </div>
    {% if pode_filtrar_unidade %}
    <div>
      <label class="form-label">Unidade</label>
      <select name="unidade" class="form-select">
        <option value="">Todas</option>
        {% for u in unidades %}
          <option value="{{ u.pk }}" {% if u.pk|stringformat:"s" == unidade_selecionada %}selected{% endif %}>{{ u.nome }}</option>
        {% endfor %}
      </select>
    </div>
    {% endif %}
    <button type="submit" class="btn btn-primary">Filtrar</button>
    <a href="{% url 'relatorios:gastos-pdf' %}?{{ request.GET.urlencode }}" class="btn btn-secondary">Exportar PDF</a>
  </div>
</form>
```

**CSS classes in use** (confirmed in `static/css/main.css` per RESEARCH.md sources):
- `.card`, `.card-grid`, `.card-label`, `.card-value` — KPI cards
- `.table-container`, `.badge` — table and status badges
- `.form-group`, `.form-label`, `.form-input`, `.form-select` — form elements
- `.btn`, `.btn-primary`, `.btn-secondary` — buttons
- `.mb-lg`, `.mt-lg`, `.text-muted` — spacing and utility

---

### `apps/relatorios/templates/relatorios/requisicoes.html` (component, request-response)

**Analog:** same as gastos.html — filter form + table

Filter form uses `<select name="status">` with choices from `Requisicao.Status` and optional `<select name="unidade">`. Table rows render status with `.badge` class (pattern observed in cotacoes templates from codebase structure).

---

### `apps/relatorios/tests/conftest.py` (test)

**Analog:** `apps/cotacoes/tests/conftest.py` — exact copy structure with additions

**Full fixture pattern** (`apps/cotacoes/tests/conftest.py` lines 1-109):
```python
from decimal import Decimal
import pytest
from apps.accounts.models import UnidadeOrganizacional, User
from apps.fornecedores.models import Fornecedor
from apps.requisicoes.models import CategoriaCompra, Requisicao


@pytest.fixture
def test_unit(db):
    return UnidadeOrganizacional.objects.create(
        nome="Unidade Teste",
        descricao="Unidade para testes",
        ativo=True,
    )


@pytest.fixture
def comprador_user(db, test_unit):
    return User.objects.create_user(
        username="comprador",
        email="comprador@test.com",
        password="testpass123",
        role=User.Role.COMPRADOR,
        default_unit=test_unit,
    )


@pytest.fixture
def solicitante_user(db, test_unit):
    return User.objects.create_user(
        username="solicitante",
        email="solicitante@test.com",
        password="testpass123",
        role=User.Role.SOLICITANTE,
        default_unit=test_unit,
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username="admin",
        email="admin@test.com",
        password="testpass123",
        role=User.Role.ADMIN,
        is_superuser=True,
        is_staff=True,
    )


@pytest.fixture
def categoria(db):
    return CategoriaCompra.objects.create(nome="Informática", ativo=True)


@pytest.fixture
def fornecedor(db, categoria):
    return Fornecedor.objects.create(
        cnpj="11222333000181",
        razao_social="Empresa Teste Ltda",
        email="teste@empresa.com",
        categoria=categoria,
        ativo=True,
    )


@pytest.fixture
def requisicao_aprovada(db, test_unit, categoria, comprador_user):
    return Requisicao.objects.create(
        descricao="Compra de notebooks",
        status=Requisicao.Status.APROVADO,
        valor_estimado=Decimal("5000.00"),
        justificativa="teste",
        categoria=categoria,
        unidade=test_unit,
        criado_por=comprador_user,
    )
```

For `relatorios/tests/conftest.py`, add these additional fixtures:
```python
@pytest.fixture
def rfq_com_vencedor(db, requisicao_aprovada, comprador_user, fornecedor):
    """RFQ com vencedor definido — usado para testar KPI 'Gasto do Mês'."""
    from apps.cotacoes.models import CotacaoFornecedor, RFQ
    rfq = RFQ.objects.create(requisicao=requisicao_aprovada, criado_por=comprador_user)
    cotacao = CotacaoFornecedor.objects.create(
        rfq=rfq,
        fornecedor=fornecedor,
        preco_unitario=Decimal("1500.00"),
        prazo_entrega="15 dias",
        condicoes_pagamento="30 dias",
    )
    rfq.vencedor = cotacao
    rfq.justificativa_selecao = "Menor preço"
    rfq.save(update_fields=["vencedor", "justificativa_selecao", "atualizado_em"])
    return rfq


@pytest.fixture
def diretor_user(db, test_unit):
    return User.objects.create_user(
        username="diretor",
        email="diretor@test.com",
        password="testpass123",
        role=User.Role.DIRETOR,
        default_unit=test_unit,
    )
```

---

### `apps/relatorios/tests/test_views.py` (test)

**Analog:** `apps/cotacoes/tests/test_views.py`

**Test class structure** (`apps/cotacoes/tests/test_views.py` lines 18-60):
```python
class TestNovaRFQView:
    """
    Testes COT-01: criação de RFQ via /cotacoes/nova/.

    Cobre:
      T-04-01  403 para Solicitante
    """

    def test_acesso_negado_solicitante(self, client, solicitante_user):
        """Solicitante deve receber 403 ao tentar acessar /cotacoes/nova/."""
        client.force_login(solicitante_user)
        response = client.get("/cotacoes/nova/")
        assert response.status_code == 403
```

Pattern for relatorios view tests:
```python
class TestAcesso:
    def test_solicitante_negado_gastos(self, client, solicitante_user):
        client.force_login(solicitante_user)
        response = client.get("/relatorios/gastos/")
        assert response.status_code == 403

    def test_comprador_acessa_gastos(self, client, comprador_user):
        client.force_login(comprador_user)
        response = client.get("/relatorios/gastos/")
        assert response.status_code == 200


class TestPDF:
    def test_pdf_content_type(self, client, comprador_user):
        client.force_login(comprador_user)
        response = client.get("/relatorios/gastos/pdf/")
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"

    def test_pdf_attachment(self, client, comprador_user):
        client.force_login(comprador_user)
        response = client.get("/relatorios/gastos/pdf/")
        assert "attachment" in response["Content-Disposition"]
```

---

### `apps/core/views.py` — enrich DashboardView (controller)

**Analog:** Self — current content is the stub to be enriched

**Current stub** (`apps/core/views.py` lines 1-6):
```python
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "core/dashboard.html"
```

**Pattern to add** — `get_context_data()` following TemplateView convention (from RESEARCH.md §Pattern 4):
```python
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from apps.relatorios import services as relatorios_services


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "core/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["kpis"] = relatorios_services.get_dashboard_kpis(self.request.user)
        return ctx
```

---

### `apps/core/templates/core/dashboard.html` — populate KPI cards (component)

**Analog:** Self — current stub with `&mdash;` values

**Current stub** (`apps/core/templates/core/dashboard.html` lines 7-24):
```html
<div class="card-grid">
  <div class="card">
    <div class="card-label">Requisições Abertas</div>
    <div class="card-value">&mdash;</div>
  </div>
  <div class="card">
    <div class="card-label">Cotações em Andamento</div>
    <div class="card-value">&mdash;</div>
  </div>
  <div class="card">
    <div class="card-label">Gasto do Mês</div>
    <div class="card-value">&mdash;</div>
  </div>
  <div class="card">
    <div class="card-label">Fornecedores Ativos</div>
    <div class="card-value">&mdash;</div>
  </div>
</div>
<p class="text-muted mt-lg">Dashboard em construção — dados disponíveis após as fases 2-5.</p>
```

Replace `&mdash;` with context variables and remove the stub `<p>`:
```html
<div class="card-grid">
  <div class="card">
    <div class="card-label">Requisições Abertas</div>
    <div class="card-value">{{ kpis.requisicoes_abertas }}</div>
  </div>
  <div class="card">
    <div class="card-label">Cotações em Andamento</div>
    <div class="card-value">{{ kpis.cotacoes_em_andamento }}</div>
  </div>
  <div class="card">
    <div class="card-label">Gasto do Mês</div>
    <div class="card-value">R$ {{ kpis.gasto_mes|floatformat:2 }}</div>
  </div>
  <div class="card">
    <div class="card-label">Fornecedores Ativos</div>
    <div class="card-value">{{ kpis.fornecedores_ativos }}</div>
  </div>
</div>
```

---

### `templates/base.html` — update Relatórios nav link (component)

**Analog:** Self — patch one line

**Current** (`templates/base.html` lines 77-80):
```html
{% if request.user.role == 'comprador' or request.user.role == 'diretor' or request.user.role == 'admin' %}
<a href="#"
   class="nav-item">
  Relatórios
</a>
```

**Replace with** (following nav-item pattern from lines 27-30):
```html
{% if request.user.role == 'comprador' or request.user.role == 'diretor' or request.user.role == 'admin' or request.user.is_superuser %}
<a href="{% url 'relatorios:gastos' %}"
   class="nav-item {% if 'relatorios' in request.path %}is-active{% endif %}">
  Relatórios
</a>
```

---

### `config/urls.py` — add relatorios urls (config)

**Analog:** Self — current file, add one path

**Current pattern** (`config/urls.py` lines 8-16):
```python
urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("requisicoes/", include("apps.requisicoes.urls")),
    path("aprovacoes/", include("apps.aprovacoes.urls")),
    path("fornecedores/", include("apps.fornecedores.urls")),
    path("estoque/", include("apps.estoque.urls")),
    path("cotacoes/", include("apps.cotacoes.urls")),
    path("", include("apps.core.urls")),
]
```

Add before the `core.urls` catch-all:
```python
path("relatorios/", include("apps.relatorios.urls")),
```

---

### `config/settings/base.py` — add to INSTALLED_APPS (config)

**Analog:** Self — find the INSTALLED_APPS list and append the new app

Pattern from existing entries (all follow `"apps.<name>"` format):
```python
INSTALLED_APPS = [
    ...
    "apps.cotacoes",
    "apps.relatorios",  # add after cotacoes
    ...
]
```

---

## Shared Patterns

### Authentication / Access Control
**Source:** `apps/fornecedores/views.py` lines 25-41
**Apply to:** All views in `apps/relatorios/views.py`

```python
from apps.fornecedores.views import CompradorRequiredMixin

class GastosView(CompradorRequiredMixin, View): ...
class GastosPDFView(CompradorRequiredMixin, View): ...
class RequisicoesPainelView(CompradorRequiredMixin, View): ...
class RequisicoespainelPDFView(CompradorRequiredMixin, View): ...
```

The mixin already checks `role in ("comprador", "admin")` and `is_superuser`. It covers `diretor` only if `diretor` is added to the check — verify the mixin against CONTEXT.md §D-02: relatórios are accessible to `comprador`, `diretor`, and `admin`. The existing mixin does NOT include `diretor`. The relatorios views need an extended mixin or the existing `CompradorRequiredMixin` needs to be checked. **Note for planner:** `CompradorRequiredMixin` in `apps/fornecedores/views.py` line 38 checks `role in ("comprador", "admin")` — this excludes `diretor`. Create `RelatorioRequiredMixin` in `apps/relatorios/views.py` that includes `diretor`.

### Service Layer — No Queries in Views
**Source:** `apps/aprovacoes/services.py` lines 1-6 (docstring), `apps/cotacoes/services.py` lines 1-18
**Apply to:** All views in `apps/relatorios/views.py`

Views call `services.<function>(params)` and pass the result directly to context. No ORM calls (`filter`, `aggregate`, `annotate`) inside view methods.

### Sum() None Fallback
**Source:** `apps/cotacoes/services.py` lines 86-95 (pattern for guard against zero)
**Apply to:** All `aggregate(total=Sum(...))` calls in `apps/relatorios/services.py`

```python
resultado = queryset.aggregate(total=Sum("preco_unitario"))
value = resultado["total"] or Decimal("0")
```

### PDF BytesIO Pattern
**Source:** CLAUDE.md §PDF Generation (no existing PDF view in codebase yet — this is the first)
**Apply to:** `GastosPDFView` and `RequisicoespainelPDFView`

```python
buffer = BytesIO()
doc = SimpleDocTemplate(buffer, pagesize=A4)
# ... build story ...
doc.build(story)
buffer.seek(0)
return FileResponse(buffer, as_attachment=True, filename="filename.pdf")
```

### GET Params Parsing
**Source:** `apps/fornecedores/views.py` lines 92-95
**Apply to:** `GastosView`, `GastosPDFView`, `RequisicoesPainelView`, `RequisicoespainelPDFView`

```python
q = request.GET.get("q", "").strip()
categoria_pk = request.GET.get("categoria", "")
# For relatorios:
data_inicio = request.GET.get("data_inicio", date.today().replace(day=1).isoformat())
data_fim = request.GET.get("data_fim", date.today().isoformat())
unidade_id = request.GET.get("unidade", "") or None
```

Validate `data_inicio`/`data_fim` with `datetime.strptime()` + try/except, defaulting to current month on parse failure (security: RESEARCH.md §Known Threat Patterns).

### Test Class Structure
**Source:** `apps/cotacoes/tests/test_views.py` lines 18-60
**Apply to:** `apps/relatorios/tests/test_views.py` and `apps/relatorios/tests/test_services.py`

- One class per feature group (e.g., `TestAcesso`, `TestGastosView`, `TestPDF`)
- Use `client.force_login(user)` for authentication
- Use `pytest.mark.django_db` implicitly via `db` fixture dependency
- Assert `response.status_code` and response content

### user.default_unit (Critical)
**Source:** `apps/cotacoes/tests/conftest.py` line 31 — `default_unit=test_unit`
**Apply to:** All queries filtering by user unit in `apps/relatorios/services.py`

The field is `user.default_unit`, NOT `user.unidade`. CONTEXT.md uses `user.unidade` informally — the code must use `user.default_unit` (verified in `apps/accounts/models.py` line 44 per RESEARCH.md).

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `apps/relatorios/apps.py` | config | — | No existing apps.py read directly; structure inferred from Django convention and RESEARCH.md code example — straightforward `AppConfig` boilerplate |

---

## Critical Notes for Planner

1. **RelatorioRequiredMixin vs CompradorRequiredMixin:** `CompradorRequiredMixin` in `fornecedores/views.py` allows `comprador` and `admin` only. The relatorios views must allow `diretor` too (CONTEXT.md). Create a new `RelatorioRequiredMixin` in `apps/relatorios/views.py` with `role in ("comprador", "diretor", "admin")`.

2. **Month + Year filter:** Every `__month=mes_atual` lookup must be paired with `__year=ano_atual` or the KPI will accumulate data from prior years after 12 months in production.

3. **DashboardView import dependency:** `apps/core/views.py` will import from `apps.relatorios.services` — `apps.relatorios` must be in `INSTALLED_APPS` and the app must be created before running the server.

4. **No new pip packages:** `reportlab` is already in `requirements.txt`; all other imports are Django stdlib or Python stdlib.

## Metadata

**Analog search scope:** `apps/aprovacoes/`, `apps/cotacoes/`, `apps/fornecedores/`, `apps/core/`, `templates/`, `config/`
**Files scanned:** 11 source files read directly
**Pattern extraction date:** 2026-06-11
