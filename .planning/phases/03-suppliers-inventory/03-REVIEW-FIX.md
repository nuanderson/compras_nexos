---
phase: 03-suppliers-inventory
fixed_at: 2026-06-11T12:54:00Z
review_path: .planning/phases/03-suppliers-inventory/03-REVIEW.md
iteration: 1
findings_in_scope: 7
fixed: 7
skipped: 0
status: all_fixed
---

# Fase 03: Relatório de Fix do Code Review

**Fixed at:** 2026-06-11
**Source review:** `.planning/phases/03-suppliers-inventory/03-REVIEW.md`
**Iteration:** 1

**Sumário:**
- Findings em escopo: 7 (3 Critical + 4 Warning)
- Corrigidos: 7
- Ignorados: 0

Todos os 54 testes passaram após as correções: `54 passed, 25 warnings`.

---

## Issues Corrigidos

### CR-01: `hx-get` em `lista.html` para view que só aceita POST

**Arquivos modificados:** `templates/estoque/lista.html`
**Commit:** e2318c3
**Correção aplicada:** Substituído o loop `{% for item in itens %}` que renderizava um `<tr>` com botão `hx-get` por `{% include "estoque/partials/item_row.html" %}`. O `item_row.html` já continha o formulário correto com `hx-post`, `{% csrf_token %}` e `hx-swap="outerHTML"`. O `<div id="quantidade-modal">` foi removido pois não é mais necessário. Isso elimina o HTTP 405 e reutiliza o partial já existente e correto.

---

### CR-02: Comprador com `default_unit=None` não consegue atualizar quantidades

**Arquivos modificados:** `apps/estoque/views.py`
**Commit:** 3c67ebd
**Correção aplicada:** Adicionada guarda de role em `AtualizarQuantidadeView.post()` seguindo o mesmo padrão de `ListaEstoqueView` e `EditarItemEstoqueView`: se `user.is_superuser` ou `user.role in ("comprador", "admin")`, busca o item sem filtro de unidade; caso contrário filtra por `unidade_organizacional=user.default_unit`.

---

### CR-03: Testes de `fornecedores` sem `@pytest.mark.django_db`

**Arquivos modificados:** `apps/fornecedores/tests/test_views.py`, `apps/fornecedores/tests/test_models.py`
**Commit:** 6bcc059
**Correção aplicada:** Adicionado `@pytest.mark.django_db` nas classes `TestListaFornecedoresView`, `TestCadastrarFornecedorView`, `TestToggleAtivoView` (em `test_views.py`) e `TestFornecedorModel`, `TestFornecedorCategoriaProtect` (em `test_models.py`). `TestCnpjFormatFilter` não foi alterada — testa apenas lógica pura sem acesso ao banco.

---

### WR-01: `ItemEstoqueForm` sem validação de quantidade negativa

**Arquivos modificados:** `apps/estoque/forms.py`
**Commit:** 0fc1f8c
**Correção aplicada:** Adicionados métodos `clean_quantidade_atual()` e `clean_quantidade_minima()` em `ItemEstoqueForm` que levantam `ValidationError` se o valor for negativo. Segue o mesmo padrão já existente em `AtualizarQuantidadeForm`.

---

### WR-02: Toggle HTMX sem CSRF explícito no `fornecedor_row.html`

**Arquivos modificados:** `templates/fornecedores/partials/fornecedor_row.html`
**Commit:** 37e5930
**Correção aplicada:** O botão de toggle foi envolvido em um `<form method="post">` inline com `{% csrf_token %}` explícito. Os atributos HTMX (`hx-post`, `hx-target`, `hx-swap`, `hx-confirm`) foram movidos para o `<form>`, e o `<button>` passou a ser `type="submit"`. Isso elimina a dependência implícita do listener global de `base.html` para que o CSRF funcione.

---

### WR-03: `save(update_fields=["ativo"])` não atualiza `atualizado_em`

**Arquivos modificados:** `apps/fornecedores/views.py`
**Commit:** 2953552
**Correção aplicada:** Incluído `"atualizado_em"` em `update_fields` em `ToggleAtivoView.post()`. O campo correto no `TimestampedModel` é `atualizado_em` (não `updated_at` como referenciado no REVIEW.md) — verificado em `apps/core/models.py`.

---

### WR-04: Fornecedores inativos aparecem nos resultados de busca

**Arquivos modificados:** `apps/fornecedores/views.py`
**Commit:** 5464898
**Correção aplicada:** Adicionado `.filter(ativo=True)` no queryset base de `get_queryset_fornecedores()`. A listagem de gestão (onde inativos precisam aparecer para operações administrativas de toggle) pode ser implementada em uma view separada em fase futura se necessário.

---

## Issues Ignorados

Nenhum — todos os 7 findings em escopo foram corrigidos.

---

_Corrigido: 2026-06-11_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
