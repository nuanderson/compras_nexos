---
phase: 03-suppliers-inventory
reviewed: 2026-06-11T00:00:00Z
depth: standard
files_reviewed: 33
files_reviewed_list:
  - apps/estoque/admin.py
  - apps/estoque/apps.py
  - apps/estoque/forms.py
  - apps/estoque/models.py
  - apps/estoque/tests/conftest.py
  - apps/estoque/tests/test_forms.py
  - apps/estoque/tests/test_models.py
  - apps/estoque/tests/test_views.py
  - apps/estoque/urls.py
  - apps/estoque/views.py
  - apps/fornecedores/admin.py
  - apps/fornecedores/apps.py
  - apps/fornecedores/forms.py
  - apps/fornecedores/models.py
  - apps/fornecedores/templatetags/fornecedor_tags.py
  - apps/fornecedores/tests/conftest.py
  - apps/fornecedores/tests/test_forms.py
  - apps/fornecedores/tests/test_models.py
  - apps/fornecedores/tests/test_views.py
  - apps/fornecedores/urls.py
  - apps/fornecedores/views.py
  - config/settings/base.py
  - config/urls.py
  - requirements.txt
  - templates/base.html
  - templates/estoque/atualizar_quantidade.html
  - templates/estoque/form.html
  - templates/estoque/lista.html
  - templates/estoque/partials/item_row.html
  - templates/estoque/visao_consolidada.html
  - templates/fornecedores/form.html
  - templates/fornecedores/lista.html
  - templates/fornecedores/partials/fornecedor_list.html
  - templates/fornecedores/partials/fornecedor_row.html
findings:
  critical: 3
  warning: 4
  info: 2
  total: 9
status: issues_found
---

# Fase 03: Relatório de Code Review

**Revisado:** 2026-06-11
**Profundidade:** standard
**Arquivos revisados:** 33
**Status:** issues_found

## Sumário

A implementação dos apps `estoque` e `fornecedores` é estruturalmente sólida. O padrão IDOR está corretamente implementado nas views de edição e atualização de quantidade via `unidade_organizacional=request.user.default_unit`. A validação de CNPJ usa `stdnum.validate()` corretamente. O CSRF está protegido tanto em formulários HTML quanto em requisições HTMX via listener `htmx:configRequest`.

Três bugs críticos foram encontrados: (1) o botão "Atualizar Qtd" em `lista.html` dispara um `hx-get` para uma view que só aceita POST — qualquer clique nesse botão retorna HTTP 405 para todos os usuários; (2) o Comprador (cujo `default_unit` é `None`) está bloqueado de atualizar quantidades pela guarda de IDOR que filtra por `unidade_organizacional=None`; (3) os testes do app `fornecedores` não têm `@pytest.mark.django_db`, fazendo com que os testes de views e models que acessam o banco falhem silenciosamente ou levantem erro de banco em tempo de execução.

---

## Critical Issues

### CR-01: `hx-get` em `lista.html` para view que só aceita POST — HTTP 405 para todos os usuários

**File:** `templates/estoque/lista.html:46`

**Issue:** O botão "Atualizar Qtd" usa `hx-get` para disparar uma requisição GET à URL `estoque:atualizar-quantidade`. A view `AtualizarQuantidadeView` (`apps/estoque/views.py`) só define `def post()` — nenhum handler `def get()`. O Django `View` retorna HTTP 405 (Method Not Allowed) para qualquer método não declarado. Isso significa que **o botão de atualização de quantidade nunca funciona** — todo clique resulta em 405.

O template parcial `item_row.html` (linha 19) usa corretamente `hx-post`, mas ele só é renderizado **após** uma atualização bem-sucedida. A entrada no fluxo (o botão inicial em `lista.html`) está quebrada desde o início.

**Fix:** Trocar `hx-get` por `hx-post` no botão, ou adicionar um handler `def get()` na view que retorne o formulário inline. O mais simples, mantendo o padrão de `item_row.html`:

```html
<!-- templates/estoque/lista.html linha 44-51 — substituir hx-get por hx-post -->
<form
  hx-post="{% url 'estoque:atualizar-quantidade' item.pk %}"
  hx-target="#item-{{ item.pk }}"
  hx-swap="outerHTML"
  style="display:inline;"
>
  {% csrf_token %}
  <input
    type="number"
    name="quantidade_atual"
    value="{{ item.quantidade_atual }}"
    min="0"
    style="width:80px;"
    class="form-control form-control-sm d-inline"
  >
  <button type="submit" class="btn btn-sm btn-accent">Atualizar Qtd</button>
</form>
```

Isso elimina também a necessidade do `<div id="quantidade-modal">` e do template `atualizar_quantidade.html` (que estende `base.html` e seria renderizado dentro de uma `div` inline — gerando HTML aninhado inválido).

---

### CR-02: Comprador com `default_unit=None` não consegue atualizar nenhuma quantidade

**File:** `apps/estoque/views.py:127-130`

**Issue:** `AtualizarQuantidadeView.post()` filtra por `unidade_organizacional=request.user.default_unit`. O Comprador é criado com `default_unit=None` (confirmado em `apps/estoque/tests/conftest.py:46`). A query `ItemEstoque.objects.select_for_update().get(pk=pk, unidade_organizacional=None)` nunca encontra um item real, levantando `ItemEstoque.DoesNotExist` → Http404.

O Comprador deve ter permissão para atualizar quantidades de qualquer unidade (mesma lógica de `ListaEstoqueView` e `EditarItemEstoqueView`), mas `AtualizarQuantidadeView` não possui a mesma guarda condicional de role.

**Fix:**

```python
# apps/estoque/views.py — AtualizarQuantidadeView.post()
def post(self, request, pk):
    user = request.user
    try:
        with transaction.atomic():
            if user.is_superuser or user.role in ("comprador", "admin"):
                item = ItemEstoque.objects.select_for_update().get(pk=pk)
            else:
                item = ItemEstoque.objects.select_for_update().get(
                    pk=pk,
                    unidade_organizacional=user.default_unit,
                )
            form = AtualizarQuantidadeForm(request.POST, instance=item)
            if form.is_valid():
                form.save()
                return render(request, "estoque/partials/item_row.html", {"item": item})
            return render(
                request,
                "estoque/partials/item_row.html",
                {"item": item, "form": form},
                status=422,
            )
    except ItemEstoque.DoesNotExist:
        raise Http404
```

---

### CR-03: Testes de `fornecedores` sem `@pytest.mark.django_db` — acesso ao banco falha em runtime

**File:** `apps/fornecedores/tests/test_views.py:14` e `apps/fornecedores/tests/test_models.py:30`

**Issue:** As classes `TestListaFornecedoresView`, `TestCadastrarFornecedorView`, `TestToggleAtivoView` (em `test_views.py`) e `TestFornecedorModel`, `TestFornecedorCategoriaProtect`, `TestCnpjFormatFilter` (em `test_models.py`) **não têm** `@pytest.mark.django_db`. Os métodos de teste usam fixtures que acessam o banco (`fornecedor`, `comprador_user`, `categoria`) — isso causa erro de `DatabaseBlockedByTestError` ou falha silenciosa de fixture ao rodar com pytest-django.

Contraste com `apps/estoque/tests/test_views.py` onde todas as classes têm `@pytest.mark.django_db`.

Nota: `TestCnpjFormatFilter` não usa banco e está corretamente sem marcação. As demais classes precisam da marcação.

**Fix:** Adicionar o decorator nas classes que acessam banco:

```python
# apps/fornecedores/tests/test_views.py
@pytest.mark.django_db
class TestListaFornecedoresView:
    ...

@pytest.mark.django_db
class TestCadastrarFornecedorView:
    ...

@pytest.mark.django_db
class TestToggleAtivoView:
    ...
```

```python
# apps/fornecedores/tests/test_models.py
@pytest.mark.django_db
class TestFornecedorModel:
    ...

@pytest.mark.django_db
class TestFornecedorCategoriaProtect:
    ...
```

---

## Warnings

### WR-01: `ItemEstoqueForm` não valida `quantidade_atual < 0` nem `quantidade_minima < 0` no cadastro/edição

**File:** `apps/estoque/forms.py:12-33`

**Issue:** `AtualizarQuantidadeForm` possui `clean_quantidade_atual()` que rejeita valores negativos. Porém `ItemEstoqueForm` — usado no cadastro e na edição de itens — não possui nenhuma validação equivalente para `quantidade_atual` nem para `quantidade_minima`. Um usuário pode cadastrar um item com `quantidade_atual=-5` ou `quantidade_minima=-10`. O modelo `ItemEstoque` também não possui `MinValueValidator`.

**Fix:**

```python
# apps/estoque/forms.py — ItemEstoqueForm
def clean_quantidade_atual(self):
    valor = self.cleaned_data.get("quantidade_atual")
    if valor is not None and valor < 0:
        raise forms.ValidationError("A quantidade não pode ser negativa.")
    return valor

def clean_quantidade_minima(self):
    valor = self.cleaned_data.get("quantidade_minima")
    if valor is not None and valor < 0:
        raise forms.ValidationError("A quantidade mínima não pode ser negativa.")
    return valor
```

Ou, mais robusto, adicionar `MinValueValidator(0)` no model:

```python
# apps/estoque/models.py
from django.core.validators import MinValueValidator

quantidade_atual = models.IntegerField(default=0, validators=[MinValueValidator(0)])
quantidade_minima = models.IntegerField(default=0, validators=[MinValueValidator(0)])
```

---

### WR-02: HTMX toggle-ativo envia POST sem CSRF token explícito no `fornecedor_row.html`

**File:** `templates/fornecedores/partials/fornecedor_row.html:18-26`

**Issue:** O botão de toggle usa `hx-post` mas está dentro de um `<tr>`, não de um `<form>`. O mecanismo de CSRF depende inteiramente do listener JavaScript em `base.html` que injeta `X-CSRFToken` no header via `htmx:configRequest`. Isso funciona corretamente quando o botão é renderizado pela página completa (com `base.html`). Porém, quando `fornecedor_row.html` é retornado como **partial** pelo `ToggleAtivoView` (via `hx-swap="outerHTML"`), o `<tr>` resultante é inserido no DOM — e como `base.html` já está carregado na página, o listener global continua ativo e cobre esse caso.

O risco real é que se o partial for consumido fora do contexto de `base.html` (ex: testes de integração que fazem assertions no conteúdo HTML do partial isoladamente), a ausência de `{% csrf_token %}` fica mascarada. Não é um bug crítico no fluxo normal, mas é uma dependência implícita frágil.

**Fix:** Envolver o botão em um `<form>` inline com `{% csrf_token %}`:

```html
<form
  method="post"
  action="{% url 'fornecedores:toggle-ativo' fornecedor.pk %}"
  hx-post="{% url 'fornecedores:toggle-ativo' fornecedor.pk %}"
  hx-target="#fornecedor-{{ fornecedor.pk }}"
  hx-swap="outerHTML"
  hx-confirm="Confirmar alteração de status?"
  style="display:inline;"
>
  {% csrf_token %}
  <button type="submit" ...>
    {% if fornecedor.ativo %}Inativar{% else %}Reativar{% endif %}
  </button>
</form>
```

---

### WR-03: `ToggleAtivoView` não usa `save(update_fields=["ativo", "updated_at"])` — campo `updated_at` de `TimestampedModel` pode ficar desatualizado

**File:** `apps/fornecedores/views.py:172`

**Issue:** `fornecedor.save(update_fields=["ativo"])` atualiza apenas o campo `ativo` no banco. Se `TimestampedModel` define `updated_at = models.DateTimeField(auto_now=True)`, o Django **não** atualiza `auto_now` fields quando `update_fields` é especificado sem incluir `updated_at`. Consequência: o registro mostrará um `updated_at` antigo mesmo após o toggle.

**Fix:** Incluir `updated_at` em `update_fields`:

```python
fornecedor.save(update_fields=["ativo", "updated_at"])
```

Ou verificar se `TimestampedModel.updated_at` usa `auto_now=True` — se sim, este é o comportamento correto a corrigir.

---

### WR-04: `get_queryset_fornecedores()` retorna fornecedores inativos em todas as buscas — sem filtro de `ativo`

**File:** `apps/fornecedores/views.py:56`

**Issue:** `get_queryset_fornecedores()` não filtra por `ativo=True`. A busca por nome e CNPJ retorna fornecedores inativos misturados com os ativos. Um Comprador pode selecionar um fornecedor inativo para uma cotação sem perceber.

Isso é consistente com o requisito FORN-04 ("toggle ativo sem perda de histórico"), que implica que inativos devem ainda aparecer na lista para gestão. Porém a busca `q` provavelmente deve indicar visualmente ou filtrar inativos. Como a exibição do campo `ativo` existe na linha (`fornecedor_row.html`), o comportamento atual pode ser intencional para listagem de gestão.

Se o requisito for que busca por nome/CNPJ só retorne ativos, a correção é:

```python
qs = Fornecedor.objects.select_related("categoria").filter(ativo=True)
```

Classificado como WARNING porque o comportamento pode ser intencional, mas está não documentado e pode causar confusão operacional.

---

## Info

### IN-01: `atualizar_quantidade.html` estende `base.html` mas é usado como alvo de `hx-target="#quantidade-modal"` em `lista.html`

**File:** `templates/estoque/atualizar_quantidade.html:1`

**Issue:** O template estende `base.html` (gerando HTML completo com `<html>`, `<head>`, `<body>`), mas em `lista.html` ele seria injetado via HTMX dentro de `<div id="quantidade-modal">`. Isso resulta em HTML aninhado inválido — um documento `<html>` dentro de um `<div>`. Browsers tendem a corrigir silenciosamente, mas é semanticamente incorreto. (Note que CR-01 já elimina o uso desse template no fluxo HTMX; esse item é residual.)

**Fix:** Se o template for mantido como fallback sem HTMX (navegação direta), está correto. Se for usado como partial HTMX, remover o `{% extends "base.html" %}` e transformá-lo num partial simples.

---

### IN-02: Ausência de `reportlab` em `requirements.txt`

**File:** `requirements.txt`

**Issue:** O `CLAUDE.md` especifica ReportLab como biblioteca mandatória para geração de PDF (cliente definiu). O arquivo `requirements.txt` não contém `reportlab`. O app `relatorios` ainda não está no `INSTALLED_APPS`, então isso não gera erro imediato, mas quando a fase de relatórios for implementada, a dependência estará faltando.

**Fix:** Adicionar ao `requirements.txt`:

```
reportlab
```

---

_Revisado: 2026-06-11_
_Revisor: Claude (gsd-code-reviewer)_
_Profundidade: standard_
