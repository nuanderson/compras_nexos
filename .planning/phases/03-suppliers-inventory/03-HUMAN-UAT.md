---
status: partial
phase: 03-suppliers-inventory
source: [03-VERIFICATION.md]
started: 2026-06-11T12:00:00Z
updated: 2026-06-11T12:00:00Z
---

## Current Test

Verificação automática completa (11/11). Itens abaixo requerem teste no navegador.

Acesse: http://localhost:8002

## Tests

### 1. Busca fuzzy de fornecedores (FORN-05)
expected: Campo de busca atualiza a lista dinamicamente (sem reload) ao digitar nome ou CNPJ. Busca fuzzy tolera erros de digitação no nome (ex: "Papelari" encontra "Papelaria X"). Filtro de categoria funciona em conjunto com a busca.
result: [pending]

### 2. Toggle ativo/inativo de fornecedor e reativação (FORN-04)
expected: Botão "Inativar" muda o fornecedor para inativo e remove-o da lista imediatamente (HTMX swap). Checkbox "Mostrar fornecedores inativos" exibe os inativos na lista. Botão "Ativar" reativa o fornecedor. Todos os históricos são preservados (nenhum dado apagado).
result: [pending]

### 3. Destaque de itens abaixo do mínimo + atualização de quantidade (EST-04, EST-03)
expected: Itens com quantidade_atual < quantidade_minima aparecem destacados em vermelho/laranja na lista. Ao atualizar a quantidade para acima do mínimo, o destaque some após o swap HTMX. Quantidades negativas são rejeitadas com mensagem de erro.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
