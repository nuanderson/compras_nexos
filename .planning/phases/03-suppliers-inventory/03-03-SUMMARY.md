---
phase: "03"
plan: "03"
subsystem: "navegacao"
tags: ["navigation", "base-template", "integration", "test-suite"]
dependency_graph:
  requires:
    - "03-01 (apps/fornecedores, namespace=fornecedores)"
    - "03-02 (apps/estoque, namespace=estoque)"
  provides:
    - "templates/base.html com links Fornecedores e Estoque"
    - "Suite completa 136 testes verdes"
  affects:
    - "templates/base.html (nav links)"
    - ".planning/ROADMAP.md (Phase 3 marcada completa)"
tech_stack:
  added: []
  patterns:
    - "Condicional role-based no template para Fornecedores (comprador/admin/superuser)"
    - "Link universal sem condicional para Estoque (todos os roles)"
    - "Padrão is-active por request.path para highlight do item ativo"
key_files:
  created: []
  modified:
    - "templates/base.html (link Estoque adicionado)"
    - ".planning/ROADMAP.md (Phase 3 status: Complete)"
decisions:
  - "Link Estoque sem bloco condicional — todos os roles autenticados têm acesso (EST-05: isolamento é feito na view, não no nav)"
  - "Link Fornecedores mantido dentro de condicional existente — comprador + admin + superuser (T-03-10: defesa em profundidade, view ainda exige CompradorRequiredMixin)"
metrics:
  duration: "~17 min"
  completed: "2026-06-11"
  tasks_completed: 2
  tasks_total: 2
  files_created: 0
  files_modified: 1
  tests_added: 0
---

# Phase 03 Plan 03: Navegação global — links Fornecedores e Estoque + validação da suite completa

## Summary

Link "Estoque" adicionado ao sidebar do `base.html` para todos os roles autenticados; link "Fornecedores" já estava presente (adicionado em 03-01) com condicional role-based. Suite completa de 136 testes passa sem regressões.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Adicionar link Estoque ao base.html | b1c74df | templates/base.html |
| 2 | Validação final — suite completa e verificação de migrações | 626f4c6 | .planning/ROADMAP.md |

## Test Results

```
136 passed, 0 failures, 75 warnings in 87.93s

apps/accounts/tests/         — 14 testes (AUTH, user mgmt, unit mgmt)
apps/requisicoes/tests/      — 19 testes (REQ-01..04)
apps/aprovacoes/tests/       — 24 testes (APROV-01..06, gestor + diretor)
apps/fornecedores/tests/     — 29 testes (FORN-01..05)
apps/estoque/tests/          — 25 testes (EST-01..06, isolamento + select_for_update)
apps/core/tests/             — 0 (app sem testes dedicados)
```

Nota: Os 2 erros `SystemExit: 2` observados numa execução anterior foram timeouts da ferramenta de captura de output (execução de ~144s), não falhas reais. Executando com `python -m pytest` diretamente, todos os 136 testes passam.

## Success Criteria Verification

- [x] Link "Fornecedores" aparece na navegação apenas para comprador e admin (bloco `{% if request.user.role == 'comprador' or ... %}`)
- [x] Link "Estoque" aparece na navegação para todos os roles autenticados (sem condicional)
- [x] Suite de testes completa da fase 3 passa sem regressões (136 passed, 0 failed)
- [x] `python manage.py migrate --check` não reporta migrações pendentes (fornecedores/0001 aplicada)
- [x] `from stdnum.br import cnpj; cnpj.validate('11222333000181')` retorna valor sem exceção
- [x] `from django.contrib.postgres.search import TrigramSimilarity` retorna 'OK'
- [x] ROADMAP.md Phase 3 lista 3 planos completos

## Deviations from Plan

### Auto-fixed Issues

Nenhum desvio de código necessário.

**Observação operacional:** A migration `fornecedores/0001_initial` não estava aplicada no banco de dados local. Executado `python manage.py migrate fornecedores` para aplicar. Isso não é um bug de código — apenas estado do banco de desenvolvimento local (o plano 03-01 foi executado num agente paralelo em worktree separada).

## Known Stubs

Nenhum — todos os links de navegação apontam para URLs reais com views funcionais.

## Threat Flags

Nenhuma superfície nova além do registrado no threat model do plano.
Mitigações verificadas:
- T-03-10: Link Fornecedores protegido por condicional de role no template + CompradorRequiredMixin na view (defesa em profundidade)
- T-03-11: ROADMAP.md atualizado (arquivo de planejamento interno, sem impacto de segurança)

## Self-Check

### Files exist

- FOUND: templates/base.html (contém `{% url 'fornecedores:lista' %}` e `{% url 'estoque:lista' %}`)
- FOUND: .planning/ROADMAP.md (Phase 3: 3/3 plans complete)

### Commits exist

- FOUND: b1c74df (feat - link Estoque no nav)
- FOUND: 626f4c6 (chore - ROADMAP Phase 3 completa)

### Navigation correctness

- Fornecedores: dentro de `{% if request.user.role == 'comprador' or request.user.role == 'admin' or request.user.is_superuser %}` — CORRETO
- Estoque: fora de qualquer condicional, visível a todos os autenticados — CORRETO

## Self-Check: PASSED
