# Fase 2: Requisições & Aprovações — Mapa de Padrões

**Mapeado:** 2026-06-10
**Arquivos analisados:** 16 (novos/modificados)
**Analogs encontrados:** 16 / 16

---

## Classificação de Arquivos

| Arquivo Novo/Modificado | Papel | Fluxo de Dados | Analog Mais Próximo | Qualidade |
|------------------------|-------|----------------|---------------------|-----------|
| `apps/requisicoes/models.py` | model | CRUD | `apps/accounts/models.py` | exato |
| `apps/requisicoes/forms.py` | form | request-response | `apps/accounts/forms.py` | exato |
| `apps/requisicoes/views.py` | controller | request-response | `apps/accounts/views.py` | exato |
| `apps/requisicoes/admin.py` | config | CRUD | `apps/accounts/models.py` (padrão inferido) | role-match |
| `apps/requisicoes/templates/requisicoes/requisicao_list.html` | template | request-response | `apps/accounts/templates/accounts/user_list.html` | exato |
| `apps/requisicoes/templates/requisicoes/requisicao_form.html` | template | request-response | `apps/accounts/templates/accounts/user_form.html` | exato |
| `apps/requisicoes/templates/requisicoes/requisicao_detail.html` | template | request-response | `apps/accounts/templates/accounts/user_list.html` | role-match |
| `apps/requisicoes/templates/requisicoes/partials/requisicao_row.html` | template | request-response | `apps/accounts/templates/accounts/partials/user_row.html` | exato |
| `apps/requisicoes/templates/requisicoes/partials/status_badge.html` | template | request-response | `apps/accounts/templates/accounts/partials/user_row.html` (badge) | exato |
| `apps/requisicoes/templates/requisicoes/partials/copiar_dados.html` | template | request-response | `apps/accounts/templates/accounts/partials/user_form.html` (HTMX hx-get) | role-match |
| `apps/aprovacoes/models.py` | model | CRUD | `apps/core/models.py` + `apps/accounts/models.py` | exato |
| `apps/aprovacoes/services.py` | service | request-response | `apps/accounts/services.py` | exato |
| `apps/aprovacoes/views.py` | controller | request-response | `apps/accounts/views.py` | exato |
| `apps/aprovacoes/admin.py` | config | CRUD | (padrão do Django admin nativo) | role-match |
| `apps/aprovacoes/templates/aprovacoes/fila_gestor.html` | template | request-response | `apps/accounts/templates/accounts/user_list.html` | exato |
| `apps/aprovacoes/templates/aprovacoes/partials/modal_reprovar.html` | template | request-response | `apps/accounts/templates/accounts/user_confirm_deactivate.html` | exato |
| `config/settings/base.py` | config | — | `config/settings/base.py` (modificação) | exato |

---

## Padrões por Arquivo

### `apps/requisicoes/models.py` (model, CRUD)

**Analog:** `apps/accounts/models.py` + `apps/core/models.py`

**Padrão de imports** (accounts/models.py linhas 7-8 + core/models.py linhas 1-4):
```python
from django.conf import settings
from django.db import models
from apps.core.models import AuditedModel
```

**Padrão de modelo com TextChoices** (accounts/models.py linhas 27-32):
```python
class User(AbstractUser):
    class Role(models.TextChoices):
        SOLICITANTE = "solicitante", "Solicitante"
        GESTOR = "gestor", "Gestor"
```
Aplicar o mesmo padrão de `TextChoices` para `Requisicao.Status`.

**Padrão de FK com SET_NULL e related_name** (accounts/models.py linhas 44-50):
```python
default_unit = models.ForeignKey(
    UnidadeOrganizacional,
    null=True,
    blank=True,
    on_delete=models.SET_NULL,
    related_name="default_users",
)
```
`Requisicao.unidade` usa `on_delete=models.PROTECT` (não SET_NULL — requisição não pode perder unidade).

**Padrão de AuditedModel** (core/models.py linhas 14-23):
```python
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
`Requisicao(AuditedModel)` herda `criado_por`, `criado_em`, `atualizado_em` gratuitamente.

**Padrão de DecimalField monetário** (core/models.py linha 1, comentário):
```python
# Monetary fields in all apps: DecimalField(max_digits=12, decimal_places=2) — never FloatField
```
`valor_estimado = models.DecimalField(max_digits=12, decimal_places=2)` — obrigatório.

**Padrão de Meta** (accounts/models.py linhas 17-20):
```python
class Meta:
    verbose_name = "Unidade Organizacional"
    verbose_name_plural = "Unidades Organizacionais"
    ordering = ["nome"]
```

---

### `apps/requisicoes/forms.py` (form, request-response)

**Analog:** `apps/accounts/forms.py`

**Padrão de imports** (accounts/forms.py linhas 1-6):
```python
from django import forms
from .models import UnidadeOrganizacional, User
```

**Padrão de ModelForm simples** (accounts/forms.py linhas 39-42):
```python
class UnidadeForm(forms.ModelForm):
    class Meta:
        model = UnidadeOrganizacional
        fields = ["nome", "descricao", "ativo"]
```
`RequisicaoForm` segue este padrão com `fields = ["descricao", "categoria", "valor_estimado", "justificativa", "unidade"]`.

**Padrão de validação cruzada em `clean()`** (accounts/forms.py linhas 24-29):
```python
def clean(self):
    cleaned_data = super().clean()
    p1 = cleaned_data.get("password1")
    p2 = cleaned_data.get("password2")
    if p1 and p2 and p1 != p2:
        raise forms.ValidationError("As senhas não coincidem. Tente novamente.")
    return cleaned_data
```
`AprovacaoForm.clean()` valida que `motivo` não está vazio quando `acao == 'reprovar'`.

---

### `apps/requisicoes/views.py` (controller, request-response)

**Analog:** `apps/accounts/views.py`

**Padrão de imports** (accounts/views.py linhas 1-21):
```python
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import ListView

from . import services
from .forms import UnidadeForm, UserCreateForm, UserEditForm
from .models import UnidadeOrganizacional, User
```

**Padrão de View com HTMX: GET + POST + partial response** (accounts/views.py linhas 120-143):
```python
class UserCreateView(AdminRequiredMixin, View):
    def get(self, request):
        form = UserCreateForm()
        return render(
            request,
            "accounts/user_form.html",
            {"form": form, "action": "create", "page_title": "Criar Usuário"},
        )

    def post(self, request):
        form = UserCreateForm(request.POST)
        if form.is_valid():
            services.create_user(form.cleaned_data)
            if request.htmx:
                from django_htmx.http import HttpResponseClientRedirect
                return HttpResponseClientRedirect(reverse("accounts:user-list"))
            return redirect("accounts:user-list")
        template = (
            "accounts/partials/user_form.html"
            if request.htmx
            else "accounts/user_form.html"
        )
        return render(request, template, {"form": form, "action": "create"})
```
Chave: `if request.htmx` decide template full vs partial. Views do Solicitante replicam exatamente este padrão.

**Padrão de partial para `outerHTML` swap** (accounts/views.py linhas 193-202):
```python
class UserDeactivateView(AdminRequiredMixin, View):
    def post(self, request, pk):
        target_user = get_object_or_404(User, pk=pk)
        services.deactivate_user(target_user, actor=request.user)
        # Return updated row partial for HTMX outerHTML swap
        return render(
            request,
            "accounts/partials/user_row.html",
            {"user": target_user},
        )
```
Views de aprovação/reprovação retornam `fila_row.html` com `outerHTML swap` — mesmo padrão.

**Padrão de ListView com get_queryset** (accounts/views.py linhas 111-117):
```python
class UserListView(AdminRequiredMixin, ListView):
    model = User
    template_name = "accounts/user_list.html"
    context_object_name = "users"

    def get_queryset(self):
        return User.objects.select_related("default_unit").order_by("email")
```
`FilaGestorView` e `RequisicaoListView` replicam com filtros específicos.

---

### `apps/aprovacoes/models.py` (model, CRUD)

**Analog:** `apps/core/models.py` + `apps/accounts/models.py`

**Padrão de TimestampedModel** (core/models.py linhas 6-12):
```python
class TimestampedModel(models.Model):
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
```
`AprovacaoLog(TimestampedModel)` — herda campos de auditoria sem `criado_por` (o campo `aprovador` é explícito no log).

**Padrão de FK para AUTH_USER_MODEL** (core/models.py linhas 15-20):
```python
criado_por = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    null=True,
    on_delete=models.SET_NULL,
    related_name="%(app_label)s_%(class)s_criado",
)
```
`AprovacaoLog.aprovador` usa `settings.AUTH_USER_MODEL` com `null=True, on_delete=models.SET_NULL`.

---

### `apps/aprovacoes/services.py` (service, request-response)

**Analog:** `apps/accounts/services.py`

**Padrão de docstring de módulo** (accounts/services.py linhas 1-5):
```python
"""
Accounts service layer.
Business logic for user and organizational unit management.
Views call these functions — never contain business logic themselves.
"""
```

**Padrão de função de serviço** (accounts/services.py linhas 11-29):
```python
def create_user(data: dict) -> User:
    """
    Create a new user with the given data.
    Sets password via set_password() and assigns to the appropriate Django Group.
    """
    ...
    user.save()
    return user
```
Funções retornam o objeto modificado; sem efeitos colaterais invisíveis.

**Padrão de `save(update_fields=...)`** (accounts/services.py linha 39):
```python
user.save(update_fields=["is_active"])
```
Todas as transições de estado em `aprovacoes/services.py` usam `save(update_fields=['status', 'atualizado_em'])` — nunca `save()` completo.

---

### `apps/aprovacoes/views.py` (controller, request-response)

**Analog:** `apps/accounts/views.py`

**Padrão de AdminRequiredMixin** (accounts/views.py linhas 95-103):
```python
class AdminRequiredMixin(LoginRequiredMixin):
    """Restrict access to users with role='admin' or is_superuser=True."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role != "admin" and not request.user.is_superuser:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
```
`GestorRequiredMixin` e `DiretorRequiredMixin` replicam exatamente este padrão, alterando apenas a condição de role.

**Padrão de hx-get para modal** (accounts/templates/accounts/partials/user_row.html linha 18):
```html
<button hx-get="{% url 'accounts:user-deactivate-confirm' user.pk %}"
        hx-target="#confirm-container"
        hx-swap="innerHTML"
        class="btn btn-ghost" ...>Desativar</button>
```
Botão "Reprovar" na fila do Gestor usa o mesmo padrão: `hx-get` carrega modal em `#modal-container`.

---

### Templates de Requisições

**Analog:** `apps/accounts/templates/accounts/`

**Padrão de template de listagem** (accounts/templates/accounts/user_list.html completo):
```html
{% extends "base.html" %}
{% block page_title %}Usuários{% endblock %}
{% block page_actions %}<a href="..." class="btn btn-primary">Criar usuário</a>{% endblock %}
{% block content %}
  <div id="confirm-container"></div>
  {% if users %}
    <div class="table-container">
      <table>
        <thead><tr><th>...</th></tr></thead>
        <tbody>
          {% for user in users %}
            {% include "accounts/partials/user_row.html" %}
          {% endfor %}
        </tbody>
      </table>
    </div>
  {% else %}
    <div class="card" style="text-align:center">
      <p ...>Nenhum usuário cadastrado</p>
    </div>
  {% endif %}
{% endblock %}
```
`requisicao_list.html` e `fila_gestor.html` copiam esta estrutura: `extend base.html`, bloco `page_actions` com botão CTA, tabela com include de partial de linha, estado vazio.

**Padrão de linha de tabela com badge e ações HTMX** (accounts/templates/accounts/partials/user_row.html completo):
```html
<tr id="user-row-{{ user.pk }}" ...>
  <td>...</td>
  <td>
    <span class="badge {% if user.is_active %}badge-ativo{% else %}badge-inativo{% endif %}">...</span>
  </td>
  <td>
    <button hx-get="..." hx-target="#confirm-container" hx-swap="innerHTML" class="btn btn-ghost">Desativar</button>
  </td>
</tr>
```
`fila_row.html` e `requisicao_row.html` replicam: `id="fila-row-{{ req.pk }}"` para target de `outerHTML swap`.

**Padrão de formulário full/partial** (accounts/templates/accounts/user_form.html + partials/user_form.html):
```html
{# user_form.html — full page #}
{% extends "base.html" %}
{% block content %}
  <div class="card" style="max-width:640px;">
    <div id="form-container">
      {% include "accounts/partials/user_form.html" %}
    </div>
  </div>
{% endblock %}

{# partials/user_form.html — o form em si #}
<form hx-post="..." hx-target="#form-container" hx-swap="innerHTML">
  {% csrf_token %}
  {% for field in form %}
    <div class="form-group">
      <label class="form-label" for="{{ field.id_for_label }}">{{ field.label }}{% if field.field.required %} *{% endif %}</label>
      {{ field }}
      {% for error in field.errors %}<p class="form-error">{{ error }}</p>{% endfor %}
    </div>
  {% endfor %}
  <div class="form-actions">
    <button type="submit" class="btn btn-primary">...</button>
    <a href="..." class="btn btn-secondary">Cancelar</a>
  </div>
</form>
<script>
document.querySelectorAll('#form-container input, #form-container select, #form-container textarea').forEach(function(el) {
  el.classList.add(el.tagName.toLowerCase() === 'select' ? 'form-select' : 'form-input');
});
</script>
```
`requisicao_form.html` e `partials/campos_requisicao.html` replicam esta estrutura exatamente. O `<script>` de aplicação de classes CSS é obrigatório — sem ele os campos ficam sem estilo.

**Padrão de modal de confirmação** (accounts/templates/accounts/user_confirm_deactivate.html completo):
```html
<div class="card" style="margin-bottom:16px;border-color:var(--color-destructive);">
  <p style="font-size:14px;margin-bottom:16px;">
    <strong>Desativar usuário:</strong> ...
  </p>
  <div style="display:flex;gap:8px;">
    <button hx-post="{% url 'accounts:user-deactivate' target_user.pk %}"
            hx-target="#user-row-{{ target_user.pk }}"
            hx-swap="outerHTML"
            class="btn btn-destructive">Confirmar desativação</button>
    <button hx-get="" hx-target="#confirm-container" hx-swap="innerHTML"
            class="btn btn-secondary">Cancelar</button>
  </div>
</div>
```
`modal_reprovar.html` copia este padrão com `<textarea name="motivo" required>` adicional e `{% csrf_token %}` obrigatório (CR-04).

---

## Padrões Compartilhados (Cross-Cutting)

### Autenticação / Proteção de Views
**Fonte:** `apps/accounts/views.py` linhas 95-103
**Aplicar em:** todas as views de `apps/requisicoes/views.py` e `apps/aprovacoes/views.py`
```python
class AdminRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role != "admin" and not request.user.is_superuser:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
```
Replicar como `SolicitanteRequiredMixin`, `GestorRequiredMixin`, `DiretorRequiredMixin` alterando a condição `role`.

### HTMX: Detecção de Requisição e Retorno de Partial
**Fonte:** `apps/accounts/views.py` linhas 133-143
**Aplicar em:** todas as views POST de `apps/requisicoes/views.py` e `apps/aprovacoes/views.py`
```python
if request.htmx:
    from django_htmx.http import HttpResponseClientRedirect
    return HttpResponseClientRedirect(reverse("accounts:user-list"))
return redirect("accounts:user-list")
# ou para erros:
template = (
    "accounts/partials/user_form.html"
    if request.htmx
    else "accounts/user_form.html"
)
```

### HTMX: hx-get para Modal + hx-post com outerHTML swap
**Fonte:** `apps/accounts/templates/accounts/partials/user_row.html` linha 18 + `user_confirm_deactivate.html` linhas 6-7
**Aplicar em:** `fila_gestor.html`, `fila_diretor.html`, `modal_reprovar.html`
```html
{# Botão que abre modal #}
<button hx-get="{% url 'aprovacoes:modal-reprovar' req.pk %}"
        hx-target="#modal-container"
        hx-swap="innerHTML"
        class="btn btn-destructive btn-sm">Reprovar</button>

{# Modal faz POST e atualiza a linha diretamente #}
<button hx-post="{% url 'aprovacoes:reprovar' req.pk %}"
        hx-target="#fila-row-{{ req.pk }}"
        hx-swap="outerHTML"
        class="btn btn-destructive">Confirmar</button>
```

### CSRF em Forms de Partials HTMX
**Fonte:** `apps/accounts/templates/accounts/partials/user_form.html` linha 2 — validado por CR-04 em `01-REVIEW.md`
**Aplicar em:** TODOS os `<form>` em partials: `campos_requisicao.html`, `modal_reprovar.html`, `modal_aprovar.html`
```html
<form hx-post="..." ...>
  {% csrf_token %}   {# OBRIGATÓRIO — sem isso HTTP 403 #}
  ...
</form>
```

### Aplicação de Classes CSS em Campos de Formulário
**Fonte:** `apps/accounts/templates/accounts/partials/user_form.html` linhas 16-19
**Aplicar em:** todos os templates de formulário dos dois novos apps
```html
<script>
document.querySelectorAll('#form-container input, #form-container select, #form-container textarea').forEach(function(el) {
  el.classList.add(el.tagName.toLowerCase() === 'select' ? 'form-select' : 'form-input');
});
</script>
```

### save(update_fields=...) para Eficiência
**Fonte:** `apps/accounts/services.py` linha 39
**Aplicar em:** todos os `save()` em `apps/aprovacoes/services.py` e `apps/requisicoes/`
```python
obj.save(update_fields=["campo_alterado", "atualizado_em"])
```

### INSTALLED_APPS
**Fonte:** `config/settings/base.py` linhas 19-32
**Modificar:** adicionar `"apps.requisicoes"` e `"apps.aprovacoes"` na seção `# Local apps`
```python
INSTALLED_APPS = [
    ...
    # Local apps
    "apps.core",
    "apps.accounts",
    "apps.requisicoes",   # adicionar
    "apps.aprovacoes",    # adicionar
]
```

---

## Sem Analog Direto

| Arquivo | Papel | Fluxo | Motivo |
|---------|-------|-------|--------|
| `apps/aprovacoes/services.py` (lógica `select_for_update`) | service | transação atômica | Nenhum serviço existente usa transações com lock — padrão novo no projeto. Usar exemplos do RESEARCH.md (Padrão 2) |
| `apps/requisicoes/templates/requisicoes/partials/copiar_dados.html` | template | HTMX `hx-get` com change | Nenhum exemplo de `hx-trigger="change"` em select existe ainda. Usar Padrão 7 do RESEARCH.md |
| `apps/requisicoes/templates/requisicoes/partials/status_badge.html` | template | HTMX polling | Nenhum polling existente. Usar `hx-get` + `hx-trigger="every 15s"` conforme CLAUDE.md Pattern 2 |
| `apps/aprovacoes/templates/aprovacoes/partials/modal_aprovar.html` / `modal_reprovar.html` | template | HTMX modal | Analog parcial em `user_confirm_deactivate.html` mas sem textarea — combinar padrão existente com `{% csrf_token %}` obrigatório |

---

## Metadados

**Escopo de busca de analogs:** `apps/accounts/`, `apps/core/`, `config/settings/`, `templates/`
**Arquivos escaneados:** 17
**Data do mapeamento:** 2026-06-10
