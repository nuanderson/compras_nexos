---
phase: "02-requisitions-approvals"
plan: "04"
subsystem: diretor-slice
tags: [django, views, htmx, templates, tdd, aprovacoes, diretor]
dependency_graph:
  requires:
    - aprovacoes.services.aprovar_diretor — Plan 02-02
    - aprovacoes.services.reprovar_requisicao — Plan 02-02
    - aprovacoes.ReprovaForm — Plan 02-03
    - aprovacoes.GestorRequiredMixin (padrão replicado) — Plan 02-03
    - aprovacoes.urls (rotas do Gestor preservadas) — Plan 02-03
  provides:
    - aprovacoes.views: DiretorRequiredMixin, FilaDiretorView, AprovarDiretorView, ModalReprovarDiretorView, ReprovarDiretorView
    - aprovacoes.urls: 4 rotas do Diretor (fila-diretor, aprovar-diretor, modal-reprovar-diretor, reprovar-diretor)
    - templates: fila_diretor.html, partials/fila_diretor_row.html, partials/modal_reprovar_diretor.html
    - Fluxo de aprovação de 2 níveis completo end-to-end
  affects:
    - Fase completa: APROV-01..APROV-05, REQ-04 todos satisfeitos
tech_stack:
  added: []
  patterns:
    - DiretorRequiredMixin replicando GestorRequiredMixin (role in diretor/admin ou superuser)
    - FilaDiretorView sem filtro de unidade (D-06 — Diretor vê todas as unidades)
    - Mesmo padrão HTMX outerHTML swap para remover linhas da fila
    - ReprovaForm reutilizado do Plano 03 (sem duplicação)
    - Estado terminal REPROVADO → apovar_diretor levanta ValueError → 409 (D-13)
key_files:
  created:
    - apps/aprovacoes/templates/aprovacoes/fila_diretor.html
    - apps/aprovacoes/templates/aprovacoes/partials/fila_diretor_row.html
    - apps/aprovacoes/templates/aprovacoes/partials/modal_reprovar_diretor.html
    - apps/aprovacoes/tests/test_views_diretor.py
  modified:
    - apps/aprovacoes/views.py (4 views do Diretor adicionadas)
    - apps/aprovacoes/urls.py (4 rotas do Diretor adicionadas)
    - templates/base.html (nav "Aprovações (Diretoria)" para diretor/admin)
decisions:
  - "FilaDiretorView sem filtro de unidade — Diretor vê PENDENTE_DIRETOR de todas as unidades (D-06)"
  - "DiretorRequiredMixin bloqueia Gestor/Solicitante (role in diretor/admin ou superuser)"
  - "ReprovaForm reutilizado do Plano 03 — sem duplicação de validação"
  - "Estado terminal D-13: aprovar requisição REPROVADA → ValueError no service → 409"
metrics:
  duration_minutes: 22
  completed_date: "2026-06-10"
  tasks_completed: 1
  tasks_total: 1
  files_created: 4
  files_modified: 3
---

# Phase 02 Plan 04: Slice Vertical do Diretor — Fila 2º Nível Summary

**One-liner:** Fila do Diretor (todas as unidades) com aprovar → APROVADO e reprovar → REPROVADO permanente via modal HTMX; `DiretorRequiredMixin` bloqueando demais perfis; 10 testes verdes; fluxo de aprovação de 2 níveis completo end-to-end.

## What Was Built

### Views do Diretor (`apps/aprovacoes/views.py`)

- **DiretorRequiredMixin**: role in (diretor, admin) ou `is_superuser` — bloqueia Gestor e Solicitante com 403.
- **FilaDiretorView**: filtra `status=PENDENTE_DIRETOR` SEM filtro de unidade (D-06). Diretor vê requisições de todas as unidades. Ordenação FIFO por `criado_em`.
- **AprovarDiretorView**: POST → `services.aprovar_diretor(pk, request.user)` → APROVADO terminal. ValueError (estado inválido, incluindo REPROVADO permanente) → 409.
- **ModalReprovarDiretorView**: GET → renderiza `modal_reprovar_diretor.html` com `ReprovaForm` reutilizado.
- **ReprovarDiretorView**: POST com validação de motivo via `ReprovaForm`; inválido → modal com erros (sem transicionar); válido → `services.reprovar_requisicao` → REPROVADO permanente.

### URLs (`apps/aprovacoes/urls.py`)

4 rotas adicionadas preservando as 4 do Gestor (total: 8 rotas no namespace `aprovacoes`):
- `fila-diretor/` → FilaDiretorView
- `<int:pk>/aprovar-diretor/` → AprovarDiretorView
- `<int:pk>/modal-reprovar-diretor/` → ModalReprovarDiretorView
- `<int:pk>/reprovar-diretor/` → ReprovarDiretorView

### Templates

- **fila_diretor.html**: extends base; colunas Solicitante, Unidade, Descrição, Categoria, Valor Estimado, Data, Ações; estado vazio "Nenhuma requisição aguardando aprovação da diretoria"; div `#modal-container`.
- **partials/fila_diretor_row.html**: `<tr id="fila-diretor-row-{{ req.pk }}">` com botão Aprovar (hx-post + outerHTML) e Reprovar (hx-get modal para #modal-container).
- **partials/modal_reprovar_diretor.html**: `{% csrf_token %}` + `name="motivo" required` + exibição de erros; hx-post para `aprovacoes:reprovar-diretor`.

### Nav (`templates/base.html`)

Item "Aprovações (Diretoria)" visível para `role == 'diretor'` ou `role == 'admin'` — preserva item do Gestor do Plano 03.

## Verification Results

| Check | Result |
|-------|--------|
| `python manage.py check` | PASSED — 0 issues |
| `pytest test_views_diretor.py` (10 testes) | PASSED — verde |
| FilaDiretorView sem filtro de unidade (D-06) | PASSED |
| DiretorRequiredMixin bloqueia Gestor → 403 | PASSED |
| DiretorRequiredMixin bloqueia Solicitante → 403 | PASSED |
| Aprovar PENDENTE_DIRETOR → APROVADO | PASSED |
| Aprovar estado inválido → 409 | PASSED |
| Reprovar sem motivo → não transiciona | PASSED |
| Reprovar com motivo → REPROVADO permanente | PASSED |
| Aprovar requisição REPROVADA → 409 (D-13) | PASSED |
| `{% csrf_token %}` no modal | PASSED |
| Rotas do Gestor preservadas | PASSED |

## Deviations from Plan

Nenhum desvio significativo. Execução conforme o plano.

## Threat Flags

| Ameaça | Mitigação Aplicada |
|--------|-------------------|
| T-04-01: Gestor/Solicitante acessando fila do Diretor | DiretorRequiredMixin → 403 |
| T-04-02: Reprovação do Diretor sem motivo | ReprovaForm + service (defense in depth) |
| T-04-03: Ação sobre estado terminal REPROVADO | service levanta ValueError → 409 (D-13) |
| T-04-04: Aprovação dupla concorrente | select_for_update() no service (Plano 02) |
| T-04-05: CSRF em modal HTMX | {% csrf_token %} no modal_reprovar_diretor.html |

## Self-Check

### Files verified to exist:
- `apps/aprovacoes/views.py` — DiretorRequiredMixin + FilaDiretorView FOUND
- `apps/aprovacoes/urls.py` — 8 rotas (4 Gestor + 4 Diretor) FOUND
- `apps/aprovacoes/templates/aprovacoes/fila_diretor.html` — FOUND
- `apps/aprovacoes/templates/aprovacoes/partials/fila_diretor_row.html` — FOUND
- `apps/aprovacoes/templates/aprovacoes/partials/modal_reprovar_diretor.html` — FOUND
- `apps/aprovacoes/tests/test_views_diretor.py` — FOUND

### Commits:
- `3679546` — test(02-04): add failing tests for slice vertical do Diretor
- `f701355` — feat(02-04): slice do Diretor — fila 2o nivel, aprovar/reprovar HTMX, URLs e nav

## Self-Check: PASSED
