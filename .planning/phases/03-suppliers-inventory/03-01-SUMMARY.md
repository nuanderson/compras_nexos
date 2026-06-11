---
phase: "03"
plan: "01"
subsystem: "fornecedores"
tags: ["crud", "cnpj-validation", "htmx-live-search", "pg-trgm", "tdd"]
dependency_graph:
  requires:
    - "01-accounts (TimestampedModel, User.Role)"
    - "01-requisicoes (CategoriaCompra)"
  provides:
    - "apps.fornecedores (Fornecedor model)"
    - "FornecedorForm com validação CNPJ"
    - "CompradorRequiredMixin"
    - "cnpj_format template filter"
    - "HTMX live search em /fornecedores/"
  affects:
    - "config/settings/base.py (INSTALLED_APPS)"
    - "config/urls.py"
    - "templates/base.html (nav link Fornecedores)"
tech_stack:
  added:
    - "python-stdnum==2.2 (validação CNPJ numérico e alfanumérico Jul/2026)"
  patterns:
    - "CompradorRequiredMixin (padrão GestorRequiredMixin de aprovacoes)"
    - "TrigramSimilarity + busca exata CNPJ (pg_trgm já habilitado em accounts/0001_initial.py)"
    - "Template filter cnpj_format via stdnum.br.cnpj.format()"
    - "HTMX outerHTML swap para toggle ativo"
    - "hx-trigger=input delay:300ms + search para live search"
key_files:
  created:
    - "apps/fornecedores/models.py"
    - "apps/fornecedores/forms.py"
    - "apps/fornecedores/views.py"
    - "apps/fornecedores/urls.py"
    - "apps/fornecedores/admin.py"
    - "apps/fornecedores/apps.py"
    - "apps/fornecedores/templatetags/fornecedor_tags.py"
    - "apps/fornecedores/migrations/0001_initial.py"
    - "apps/fornecedores/tests/conftest.py"
    - "apps/fornecedores/tests/test_models.py"
    - "apps/fornecedores/tests/test_forms.py"
    - "apps/fornecedores/tests/test_views.py"
    - "templates/fornecedores/lista.html"
    - "templates/fornecedores/form.html"
    - "templates/fornecedores/partials/fornecedor_list.html"
    - "templates/fornecedores/partials/fornecedor_row.html"
  modified:
    - "requirements.txt (python-stdnum==2.2)"
    - "config/settings/base.py (INSTALLED_APPS)"
    - "config/urls.py (path fornecedores/)"
    - "templates/base.html (nav link Fornecedores atualizado)"
decisions:
  - "cnpj CharField(max_length=20) no form para aceitar entrada formatada antes do clean_cnpj (Desvio Rule 1)"
  - "stdnum.validate() como API principal — não compact()+is_valid() (conforme RESEARCH.md)"
  - "CompradorRequiredMixin definido em apps/fornecedores/views.py por consistência com Fase 2 (Opção A do RESEARCH.md)"
  - "Template filter cnpj_format — não model property (conforme RESEARCH.md recomendação)"
metrics:
  duration: "~45 min"
  completed: "2026-06-11"
  tasks_completed: 2
  tasks_total: 2
  files_created: 16
  files_modified: 4
  tests_added: 29
---

# Phase 03 Plan 01: Scaffold do app fornecedores — modelo, formulário, views e templates

## Summary

App `apps.fornecedores` completo com Fornecedor(TimestampedModel), validação CNPJ via `stdnum.validate()` suportando formato alfanumérico Jul/2026, busca fuzzy pg_trgm + exata por CNPJ, toggle ativo HTMX outerHTML, 29 testes verdes.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Testes modelo e formulário | 159d7b1 | test_models.py, test_forms.py |
| 1 (GREEN) | Scaffold: modelo, formulário, migração | 45cf5ec | models.py, forms.py, admin.py, migrations/0001, templatetags, requirements.txt, settings, urls |
| 2 (RED) | Testes views | 8b31d5f | conftest.py, test_views.py |
| 2 (GREEN) | Views, URLs e templates | 521ea75 | views.py, urls.py, lista.html, form.html, partials/* |

## Test Results

```
29 passed, 0 failures
apps/fornecedores/tests/test_models.py  — 7 testes (FORN-01, FORN-02 alfanumérico, FORN-03, cnpj_format)
apps/fornecedores/tests/test_forms.py   — 6 testes (clean_cnpj, unicidade, edição própria)
apps/fornecedores/tests/test_views.py   — 13 testes (403/200, HTMX partial, toggle, cadastro)
apps/fornecedores/tests/conftest.py     — 6 fixtures
```

## Success Criteria Verification

- [x] python-stdnum==2.2 está em requirements.txt
- [x] "apps.fornecedores" está em INSTALLED_APPS
- [x] Migration 0001_initial.py existe e é válida (`manage.py migrate --check` OK)
- [x] pytest apps/fornecedores/ passa (29 testes verde)
- [x] CNPJ alfanumérico "12ABC34501DE35" é aceito pelo FornecedorForm
- [x] CNPJ "00000000000000" é rejeitado com mensagem de erro
- [x] Busca fuzzy por nome retorna fornecedores similares (TrigramSimilarity)
- [x] Toggle ativo via POST HTMX atualiza o campo sem reload

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Campo CNPJ no form rejeitava input formatado por max_length=14**

- **Found during:** Task 1 (RED phase)
- **Issue:** `ModelForm` herda `max_length=14` do campo `Fornecedor.cnpj`, mas o usuário digita "11.222.333/0001-81" (18 chars com formatação). A validação de max_length ocorre ANTES do `clean_cnpj()` compactar o valor.
- **Fix:** Sobrescrever o campo `cnpj` no `FornecedorForm` com `forms.CharField(max_length=20)` para aceitar entrada formatada. O `clean_cnpj()` ainda compacta para 14 chars antes de salvar.
- **Files modified:** `apps/fornecedores/forms.py`
- **Commit:** 45cf5ec

**2. [Rule 1 - Bug] CNPJ de teste inválido em test_views.py**

- **Found during:** Task 2 (GREEN phase) — primeiro ciclo
- **Issue:** O CNPJ "45.678.904/0001-50" usado no teste `test_cadastrar_fornecedor_valido_cria_e_redireciona` falhou na validação `stdnum.validate()` (dígito verificador incorreto).
- **Fix:** Substituído por "07.526.557/0001-00" (CNPJ válido verificado interativamente).
- **Files modified:** `apps/fornecedores/tests/test_views.py`
- **Commit:** 521ea75

## TDD Gate Compliance

- [x] RED gate: `test(03-01): adicionar testes RED para modelo e formulário de fornecedor` (159d7b1)
- [x] GREEN gate: `feat(03-01): scaffold do app fornecedores — modelo, formulário e migração` (45cf5ec)
- [x] RED gate (Task 2): `test(03-01): adicionar testes RED para views de fornecedores` (8b31d5f)
- [x] GREEN gate (Task 2): `feat(03-01): views, URLs e templates de fornecedores` (521ea75)

## Known Stubs

Nenhum — todos os dados são carregados do banco de dados real via queryset.

## Threat Flags

Nenhum novo surface não coberto pelo threat model do plano.
Todas as mitigações do threat register implementadas:
- T-03-01: CompradorRequiredMixin em todas as views (/fornecedores/*)
- T-03-02: ToggleAtivoView aceita apenas POST (GET retorna 405)
- T-03-03: stdnum.validate() garante formato ^[\dA-Z]+$ + ORM parameterizado
- T-03-04: q truncado a 100 chars em get_queryset_fornecedores()

## Self-Check: PASSED
