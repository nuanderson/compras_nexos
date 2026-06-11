# Phase 3: Suppliers & Inventory — Research

**Researched:** 2026-06-11
**Domain:** Django forms/validation, pg_trgm search, HTMX live search, Django Admin config models
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01 — Categorias de fornecedores: reusar CategoriaCompra**
Fornecedor usa FK para `CategoriaCompra` (já existente em `apps/requisicoes`).
FK `PROTECT` — não deletar categoria com fornecedor vinculado. Campo obrigatório.

**D-02 — CNPJ: armazenar compactado, validar com python-stdnum**
`cnpj = models.CharField(max_length=14, unique=True)`. Validar + compactar no `clean()` do form, nunca no model.

**D-03 — Busca de fornecedores: pg_trgm fuzzy + filtro de categoria**
TrigramSimilarity em `razao_social`, busca exata em `cnpj`. Filtro de categoria via GET param.
HTMX live search com `hx-trigger="input delay:300ms"`.

**D-04 — Unidade de medida do estoque: modelo configurável pelo Admin**
Modelo `UnidadeMedida` em `apps/estoque` com `nome`, `sigla`, `ativo`. FK em `ItemEstoque`.
Seed migration `0002_seed_unidades.py` com: UN, KG, CX, L, M, PAR, PCT, RES.

**D-05 — Atualização de estoque: edição direta do campo quantidade**
`POST /estoque/<pk>/editar/` substitui `quantidade_atual` diretamente. `select_for_update()` para concorrência.

**D-06 — Isolamento de estoque por unidade**
`ItemEstoque` tem FK para `UnidadeOrganizacional`. Solicitante/Gestor: `unidade=request.user.default_unit`.
Comprador/Admin: sem filtro de unidade.

### Claude's Discretion

Nada explicitamente delegado. Todas as decisões técnicas de implementação (nomes de URLs, estrutura de partials,
padrão de template filter vs. model property para formatação de CNPJ) ficam a critério do implementador,
desde que sigam as convenções das fases anteriores.

### Deferred Ideas (OUT OF SCOPE)

- Histórico de movimentações de estoque (v2 — EST-V2-01)
- Avaliação de fornecedor após compra (v2 — FORN-V2-01)
- Alerta automático de estoque baixo → sugestão de requisição (v2 — EST-V2-02)
- Many-to-many categorias por fornecedor (v2 se necessário)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FORN-01 | Comprador cadastra fornecedores: CNPJ, razão social, e-mail, telefone | Model `Fornecedor(TimestampedModel)` com campos typed abaixo |
| FORN-02 | Validação CNPJ via `python-stdnum` (suporta formato alfanumérico jul/2026) | `validate()` + `InvalidLength/Format/Checksum` — ver §python-stdnum API |
| FORN-03 | Fornecedores organizados por categorias — reusar `CategoriaCompra` | FK confirmado no model existente |
| FORN-04 | Ativar/inativar fornecedor sem perder histórico | `ativo = BooleanField` + `ToggleAtivoView` via HTMX outerHTML swap |
| FORN-05 | Busca e filtro por nome, CNPJ ou categoria — pg_trgm fuzzy | `TrigramSimilarity` import + Q() para CNPJ exato + GET param categoria |
| EST-01 | Solicitante cadastra itens de estoque da unidade | `ItemEstoque(TimestampedModel)` com `unidade` FK obrigatório |
| EST-02 | Quantidade mínima (ponto de pedido) por item | `quantidade_minima = DecimalField` — não `IntegerField` (pode ser fracionado) |
| EST-03 | Atualização de quantidade — edição direta do campo | `select_for_update()` + `AtualizarQuantidadeForm` com campo único |
| EST-04 | Sistema destaca itens abaixo do mínimo | Propriedade `abaixo_do_minimo` no model + filter/annotation na view |
| EST-05 | Isolamento por unidade | `get_object_or_404(ItemEstoque, pk=pk, unidade=request.user.default_unit)` em toda ação |
| EST-06 | Visão consolidada Comprador/Admin | QuerySet sem filtro de unidade nas views de Comprador |
</phase_requirements>

---

## Summary

Esta fase cria dois apps novos (`apps/fornecedores` e `apps/estoque`) e não modifica nenhum
app existente além de adicionar `python-stdnum` ao `requirements.txt` e registrar os novos apps
em `INSTALLED_APPS` e `config/urls.py`.

O risco técnico mais relevante é o padrão de validação de CNPJ: a função `validate()` de
`python-stdnum` é a API correta (não `compact()` + `is_valid()` como está esboçado no CONTEXT.md).
`validate()` compacta internamente, valida formato, comprimento e dígitos verificadores em uma
única chamada e retorna o CNPJ compactado ou levanta `ValidationError` (subclasse de `ValueError`).
O CONTEXT.md usa o padrão `compact() + is_valid()` que também funciona, mas é redundante.

A busca pg_trgm via `TrigramSimilarity` está disponível no Django 5.2 sem configuração adicional
além da extensão `pg_trgm` que já deve estar habilitada desde a Fase 1. O threshold `sim__gt=0.1`
do CONTEXT.md é razoável para nomes em português mas pode retornar falsos positivos em buscas de
uma ou duas letras — a view deve retornar queryset vazio quando `q` estiver em branco.

O padrão HTMX de live search com `hx-trigger="input delay:300ms"` está bem estabelecido nas fases
anteriores (CLAUDE.md). O único cuidado especial é retornar uma partial vazia (não 404) quando a
query está vazia, para que HTMX limpe a lista sem erro.

**Primary recommendation:** Use `stdnum.br.cnpj.validate()` diretamente no `clean_cnpj()` do form.
Capture `stdnum.exceptions.ValidationError` (não `Exception` bare). Retorne o valor compactado de
`validate()` — ele já é a forma compacta correta para os 14 caracteres do CharField.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| CNPJ validation | Backend (form/view) | — | Validação de dados de entrada pertence ao form layer; nunca no model nem no template |
| Supplier CRUD | Backend (views) | — | Comprador-only; sem lógica no frontend além de HTMX swaps |
| CNPJ display formatting | Template layer | Model property | Template filter `cnpj_format` ou property `cnpj_formatado` — ambos aceitáveis; filter é mais reutilizável |
| pg_trgm search | Database + Backend | — | Annotation SQL via ORM; view monta a query, DB executa |
| HTMX live search | Browser + Backend | — | `hx-trigger` no input, view retorna partial, JS puro mínimo |
| Inventory isolation | Backend (view queryset) | — | Filtro de unidade no queryset, nunca delegado ao template |
| Stock quantity update | Backend (view + form) | DB (select_for_update) | Escrita com lock otimista no nível de linha |
| Below-minimum highlight | Template + Model | — | `item.abaixo_do_minimo` como propriedade; template aplica classe CSS |
| UnidadeMedida config | Django Admin | — | Sem view custom necessária; Admin puro é suficiente |

---

## Standard Stack

### Core (tudo já no projeto — zero novas dependências além de python-stdnum)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `python-stdnum` | 2.2 | Validação CNPJ (e qualquer outro identificador BR) | Única biblioteca com suporte ao formato alfanumérico Jul/2026; LGPL; 14+ anos de histórico |
| `django.contrib.postgres.search` | Django 5.2 built-in | `TrigramSimilarity` para busca fuzzy | Parte do Django contrib; zero dependência extra |
| `django_htmx` | já instalado | `request.htmx`, `retarget`, `reswap` | Padrão do projeto desde Fase 1 |

### Não instalar

Nada adicional. `psycopg2-binary`, `django-htmx` e `whitenoise` já estão no `requirements.txt`.

**Installation:**
```bash
# Adicionar ao requirements.txt:
python-stdnum==2.2
```

**Version verification:**
```bash
pip index versions python-stdnum
# Resultado confirmado: 2.2 é a versão mais recente (2026-06-11)
```

---

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| python-stdnum | PyPI | ~14 anos | alto | github.com/arthurdejong/python-stdnum | [OK] | Aprovado |

**Resultado slopcheck:** `[OK]` — flagged apenas como "classic LLM naming pattern" mas verificado como pacote estabelecido.

**Packages removed due to slopcheck [SLOP] verdict:** none

**Packages flagged as suspicious [SUS]:** none

---

## python-stdnum CNPJ API (FORN-02)

### Funções públicas relevantes

[VERIFIED: pip show python-stdnum + inspect.getsource()]

| Função | Assinatura | Comportamento | Levanta |
|--------|-----------|---------------|---------|
| `validate(number)` | `str -> str` | Compacta + valida formato, comprimento e dígito verificador. Retorna o CNPJ compactado (14 chars). | `InvalidFormat`, `InvalidLength`, `InvalidChecksum` (todas subclasses de `ValidationError` e `ValueError`) |
| `compact(number)` | `str -> str` | Remove separadores (` -./`), faz strip, uppercase. **Nunca levanta exceção.** Retorna string suja se input inválido. | Nunca |
| `is_valid(number)` | `str -> bool` | Retorna `True` se `validate()` não levantaria. | Nunca |
| `format(number)` | `str -> str` | Formata para exibição: `XX.XXX.XXX/XXXX-XX` (numérico) ou `XX.XXX.XXX/XXXX-XX` (alfanumérico). Funciona com ambos os formatos. | — |

### Hierarquia de exceções

```python
stdnum.exceptions.ValidationError  # base — é subclasse de ValueError
├── InvalidFormat       # formato inválido (ex: zeros, delimitador errado)
├── InvalidLength       # comprimento != 14 após compact
├── InvalidChecksum     # dígitos verificadores incorretos
└── InvalidComponent    # componente inválido
```

Importação: `from stdnum.exceptions import ValidationError`
Ou captura de tudo: `except ValidationError as e:` — cobre todos os subtipos.

### Suporte ao formato alfanumérico (Jul/2026)

[VERIFIED: pip show python-stdnum 2.2 + docstring + interactive test]

A versão 2.2 (mais recente) **já suporta** o formato alfanumérico (Resolução Cofins 252/2026):

```python
# Exemplo do docstring oficial da lib:
cnpj.validate('12. ABC.345 /01DE-35')  # → '12ABC34501DE35'
cnpj.validate('12ABC34501DE35')        # → '12ABC34501DE35'
cnpj.format('12ABC34501DE35')          # → '12.ABC.345/01DE-35'
```

O campo `cnpj = CharField(max_length=14)` suporta ambos os formatos sem alteração — ambos têm exatamente 14 caracteres após `compact()`.

**Regex interna:** `^[\dA-Z]+$` — dígitos e letras maiúsculas apenas. `compact()` já faz `.upper()`.

### Padrão correto para `clean_cnpj()` no form

[VERIFIED: interactive Python session 2026-06-11]

```python
# apps/fornecedores/forms.py
from stdnum.br import cnpj as cnpj_lib
from stdnum.exceptions import ValidationError as StdnumValidationError

class FornecedorForm(forms.ModelForm):
    def clean_cnpj(self):
        valor = self.cleaned_data.get("cnpj", "")
        try:
            # validate() = compact() + check_length + check_format + check_checksum
            # Retorna o CNPJ compactado (14 chars) — pronto para salvar
            compactado = cnpj_lib.validate(valor)
        except StdnumValidationError:
            raise forms.ValidationError("CNPJ inválido. Verifique os dígitos.")
        # Unicidade manual (exclui próprio pk em edição)
        qs = Fornecedor.objects.filter(cnpj=compactado)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Já existe um fornecedor cadastrado com este CNPJ.")
        return compactado
```

**Por que `validate()` e não `compact() + is_valid()`:**
- `compact()` nunca levanta exceção — retorna garbage se input for inválido (`compact("abc") → "ABC"`)
- `validate()` é a função oficial que combina compact + todas as verificações em uma chamada
- O CONTEXT.md usa `compact() + is_valid()` com `except Exception` — funciona, mas o `except Exception` esconde bugs; use `StdnumValidationError` específico

**Diferença entre `clean()` e `validate()` na lib:**
- `stdnum.br.cnpj.clean(number)` — formata com separadores (ex: `11.222.333/0001-81`), NÃO é o `forms.clean_cnpj()`
- Não usar `cnpj_lib.clean()` no form — confundiria os dois "clean"

---

## pg_trgm + TrigramSimilarity (FORN-05)

### Import path confirmado

[VERIFIED: Python REPL 2026-06-11]

```python
from django.contrib.postgres.search import TrigramSimilarity
# Também disponível, mas não necessário para esta fase:
# TrigramDistance, TrigramWordSimilarity, TrigramStrictWordSimilarity
```

### Padrão combinado: fuzzy em nome + exato em CNPJ + filtro categoria

```python
# apps/fornecedores/views.py
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Q

def get_queryset_fornecedores(q=None, categoria_pk=None, apenas_ativos=True):
    qs = Fornecedor.objects.select_related("categoria")
    if apenas_ativos:
        qs = qs.filter(ativo=True)
    if categoria_pk:
        qs = qs.filter(categoria_id=categoria_pk)
    if q:
        # Estratégia: tenta CNPJ exato primeiro, senão fuzzy em razao_social
        cnpj_compactado = q.replace(".", "").replace("/", "").replace("-", "").strip().upper()
        if len(cnpj_compactado) == 14 and cnpj_compactado.isalnum():
            # Query parece ser um CNPJ — busca exata
            qs = qs.filter(cnpj=cnpj_compactado)
        else:
            # Fuzzy no nome
            qs = (
                qs.annotate(sim=TrigramSimilarity("razao_social", q))
                .filter(sim__gt=0.1)
                .order_by("-sim")
            )
    else:
        qs = qs.order_by("razao_social")
    return qs
```

### Threshold `sim__gt=0.1`

[ASSUMED] — Valor do CONTEXT.md. 0.1 é permissivo (retorna quase qualquer match de 2+ chars).
Para nomes em português com acentos, 0.1 é adequado pois `pg_trgm` não é sensível a case mas
é sensível a acentos. Para buscas de 1-2 caracteres (ex: "AB"), o threshold baixo pode retornar
muitos resultados. A view deve retornar queryset vazio (não erro) quando `q == ""`.

**Pitfall — query vazia:** Se `q = ""` e `sim__gt=0.1`, o resultado é imprevisível. Sempre
guardar o `if q:` antes de aplicar o annotate.

### pg_trgm extension

A extensão `pg_trgm` deve estar habilitada desde a Fase 1 (migration `TrigramExtension()`). Se não
estiver, a query levanta `ProgrammingError: function similarity(character varying, unknown) does not exist`.
O plano deve verificar ou criar a migration de extensão se ainda não existir.

---

## HTMX Live Search (FORN-05)

### Padrão confirmado no projeto (base.html já configura CSRF via event listener)

[VERIFIED: apps/aprovacoes/views.py + templates/base.html]

O projeto já usa `htmx:configRequest` para CSRF em todos os requests HTMX. Não é necessário
`hx-headers` adicional no input de busca.

### Template de input para live search

```html
<!-- templates/fornecedores/partials/search_bar.html -->
<input
  type="search"
  name="q"
  value="{{ request.GET.q }}"
  placeholder="Buscar por nome ou CNPJ..."
  hx-get="{% url 'fornecedores:lista' %}"
  hx-trigger="input delay:300ms, search"
  hx-target="#fornecedores-list"
  hx-swap="innerHTML"
  hx-include="[name='categoria']"
>
```

**`hx-trigger="input delay:300ms, search"`** — `search` captura o clique no X do campo tipo
`search` (quando usuário limpa o campo), garantindo que a lista seja esvaziada sem aguardar o delay.

**`hx-include="[name='categoria']"`** — inclui o select de categoria no mesmo request, permitindo
que filtro de categoria e busca por nome funcionem juntos sem JavaScript adicional.

### View com detecção de HTMX

```python
# apps/fornecedores/views.py
class ListaFornecedoresView(CompradorRequiredMixin, View):
    def get(self, request):
        q = request.GET.get("q", "").strip()
        categoria_pk = request.GET.get("categoria", "")
        qs = get_queryset_fornecedores(q=q or None, categoria_pk=categoria_pk or None)
        ctx = {
            "fornecedores": qs,
            "categorias": CategoriaCompra.objects.filter(ativo=True),
            "q": q,
            "categoria_pk": categoria_pk,
        }
        if request.htmx:
            return render(request, "fornecedores/partials/fornecedor_list.html", ctx)
        return render(request, "fornecedores/lista.html", ctx)
```

### Evitar full page reload em query vazia

Quando `q == ""`, a view deve retornar a lista completa (sem filtro de nome), não um erro.
O template partial `fornecedor_list.html` renderiza a tabela mesmo com queryset vazio
(com mensagem "Nenhum fornecedor encontrado" quando vazio).

---

## CNPJ Display Formatting (FORN-01, FORN-05)

### Abordagem recomendada: template filter customizado

[ASSUMED — convenção comum Django; sem verificação adicional]

Criar `apps/fornecedores/templatetags/fornecedor_tags.py`:

```python
from django import template
from stdnum.br import cnpj as cnpj_lib

register = template.Library()

@register.filter
def cnpj_format(value):
    """Formata CNPJ compactado para exibição: XX.XXX.XXX/XXXX-XX ou XX.XXX.XXX/XXXX-XX (alfanumérico)."""
    if not value:
        return value
    try:
        return cnpj_lib.format(value)
    except Exception:
        return value  # fallback: exibe o valor cru
```

Uso no template:
```html
{% load fornecedor_tags %}
{{ fornecedor.cnpj|cnpj_format }}
```

**Por que filter e não model property:**
- Filter é reutilizável em qualquer template do projeto
- Mantém o model limpo de lógica de apresentação
- `cnpj_lib.format()` já funciona com ambos os formatos (numérico e alfanumérico) — confirmado em teste

**Por que não model property:** O model não deve importar `stdnum` — a responsabilidade de
formatação é de apresentação, não de dados. `str(fornecedor)` já usa `razao_social`.

---

## Django Admin para UnidadeMedida (D-04)

### Padrão para config models simples

[VERIFIED: padrão aplicado em apps/aprovacoes — ConfiguracaoAlcada usa Admin puro]

```python
# apps/estoque/admin.py
from django.contrib import admin
from .models import UnidadeMedida, ItemEstoque

@admin.register(UnidadeMedida)
class UnidadeMedidaAdmin(admin.ModelAdmin):
    list_display = ["nome", "sigla", "ativo"]
    list_editable = ["ativo"]
    list_filter = ["ativo"]
    search_fields = ["nome", "sigla"]
    ordering = ["nome"]

@admin.register(ItemEstoque)
class ItemEstoqueAdmin(admin.ModelAdmin):
    list_display = ["nome", "unidade_organizacional", "quantidade_atual", "quantidade_minima", "abaixo_do_minimo_display"]
    list_filter = ["unidade_organizacional", "unidade_medida"]
    search_fields = ["nome"]
    raw_id_fields = ["unidade_organizacional"]

    def abaixo_do_minimo_display(self, obj):
        return obj.abaixo_do_minimo
    abaixo_do_minimo_display.boolean = True
    abaixo_do_minimo_display.short_description = "Abaixo do mínimo"
```

### Gotchas com Django Admin para config models

1. **`list_editable` exige `list_display`:** O campo editável deve aparecer em `list_display`. `ativo` já está.

2. **`unique=True` em sigla/nome:** O Admin valida unicidade automaticamente via ModelForm. Não é necessário override de `clean()`.

3. **Seed via migration, não fixture:** O CONTEXT.md decide usar `0002_seed_unidades.py`. Migrations de dados
   usam `RunPython` com a função de seed. É importante usar `apps.get_model()` dentro da função de seed,
   não importar o model diretamente (evita estado inconsistente em reversal).

```python
# apps/estoque/migrations/0002_seed_unidades.py
from django.db import migrations

UNIDADES_INICIAIS = [
    ("Unidade", "UN"),
    ("Quilograma", "KG"),
    ("Caixa", "CX"),
    ("Litro", "L"),
    ("Metro", "M"),
    ("Par", "PAR"),
    ("Pacote", "PCT"),
    ("Resma", "RES"),
]

def seed_unidades(apps, schema_editor):
    UnidadeMedida = apps.get_model("estoque", "UnidadeMedida")
    for nome, sigla in UNIDADES_INICIAIS:
        UnidadeMedida.objects.get_or_create(sigla=sigla, defaults={"nome": nome, "ativo": True})

def unseed_unidades(apps, schema_editor):
    UnidadeMedida = apps.get_model("estoque", "UnidadeMedida")
    UnidadeMedida.objects.filter(sigla__in=[s for _, s in UNIDADES_INICIAIS]).delete()

class Migration(migrations.Migration):
    dependencies = [("estoque", "0001_initial")]
    operations = [migrations.RunPython(seed_unidades, unseed_unidades)]
```

---

## Architecture Patterns

### System Architecture Diagram

```
Comprador                    Solicitante/Gestor
    │                              │
    ▼                              ▼
[FornecedorForm]          [ItemEstoqueForm]
    │                              │
    │ validate CNPJ                │ FK: unidade=user.default_unit
    │ (stdnum.validate)            │
    ▼                              ▼
[Fornecedor model]         [ItemEstoque model]
    │  cnpj (14 chars)            │  quantidade_atual
    │  razao_social               │  quantidade_minima
    │  FK:CategoriaCompra         │  FK:UnidadeMedida
    │  FK:CategoriaCompra         │  FK:UnidadeOrganizacional
    │                              │
    ▼                              ▼
[PostgreSQL]               [PostgreSQL]
    │  TrigramSimilarity           │  abaixo_do_minimo annotation
    │  (pg_trgm extension)         │  select_for_update (edição)
    │                              │
    ▼                              ▼
[HTMX partial]             [HTMX partial]
    │  fornecedor_list.html        │  item_row.html
    │  (live search result)        │  (quantity update OOB)
    ▼                              ▼
Browser (swap innerHTML)   Browser (swap outerHTML)
```

### Recommended Project Structure

```
apps/
├── fornecedores/
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py          # Fornecedor(TimestampedModel)
│   ├── forms.py           # FornecedorForm — clean_cnpj via stdnum.validate
│   ├── views.py           # ListaFornecedoresView, CadastrarFornecedorView,
│   │                      # EditarFornecedorView, ToggleAtivoView
│   ├── urls.py            # namespace="fornecedores"
│   ├── admin.py           # FornecedorAdmin
│   ├── templatetags/
│   │   ├── __init__.py
│   │   └── fornecedor_tags.py   # filter: cnpj_format
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   └── __init__.py
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_models.py
│       ├── test_forms.py
│       └── test_views.py
└── estoque/
    ├── __init__.py
    ├── apps.py
    ├── models.py          # UnidadeMedida, ItemEstoque(TimestampedModel)
    ├── forms.py           # ItemEstoqueForm, AtualizarQuantidadeForm
    ├── views.py           # ListaEstoqueView, CadastrarItemView, EditarItemView,
    │                      # AtualizarQuantidadeView
    ├── urls.py            # namespace="estoque"
    ├── admin.py           # UnidadeMedidaAdmin, ItemEstoqueAdmin
    ├── migrations/
    │   ├── 0001_initial.py
    │   ├── 0002_seed_unidades.py
    │   └── __init__.py
    └── tests/
        ├── __init__.py
        ├── conftest.py
        ├── test_models.py
        ├── test_forms.py
        └── test_views.py
```

### Model Sketches

#### Fornecedor

```python
# apps/fornecedores/models.py
from django.db import models
from apps.core.models import TimestampedModel
from apps.requisicoes.models import CategoriaCompra


class Fornecedor(TimestampedModel):
    cnpj = models.CharField(max_length=14, unique=True)
    razao_social = models.CharField(max_length=200)
    email = models.EmailField()
    telefone = models.CharField(max_length=20, blank=True, default="")
    categoria = models.ForeignKey(
        CategoriaCompra,
        on_delete=models.PROTECT,
        related_name="fornecedores",
    )
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Fornecedor"
        verbose_name_plural = "Fornecedores"
        ordering = ["razao_social"]

    def __str__(self):
        return self.razao_social
```

**Nota sobre `telefone`:** `blank=True, default=""` — telefone é útil mas nem sempre disponível
no cadastro inicial. A fase não especifica obrigatoriedade; sugestão: opcional.

#### ItemEstoque

```python
# apps/estoque/models.py
from django.db import models
from apps.core.models import TimestampedModel
from apps.accounts.models import UnidadeOrganizacional


class UnidadeMedida(models.Model):
    nome = models.CharField(max_length=50, unique=True)
    sigla = models.CharField(max_length=10, unique=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "Unidade de Medida"
        verbose_name_plural = "Unidades de Medida"

    def __str__(self):
        return f"{self.nome} ({self.sigla})"


class ItemEstoque(TimestampedModel):
    nome = models.CharField(max_length=200)
    unidade_medida = models.ForeignKey(
        UnidadeMedida,
        on_delete=models.PROTECT,
        related_name="itens_estoque",
    )
    quantidade_atual = models.DecimalField(max_digits=12, decimal_places=3)
    quantidade_minima = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    unidade_organizacional = models.ForeignKey(
        UnidadeOrganizacional,
        on_delete=models.PROTECT,
        related_name="itens_estoque",
    )

    class Meta:
        verbose_name = "Item de Estoque"
        verbose_name_plural = "Itens de Estoque"
        ordering = ["nome"]
        # Impede nomes duplicados dentro da mesma unidade
        unique_together = [["nome", "unidade_organizacional"]]

    def __str__(self):
        return f"{self.nome} ({self.unidade_organizacional})"

    @property
    def abaixo_do_minimo(self) -> bool:
        """EST-04 — True se quantidade_atual < quantidade_minima."""
        return self.quantidade_atual < self.quantidade_minima
```

**Por que `DecimalField(decimal_places=3)` para quantidade:**
- Itens como "Litro" ou "Metro" têm frações (0.500 L, 1.250 m)
- `IntegerField` quebra esses casos
- `decimal_places=3` cobre a maioria dos casos de uso sem overkill

**`unique_together` em nome + unidade:**
- Evita `"Papel A4"` duplicado na mesma unidade
- Não impede o mesmo nome em unidades distintas (EST-05)

---

## CompradorRequiredMixin — Padrão a criar

[VERIFIED: apps/aprovacoes/views.py — GestorRequiredMixin e DiretorRequiredMixin existentes]

`CompradorRequiredMixin` não existe ainda. Deve ser criado seguindo o padrão das fases anteriores:

```python
# apps/fornecedores/views.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class CompradorRequiredMixin(LoginRequiredMixin):
    """Restringe acesso a usuários com role='comprador', 'admin' ou is_superuser."""

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

**Decisão sobre onde colocar o Mixin:**
- Opção A: definir em `apps/fornecedores/views.py` (padrão das fases anteriores — cada app define o próprio)
- Opção B: mover todos os mixins para `apps/core/` como `apps/core/mixins.py`

Recomendação: Opção A por consistência com Fase 2 (`GestorRequiredMixin` em `apps/aprovacoes/views.py`).
Se a Fase 4 precisar de `CompradorRequiredMixin`, poderá importar de `apps/fornecedores/views.py`
ou duplicar. A refatoração para `apps/core/mixins.py` é candidata a v2.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CNPJ validation | Regex manual (`^\d{14}$` + módulo 11) | `stdnum.br.cnpj.validate()` | Algoritmo do dígito verificador tem edge cases (CNPJ com todos dígitos iguais é inválido); formato alfanumérico impossível de manter manualmente |
| CNPJ formatting | f-string com slicing | `stdnum.br.cnpj.format()` | Funciona com ambos os formatos; sem manutenção |
| Fuzzy search | `icontains` em loop | `TrigramSimilarity` via pg_trgm | `icontains` não tolera erros de digitação; pg_trgm é indexável |
| Seed data | fixture JSON | Migration `RunPython` | Fixtures precisam ser carregadas manualmente; migration é automática no deploy |
| Concurrent write protection | `try/except IntegrityError` | `select_for_update()` | Race condition entre check e save não é coberta por IntegrityError |

---

## Common Pitfalls

### Pitfall 1: `compact()` não valida — nunca levanta exceção

**What goes wrong:** O CONTEXT.md usa `compact() + is_valid()` com `except Exception`. Isso funciona mas
`compact("texto qualquer")` retorna `"TEXTOQUALSQUER"` — uma string que não é CNPJ. Se `is_valid()` retornar
`False`, o código levanta `ValidationError` corretamente. O risco é no `except Exception` bare que pode
esconder bugs reais de programação (ex: `AttributeError` se `self.cleaned_data["cnpj"]` for `None`).

**How to avoid:** Usar `validate()` diretamente e capturar apenas `StdnumValidationError`.

**Warning signs:** `except Exception` em form `clean_*` métodos é sempre um smell.

### Pitfall 2: Query TrigramSimilarity com `q` vazio

**What goes wrong:** `qs.annotate(sim=TrigramSimilarity("razao_social", "")).filter(sim__gt=0.1)` retorna
queryset vazio (similarity com string vazia é 0 para tudo), mas gera uma query PostgreSQL desnecessária
e pode ser confuso.

**How to avoid:** Guard `if q:` antes de aplicar o annotate. Quando `q == ""`, usar `qs.order_by("razao_social")`.

### Pitfall 3: TrigramSimilarity requer pg_trgm extension

**What goes wrong:** `ProgrammingError: function similarity(character varying, unknown) does not exist at character 37`
se a extensão não estiver habilitada no banco.

**How to avoid:** Verificar se a migration de `TrigramExtension()` foi criada na Fase 1. Se não, criar
migration em `apps/fornecedores/migrations/` ou `apps/core/migrations/` antes de usar `TrigramSimilarity`.

### Pitfall 4: HTMX live search — partial retorna 404 em query vazia

**What goes wrong:** View de busca retorna 404 quando `q=""`, causando HTMX error no console e
a lista desaparece sem feedback visual.

**How to avoid:** View sempre retorna 200. Lista vazia é renderizada no template com mensagem
"Nenhum fornecedor encontrado". Nunca retornar 404 de uma endpoint de busca.

### Pitfall 5: `select_for_update()` fora de `transaction.atomic()`

**What goes wrong:** `select_for_update()` sem `with transaction.atomic():` levanta `TransactionManagementError`
no Django.

**How to avoid:** Sempre encapsular `select_for_update()` em `with transaction.atomic():` ou usar
`@transaction.atomic` no método da view. Padrão já estabelecido no CONTEXT.md (D-05).

### Pitfall 6: FK `on_delete=models.PROTECT` — mensagem de erro no Admin

**What goes wrong:** Deletar `CategoriaCompra` via Django Admin quando há fornecedores vinculados
levanta `ProtectedError` com mensagem técnica em inglês.

**How to avoid:** Adicionar `list_display` com contagem de fornecedores no `CategoriaCompra` Admin
(em `apps/requisicoes/admin.py`) para dar visibilidade antes de tentar deletar. O `PROTECT` é a
decisão correta (D-01) mas o Admin precisa comunicar isso ao usuário.

### Pitfall 7: Isolamento de estoque — `get_object_or_404` sem filtro de unidade

**What goes wrong:** `get_object_or_404(ItemEstoque, pk=pk)` — Solicitante de outra unidade pode
acessar (e editar) itens alheios via URL manipulation.

**How to avoid:** Sempre `get_object_or_404(ItemEstoque, pk=pk, unidade_organizacional=request.user.default_unit)`
nas views de Solicitante. Views de Comprador/Admin não têm esse filtro (EST-06).

### Pitfall 8: `unique_together` vs `UniqueConstraint` (Django 5.2)

**What goes wrong:** `unique_together` ainda funciona em Django 5.2 mas gera `PendingDeprecationWarning`
e não suporta condições (ex: unique apenas quando `ativo=True`).

**How to avoid:** Usar `UniqueConstraint` na `Meta`:
```python
class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=["nome", "unidade_organizacional"],
            name="unique_item_por_unidade",
        )
    ]
```

---

## Configuration Updates Required

### 1. `requirements.txt`

```
python-stdnum==2.2
```

### 2. `config/settings/base.py` — INSTALLED_APPS

```python
INSTALLED_APPS = [
    ...
    "apps.fornecedores",
    "apps.estoque",
]
```

### 3. `config/urls.py`

```python
urlpatterns = [
    ...
    path("fornecedores/", include("apps.fornecedores.urls")),
    path("estoque/", include("apps.estoque.urls")),
]
```

### 4. `templates/base.html` — Nav links

Substituir os `href="#"` existentes:
```html
<!-- Fornecedores — comprador + admin only (já existe no sidebar) -->
<a href="{% url 'fornecedores:lista' %}" ...>Fornecedores</a>

<!-- Estoque — visible to all roles (novo item) -->
<a href="{% url 'estoque:lista' %}" ...>Estoque</a>
```

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-django |
| Config file | `pytest.ini` (existe, aponta para `config.settings.dev`) |
| Quick run command | `pytest apps/fornecedores/ apps/estoque/ -q` |
| Full suite command | `pytest -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FORN-01 | Fornecedor salvo com campos corretos | unit (model) | `pytest apps/fornecedores/tests/test_models.py -x` | Wave 0 |
| FORN-02 | `clean_cnpj()` valida formatos válidos e rejeita inválidos | unit (form) | `pytest apps/fornecedores/tests/test_forms.py -x` | Wave 0 |
| FORN-02 | Alphanumeric CNPJ (ex: `12ABC34501DE35`) passa validação | unit (form) | `pytest apps/fornecedores/tests/test_forms.py::test_cnpj_alfanumerico -x` | Wave 0 |
| FORN-03 | FK para CategoriaCompra — PROTECT ao deletar categoria | unit (model) | `pytest apps/fornecedores/tests/test_models.py::test_categoria_protegida -x` | Wave 0 |
| FORN-04 | Toggle ativo não deleta fornecedor — histórico preservado | unit (view) | `pytest apps/fornecedores/tests/test_views.py::test_toggle_ativo -x` | Wave 0 |
| FORN-05 | Busca por nome retorna resultado fuzzy | integration (view) | `pytest apps/fornecedores/tests/test_views.py::test_busca_fuzzy -x` | Wave 0 |
| FORN-05 | Busca por CNPJ retorna match exato | integration (view) | `pytest apps/fornecedores/tests/test_views.py::test_busca_cnpj -x` | Wave 0 |
| EST-01 | ItemEstoque criado com unidade_organizacional do usuário | unit (view) | `pytest apps/estoque/tests/test_views.py::test_criar_item -x` | Wave 0 |
| EST-02 | quantidade_minima salva corretamente | unit (model) | `pytest apps/estoque/tests/test_models.py -x` | Wave 0 |
| EST-03 | Atualização com select_for_update — sem race condition | unit (view) | `pytest apps/estoque/tests/test_views.py::test_atualizar_quantidade -x` | Wave 0 |
| EST-04 | `abaixo_do_minimo` retorna True quando qty < min | unit (property) | `pytest apps/estoque/tests/test_models.py::test_abaixo_do_minimo -x` | Wave 0 |
| EST-05 | Solicitante não acessa item de outra unidade | integration (security) | `pytest apps/estoque/tests/test_views.py::test_isolamento_unidade -x` | Wave 0 |
| EST-06 | Comprador vê itens de todas as unidades | integration (view) | `pytest apps/estoque/tests/test_views.py::test_visao_consolidada -x` | Wave 0 |

### Sampling Rate
- **Por task commit:** `pytest apps/fornecedores/ apps/estoque/ -q --tb=short`
- **Por wave merge:** `pytest -q`
- **Phase gate:** Full suite green antes de `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `apps/fornecedores/tests/__init__.py`
- [ ] `apps/fornecedores/tests/conftest.py` — fixtures: `comprador_user`, `fornecedor`, `categoria`
- [ ] `apps/fornecedores/tests/test_models.py`
- [ ] `apps/fornecedores/tests/test_forms.py`
- [ ] `apps/fornecedores/tests/test_views.py`
- [ ] `apps/estoque/tests/__init__.py`
- [ ] `apps/estoque/tests/conftest.py` — fixtures: `solicitante_user`, `unidade_medida`, `item_estoque`
- [ ] `apps/estoque/tests/test_models.py`
- [ ] `apps/estoque/tests/test_forms.py`
- [ ] `apps/estoque/tests/test_views.py`
- [ ] Framework install: nenhum — pytest + pytest-django já em `requirements-dev.txt`

---

## Security Domain

`security_enforcement: true`, `security_asvs_level: 1`

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (all views) | `LoginRequiredMixin` herdado por todos os mixins |
| V3 Session Management | yes | Django session padrão — já configurado nas fases anteriores |
| V4 Access Control | yes | `CompradorRequiredMixin` para fornecedores; isolamento de unidade via queryset filtrado em estoque |
| V5 Input Validation | yes | `stdnum.br.cnpj.validate()` no form; `DecimalField` para quantidades |
| V6 Cryptography | no | Nenhum dado criptografado nesta fase |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| IDOR em itens de estoque | Tampering/Info Disclosure | `get_object_or_404(ItemEstoque, pk=pk, unidade_organizacional=user.default_unit)` — nunca só `pk` |
| CNPJ injection (SQL via CNPJ field) | Tampering | ORM parameterizado; `validate()` garante formato `^[\dA-Z]+$` antes de salvar |
| Comprador acessando estoque alheio via URL | Elevation of Privilege | Views de estoque do Solicitante filtram por `default_unit`; Comprador tem acesso explícito (EST-06) |
| Toggle ativo via GET (CSRF bypass) | Tampering | `ToggleAtivoView` só aceita `POST`; `View.http_method_not_allowed` para GET |
| pg_trgm DoS via query muito longa | Denial of Service | Truncar `q` a 100 chars antes de passar ao ORM: `q = q[:100]` |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `unique_together` no Meta | `UniqueConstraint` em `Meta.constraints` | Django 4.0+ (deprecation warning em 5.x) | Usar `UniqueConstraint` — suporta condições e não gera warning |
| `compact() + is_valid()` | `validate()` retorna compact | python-stdnum 1.x | `validate()` é a API recomendada desde versões antigas; mais explícita |
| `hx-trigger="keyup delay:300ms"` | `hx-trigger="input delay:300ms, search"` | HTMX 2.0 | `input` captura paste/cut além de teclado; `search` captura o clear button |

**Deprecated/outdated:**
- `unique_together`: funciona mas deprecado em favor de `UniqueConstraint`
- `except Exception` bare em `clean_*` forms: antipadrão — esconde bugs de programação

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Threshold `sim__gt=0.1` é adequado para nomes de fornecedores em português | pg_trgm | Resultado pode ser muito amplo (> 100 itens) para buscas de 1-2 chars; mitigação: exigir `len(q) >= 2` para ativar fuzzy |
| A2 | `telefone` é opcional (não especificado nos requisitos) | Model Fornecedor | Se cliente exigir obrigatório, remover `blank=True, default=""` |
| A3 | `CompradorRequiredMixin` deve ficar em `apps/fornecedores/views.py` (não em `apps/core/`) | Architecture | Inconsistência menor se Fase 4 precisar reimportar |
| A4 | Template filter `cnpj_format` vs. model property — filter escolhido | CNPJ Formatting | Nenhum impacto funcional; ambos funcionam |
| A5 | `decimal_places=3` para quantidades de estoque | Model ItemEstoque | Se cliente usa apenas inteiros, `IntegerField` é mais simples |

---

## Open Questions

1. **pg_trgm extension — existe na migration da Fase 1?**
   - What we know: CLAUDE.md menciona `TrigramExtension()` como recomendação
   - What's unclear: não foi possível verificar se a migration de extensão foi de fato criada na Fase 1 (as migrations de `accounts` e `aprovacoes` não mencionam extensões)
   - Recommendation: o plano deve incluir um task de verificação/criação da migration de extensão na Wave 0

2. **`telefone` obrigatório ou opcional?**
   - What we know: FORN-01 lista telefone como campo do cadastro
   - What's unclear: requisito não especifica obrigatoriedade
   - Recommendation: implementar como opcional (`blank=True`) e confirmar com cliente

3. **Estoque — `decimal_places` para quantidade**
   - What we know: itens como litros e metros têm frações; outros (caixas, unidades) são inteiros
   - What's unclear: o cliente tem itens com frações no estoque real?
   - Recommendation: usar `decimal_places=3` por segurança; se cliente confirmar "só inteiros", migrar depois é simples

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL | TrigramSimilarity, select_for_update | ✓ (Docker) | 15+ (configured) | — |
| python-stdnum | FORN-02 CNPJ validation | ✓ (PyPI 2.2) | 2.2 | — (sem alternativa aceitável) |
| pg_trgm extension | FORN-05 fuzzy search | UNKNOWN | — | Criar migration de extensão no Wave 0 |
| pytest + pytest-django | Tests | ✓ | pytest 9.0.3 | — |

**Missing dependencies with no fallback:**
- pg_trgm extension status desconhecido — verificar migrations existentes na Wave 0

**Missing dependencies with fallback:**
- Nenhuma

---

## Sources

### Primary (HIGH confidence)
- `python-stdnum` 2.2 source code + interactive REPL — `inspect.getsource()` confirmou `compact()`, `validate()`, regex `^[\dA-Z]+$`, exceções — 2026-06-11
- `pip index versions python-stdnum` — versão 2.2 confirmada como mais recente — 2026-06-11
- `python -m slopcheck install python-stdnum` — resultado [OK] — 2026-06-11
- `django.contrib.postgres.search` — `TrigramSimilarity` import confirmado via Python REPL — 2026-06-11
- `apps/aprovacoes/views.py` — padrão `GestorRequiredMixin` e `DiretorRequiredMixin` verificados — codebase atual
- `apps/core/models.py` — `TimestampedModel` e `AuditedModel` verificados — codebase atual
- `apps/requisicoes/models.py` — `CategoriaCompra` modelo verificado para FK reutilização — codebase atual
- `config/settings/base.py` — `INSTALLED_APPS`, middleware, PostgreSQL config verificados — codebase atual
- `templates/base.html` — CSRF via `htmx:configRequest`, sidebar navigation verificados — codebase atual

### Secondary (MEDIUM confidence)
- `stdnum.br.cnpj` docstring — exemplo de CNPJ alfanumérico `'12. ABC.345 /01DE-35'` → `'12ABC34501DE35'` — fonte: módulo instalado

### Tertiary (LOW confidence)
- Threshold `sim__gt=0.1` para português — do CONTEXT.md (D-03); não verificado empiricamente

---

## Metadata

**Confidence breakdown:**
- python-stdnum API: HIGH — verificado via código-fonte + REPL interativo
- TrigramSimilarity: HIGH — import confirmado via Python REPL
- HTMX live search pattern: HIGH — padrão já aplicado nas fases anteriores (base.html + aprovacoes/views.py)
- Django Admin UnidadeMedida: HIGH — padrão idêntico ao ConfiguracaoAlcada já existente
- Model sketches: MEDIUM — baseado em requisitos + convenções do projeto; detalhes como `decimal_places` são suposições
- Threshold de similaridade: LOW — valor do CONTEXT.md, não validado empiricamente

**Research date:** 2026-06-11
**Valid until:** 2026-07-11 (python-stdnum atualiza raramente; Django 5.2 é LTS)
