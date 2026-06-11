---
phase: "03"
phase_name: "Suppliers & Inventory"
status: "discussed"
discussed_on: "2026-06-11"
requirements: "FORN-01..05, EST-01..06"
---

# Phase 03 Context: Fornecedores & Estoque

## Requirements scope

| Req | Description |
|-----|-------------|
| FORN-01 | Comprador cadastra fornecedores: CNPJ, razão social, e-mail, telefone |
| FORN-02 | Validação CNPJ via `python-stdnum` (suporta formato alfanumérico jul/2026) |
| FORN-03 | Fornecedores organizados por categorias configuráveis |
| FORN-04 | Ativar/inativar fornecedor sem perder histórico |
| FORN-05 | Busca e filtro por nome, CNPJ ou categoria |
| EST-01 | Solicitante cadastra itens de estoque da unidade: nome, unidade de medida, quantidade atual |
| EST-02 | Solicitante define quantidade mínima (ponto de pedido) |
| EST-03 | Solicitante atualiza quantidades manualmente |
| EST-04 | Sistema destaca itens abaixo do mínimo |
| EST-05 | Cada unidade vê apenas o próprio estoque |
| EST-06 | Comprador e Admin têm visão consolidada de todas as unidades |

---

## Decisions

### D-01 — Categorias de fornecedores: reusar CategoriaCompra

**Decision:** Fornecedor usa FK para `CategoriaCompra` (já existente em `apps/requisicoes`).

**Rationale:** O cliente aprovou reuso. Zero migrações extras. A lista de categorias serve igualmente para
requisições e fornecedores no v1. Se as listas precisarem divergir em v2, basta adicionar um flag ou um
modelo separado naquele momento.

**Implementation:**
```python
# apps/fornecedores/models.py
from apps.requisicoes.models import CategoriaCompra

class Fornecedor(TimestampedModel):
    categoria = models.ForeignKey(
        CategoriaCompra, on_delete=models.PROTECT, related_name="fornecedores"
    )
```

**Constraints:**
- FK `PROTECT` — não deletar categoria que tem fornecedor vinculado
- `null=True, blank=True` não permitido — categoria é obrigatória no cadastro

---

### D-02 — CNPJ: armazenar compactado, validar com python-stdnum

**Decision:** Campo `cnpj = models.CharField(max_length=14, unique=True)` armazenado no formato compactado
(somente dígitos/caracteres alfanuméricos). Validar + compactar no `clean()` do form, nunca no model.

**Rationale:** `python-stdnum` (já no stack via CLAUDE.md) suporta CNPJ alfanumérico a partir de julho/2026
(Resolução Cofins 252/2026). `unique=True` no campo compactado previne duplicatas.

**Implementation:**
```python
# apps/fornecedores/forms.py
from stdnum.br import cnpj as cnpj_lib

def clean_cnpj(self):
    valor = self.cleaned_data["cnpj"]
    try:
        compactado = cnpj_lib.compact(valor)
        if not cnpj_lib.is_valid(compactado):
            raise forms.ValidationError("CNPJ inválido.")
    except Exception:
        raise forms.ValidationError("CNPJ inválido.")
    if Fornecedor.objects.filter(cnpj=compactado).exclude(pk=self.instance.pk).exists():
        raise forms.ValidationError("Já existe um fornecedor com este CNPJ.")
    return compactado
```

---

### D-03 — Busca de fornecedores: pg_trgm fuzzy + filtro de categoria

**Decision:** Busca fuzzy via `pg_trgm` (TrigramSimilarity) no campo `razao_social` e busca exata no
campo `cnpj`. Filtro de categoria via GET param (`?categoria=<pk>`). Implementado como HTMX live search
(hx-trigger="input delay:300ms") na listagem.

**Rationale:** `pg_trgm` já está planejado no CLAUDE.md e na migration da Fase 1. Tolerância a erros
de digitação é crítica para nomes de fornecedores. Busca por CNPJ é exata (campo compactado).

**Implementation:**
```python
# apps/fornecedores/views.py
from django.contrib.postgres.search import TrigramSimilarity

qs = Fornecedor.objects.annotate(
    sim=TrigramSimilarity("razao_social", q)
).filter(sim__gt=0.1).order_by("-sim")
```

---

### D-04 — Unidade de medida do estoque: modelo configurável pelo Admin

**Decision:** Criar modelo `UnidadeMedida` em `apps/estoque` com campos `nome` (CharField) e `sigla`
(CharField, ex: "kg", "un", "cx"). FK em `ItemEstoque`. Cadastro via Django Admin.

**Rationale:** O cliente escolheu flexibilidade — lista editável pelo Admin sem deploy. Seed inicial
com as unidades mais comuns (UN, KG, CX, L, M, PAR) gerado via migration `0002_seed_unidades.py`.

**Model:**
```python
class UnidadeMedida(models.Model):
    nome = models.CharField(max_length=50, unique=True)  # ex: "Unidade"
    sigla = models.CharField(max_length=10, unique=True)  # ex: "un"
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} ({self.sigla})"
```

**Seed data (migration):**
`UN (Unidade), KG (Quilograma), CX (Caixa), L (Litro), M (Metro), PAR (Par), PCT (Pacote), RES (Resma)`

---

### D-05 — Atualização de estoque: edição direta do campo quantidade

**Decision:** `POST /estoque/<pk>/editar/` recebe `quantidade_atual` como campo numérico. O valor
substitui o anterior diretamente. Sem lógica de delta (v1). Histórico de movimentações é v2 (EST-V2-01).

**Rationale:** O cliente aprovou edição direta. Para 20 usuários internos, o controle visual basta.
`select_for_update()` protege contra edições concorrentes.

**Implementation pattern:**
```python
# apps/estoque/views.py
with transaction.atomic():
    item = ItemEstoque.objects.select_for_update().get(pk=pk, unidade=request.user.default_unit)
    form = AtualizarQuantidadeForm(request.POST, instance=item)
    if form.is_valid():
        form.save()
        # retorna partial atualizada (HTMX)
```

---

### D-06 — Isolamento de estoque por unidade

**Decision:** `ItemEstoque` tem FK para `UnidadeOrganizacional`. Views de Solicitante/Gestor filtram
por `unidade=request.user.default_unit`. Views de Comprador/Admin listam sem filtro de unidade.

**Segurança:** `get_object_or_404(ItemEstoque, pk=pk, unidade=request.user.default_unit)` em toda
ação de Solicitante — nunca expõe itens de outras unidades.

---

## Deferred (out of scope for Phase 3)

| Item | Deferred to |
|------|-------------|
| Histórico de movimentações de estoque | v2 (EST-V2-01) |
| Avaliação de fornecedor após compra | v2 (FORN-V2-01) |
| Alerta automático de estoque baixo gera sugestão de requisição | v2 (EST-V2-02) |
| Many-to-many categorias por fornecedor | v2 se necessário |

---

## App structure

```
apps/
  fornecedores/
    models.py        # Fornecedor(TimestampedModel) — cnpj, razao_social, email, telefone, categoria, ativo
    forms.py         # FornecedorForm — validação CNPJ via python-stdnum
    views.py         # ListaFornecedoresView, CadastrarFornecedorView, EditarFornecedorView, ToggleAtivoView
    urls.py          # namespace=fornecedores
    admin.py         # FornecedorAdmin
    tests/
  estoque/
    models.py        # UnidadeMedida, ItemEstoque(TimestampedModel)
    forms.py         # ItemEstoqueForm, AtualizarQuantidadeForm
    views.py         # ListaEstoqueView, CadastrarItemView, EditarItemView, AtualizarQuantidadeView
    urls.py          # namespace=estoque
    admin.py         # UnidadeMedidaAdmin, ItemEstoqueAdmin
    tests/
```

---

## Constraints carried from prior phases

- `TimestampedModel` em `apps/core/models.py` — herdar para auditoria automática
- `LoginRequiredMixin` em todas as views
- HTMX CSRF via `hx-headers` no `<body>` do `base.html`
- Service layer para qualquer lógica além de CRUD simples (ex: toggle ativo)
- `transaction.atomic()` + `select_for_update()` em toda escrita concorrente
- Dark theme: `#1a1a2e` (página), `#16213e` (cards), `#e94560` (accent)
- Permissões: `CompradorRequiredMixin` (role in comprador, admin ou superuser) para views de fornecedor
- Permissões: Solicitante e Gestor gerenciam estoque da própria unidade; Comprador/Admin têm visão consolidada
