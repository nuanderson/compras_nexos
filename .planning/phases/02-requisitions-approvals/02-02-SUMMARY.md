---
phase: "02-requisitions-approvals"
plan: "02"
subsystem: requisitions-service-layer
tags: [django, services, views, forms, htmx, templates, tdd, fsmachine]
dependency_graph:
  requires:
    - requisicoes.Requisicao (FSM 6 estados) — Plan 02-01
    - aprovacoes.AprovacaoLog — Plan 02-01
    - aprovacoes.ConfiguracaoAlcada — Plan 02-01
    - accounts.User (role, default_unit) — Plan 01-01
    - accounts.UnidadeOrganizacional — Plan 01-01
  provides:
    - aprovacoes.services: submeter_requisicao, aprovar_gestor, aprovar_diretor, reprovar_requisicao, cancelar_requisicao, _notificar_gestores
    - requisicoes.views: slice completo do Solicitante (lista, criar, editar, detalhe, enviar, cancelar, status, copiar-dados)
    - requisicoes.forms: RequisicaoForm com 5 campos
    - requisicoes.urls: namespace requisicoes com 8 rotas
    - templates: 8 templates/partials HTMX do Solicitante
  affects:
    - Plan 02-03 (fila do Gestor consome aprovacoes.services.aprovar_gestor, reprovar_requisicao)
    - Plan 02-04 (fila do Diretor consome aprovacoes.services.aprovar_diretor, reprovar_requisicao)
    - Plan 02-03 (implementa _notificar_gestores real, substituindo o stub)
tech_stack:
  added: []
  patterns:
    - Service layer com select_for_update() + transaction.atomic() para todas as transições de estado
    - Validação de motivo ANTES do transaction.atomic() (defense in depth, T-02-02)
    - transaction.on_commit() para _notificar_gestores (efeito colateral transacional)
    - SolicitanteRequiredMixin replicando AdminRequiredMixin
    - _get_requisicao_para com ownership por role (solicitante/gestor/diretor/admin)
    - HTMX polling de 15s para badge de status via hx-trigger="every 15s"
    - HTMX copiar-dados via hx-get com hx-trigger="change" em select
    - Retorno 409 em ValueError/PermissionError do service (Armadilha 4)
    - csrf_token em todos os forms de partials (CR-04)
    - Script de aplicação de classes CSS em campos_requisicao.html (padrão accounts)
key_files:
  created:
    - apps/aprovacoes/services.py (máquina de estados completa)
    - apps/aprovacoes/tests/conftest.py (fixtures de teste)
    - apps/aprovacoes/tests/test_services.py (16 testes)
    - apps/requisicoes/forms.py (RequisicaoForm)
    - apps/requisicoes/views.py (8 views + 1 mixin + 1 helper)
    - apps/requisicoes/urls.py (namespace requisicoes, 8 rotas)
    - apps/requisicoes/tests/conftest.py (fixtures de teste)
    - apps/requisicoes/tests/test_forms.py (5 testes)
    - apps/requisicoes/tests/test_views.py (16 testes)
    - apps/requisicoes/templates/requisicoes/requisicao_list.html
    - apps/requisicoes/templates/requisicoes/requisicao_form.html
    - apps/requisicoes/templates/requisicoes/requisicao_detail.html
    - apps/requisicoes/templates/requisicoes/partials/requisicao_row.html
    - apps/requisicoes/templates/requisicoes/partials/status_badge.html
    - apps/requisicoes/templates/requisicoes/partials/historico.html
    - apps/requisicoes/templates/requisicoes/partials/campos_requisicao.html
    - apps/requisicoes/templates/requisicoes/partials/copiar_dados.html
  modified:
    - config/urls.py (include apps.requisicoes.urls sob requisicoes/)
    - templates/base.html (nav Requisições aponta para requisicoes:lista)
decisions:
  - "Templates criados junto com a Task 2 (não separadamente na Task 3) para viabilizar testes de views que renderizam templates reais"
  - "SolicitanteRequiredMixin permite todos os roles autenticados — ownership granular aplicado em _get_requisicao_para"
  - "Validação de motivo antes de transaction.atomic() em reprovar_requisicao (defense in depth, T-02-02)"
  - "status_badge.html renderiza badge estático na listagem e com polling no detalhe (hx-trigger via contexto de uso)"
  - "_notificar_gestores é stub com logger.warning visível — corpo real no Plano 03"
  - "Banco PostgreSQL local (pg 18, porta 5432) configurado via .env no worktree para execução de testes"
metrics:
  duration_minutes: 39
  completed_date: "2026-06-10"
  tasks_completed: 3
  tasks_total: 3
  files_created: 19
  files_modified: 2
---

# Phase 02 Plan 02: Slice Vertical do Solicitante — Serviços, Views e Templates Summary

**One-liner:** Camada de serviço completa com 5 transições FSM atômicas (select_for_update) + slice do Solicitante end-to-end: criar rascunho, listar, detalhar com polling de status, enviar para aprovação, cancelar, copiar dados de requisição anterior.

## What Was Built

### apps/aprovacoes/services.py — Máquina de Estados Completa

Todas as 5 transições de estado implementadas com `select_for_update()` + `transaction.atomic()`:

- **submeter_requisicao**: RASCUNHO → PENDENTE_GESTOR; cria AprovacaoLog(ENVIO); `transaction.on_commit(_notificar_gestores)`
- **aprovar_gestor**: PENDENTE_GESTOR → APROVADO ou PENDENTE_DIRETOR conforme ConfiguracaoAlcada (D-09, D-10)
- **aprovar_diretor**: PENDENTE_DIRETOR → APROVADO; cria AprovacaoLog(APROVACAO_FINAL) (APROV-04)
- **reprovar_requisicao**: → REPROVADO; motivo validado **antes** do `transaction.atomic()` (APROV-05, T-02-02, defense in depth)
- **cancelar_requisicao**: RASCUNHO/PENDENTE_GESTOR → CANCELADO; bloqueia PENDENTE_DIRETOR (D-15)
- **_notificar_gestores**: stub documentado com `logger.warning("STUB: ...")` apontando para o Plano 03 (REQ-04)

O módulo define `logger = logging.getLogger(__name__)` e o stub emite WARNING visível sem levantar exceção (chamado via `on_commit`).

### apps/requisicoes/forms.py

`RequisicaoForm(ModelForm)` com `fields = ["descricao", "categoria", "valor_estimado", "justificativa", "unidade"]`:
- Queryset de categoria filtrado por `ativo=True`
- Queryset de unidade filtrado por `ativo=True`
- Kwarg `user` para pré-selecionar `default_unit` (UNIT-03)

### apps/requisicoes/views.py

- **SolicitanteRequiredMixin**: todos os autenticados acessam; ownership granular em `_get_requisicao_para`
- **_get_requisicao_para(user, pk)**: admin/diretor veem tudo; gestor vê da própria unidade; solicitante vê as próprias (T-02-04)
- **RequisicaoListView**: filtra `criado_por=request.user` com `select_related`
- **RequisicaoCreateView**: salva como RASCUNHO, não submete (D-12)
- **RequisicaoUpdateView**: só edita se status=RASCUNHO
- **RequisicaoDetailView**: contexto com `requisicao` + `logs` (REQ-03)
- **RequisicaoEnviarView**: chama `services.submeter_requisicao`, retorna 409 em ValueError (Armadilha 4)
- **RequisicaoCancelarView**: chama `services.cancelar_requisicao`, retorna partial `requisicao_row.html` via HTMX
- **StatusBadgeView**: retorna `partials/status_badge.html` para polling (REQ-02)
- **CopiarDadosView**: busca requisição com `criado_por=request.user` para ownership (T-02-04)

### apps/requisicoes/urls.py

Namespace `requisicoes` com 8 rotas; `nova/` e `copiar-dados/` **antes** de `<int:pk>/` para evitar colisão.

### Templates e Partials HTMX

- **requisicao_list.html**: listagem com estado vazio, inclui `requisicao_row.html`
- **requisicao_form.html**: card com select de copiar-dados e `#campos-requisicao`
- **requisicao_detail.html**: dados da requisição + badge com polling `hx-trigger="every 15s"` + histórico
- **partials/requisicao_row.html**: `id="requisicao-row-{{pk}}"` para outerHTML swap; botão cancelar via hx-post
- **partials/status_badge.html**: 6 estados mapeados para classes CSS (.badge-rascunho, .badge-aguardando, .badge-em-cotacao, .badge-ativo, .badge-inativo, .badge-cancelado)
- **partials/campos_requisicao.html**: form com `{% csrf_token %}` + script de classes CSS (CR-04)
- **partials/copiar_dados.html**: select com `hx-get` + `hx-trigger="change"` (D-14, Padrão 7)
- **partials/historico.html**: tabela de AprovacaoLog com ator, evento, data, motivo (REQ-03)

## Verification Results

| Check | Result |
|-------|--------|
| `python manage.py check` | PASSED — 0 issues |
| `makemigrations --check requisicoes aprovacoes` | PASSED — No changes detected |
| `pytest test_services.py` (16 testes) | PASSED — verde |
| `pytest test_forms.py` (5 testes) | PASSED — verde |
| `pytest test_views.py` (16 testes) | PASSED — verde |
| Total: 37 testes | PASSED — todos verdes |
| 8 templates existem nos caminhos corretos | PASSED |
| status_badge com `hx-trigger="every 15s"` no detalhe | PASSED |
| `{% csrf_token %}` em campos_requisicao.html | PASSED |
| Nav Requisições aponta para `requisicoes:lista` | PASSED |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Template campos_requisicao.html usava variável `action` e `requisicao` sem verificar existência**

- **Found during:** Task 2 (testes de CopiarDadosView)
- **Issue:** O template usava `{% if action == 'create' %}` e `{% url 'requisicoes:editar' requisicao.pk %}` mas CopiarDadosView não passa `action` nem `requisicao` no contexto — resultado: `NoReverseMatch` para `editar` com pk vazio
- **Fix:** Substituído por `{% if requisicao %}{% url 'requisicoes:editar' requisicao.pk %}{% else %}{% url 'requisicoes:nova' %}{% endif %}` — condicional baseado na existência de `requisicao` no contexto
- **Files modified:** `apps/requisicoes/templates/requisicoes/partials/campos_requisicao.html`
- **Commit:** `cdf1a52`

**2. [Rule 3 - Blocker] Templates criados antecipadamente na Task 2 para viabilizar testes de views**

- **Found during:** Task 2 (testes de views exigem templates para render())
- **Issue:** O plano previa criar templates apenas na Task 3, mas os testes de views (`RequisicaoListView`, `RequisicaoDetailView`, `CopiarDadosView`) chamam `render()` que requer templates existentes. Sem templates, os testes retornam `TemplateDoesNotExist`.
- **Fix:** Templates criados junto com a Task 2. Task 3 validou os acceptance criteria (manage.py check, test_views.py verde, 8 arquivos existentes). O plano foi executado em 2 commits em vez de 3, mas todos os artefatos foram entregues.
- **Files modified:** Todos os 8 templates/partials

### Environment Notes

- Python local: 3.14.5 com Django 6.0.6 (sem Python 3.12/Django 5.2 disponível fora do Docker)
- PostgreSQL 18 nativo na porta 5432 (Windows). Configurado `.env` no worktree com `DB_HOST=127.0.0.1`
- `makemigrations --check` sem app label específico reporta migration para `accounts` (artefato Django 6 — documentado no Plano 01)

## Known Stubs

**1. `_notificar_gestores` em `apps/aprovacoes/services.py`**

- **Arquivo:** `apps/aprovacoes/services.py`, função `_notificar_gestores`
- **Comportamento:** Emite `logger.warning("STUB: _notificar_gestores não implementado — REQ-04 requer implementação no Plano 03")` e retorna sem enviar e-mail
- **Razão:** O envio real de e-mail (REQ-04, D-07, D-16) pertence ao slice do Gestor no Plano 03. A função existe e é referenciada por `transaction.on_commit` em `submeter_requisicao` — o Plano 03 preencherá o corpo real.
- **Resolvido em:** Plano 03 (slice do Gestor)

## Threat Flags

Nenhuma nova superfície de ataque além do threat model do plano. Mitigações implementadas:

| Ameaça | Mitigação Aplicada |
|--------|-------------------|
| T-02-01: Spoofing — submeter/cancelar por não-dono | `req.criado_por != solicitante` → PermissionError no service |
| T-02-02: Tampering — motivo vazio em reprovação | Validação antes de `transaction.atomic()` |
| T-02-03: Tampering — aprovação/cancelamento concorrente | `select_for_update()` em todas as 5 transições |
| T-02-04: Information Disclosure — detalhe de outro Solicitante | `_get_requisicao_para` com ownership; CopiarDadosView filtra `criado_por=request.user` |
| T-02-05: Elevation of Privilege — Solicitante chamando URL de Gestor | Views de envio só chamam transições de Solicitante; Gestor/Diretor ficam no Plano 03/04 |
| T-02-06: CSRF em forms HTMX | `{% csrf_token %}` em `campos_requisicao.html`; meta csrf-token + handler em base.html |

## Self-Check

### Files verified to exist:
- `apps/aprovacoes/services.py` — FOUND
- `apps/aprovacoes/tests/test_services.py` — FOUND
- `apps/requisicoes/forms.py` — FOUND
- `apps/requisicoes/views.py` — FOUND
- `apps/requisicoes/urls.py` — FOUND
- `apps/requisicoes/templates/requisicoes/requisicao_list.html` — FOUND
- `apps/requisicoes/templates/requisicoes/requisicao_form.html` — FOUND
- `apps/requisicoes/templates/requisicoes/requisicao_detail.html` — FOUND
- `apps/requisicoes/templates/requisicoes/partials/requisicao_row.html` — FOUND
- `apps/requisicoes/templates/requisicoes/partials/status_badge.html` — FOUND
- `apps/requisicoes/templates/requisicoes/partials/historico.html` — FOUND
- `apps/requisicoes/templates/requisicoes/partials/campos_requisicao.html` — FOUND
- `apps/requisicoes/templates/requisicoes/partials/copiar_dados.html` — FOUND

### Commits verified:
- `0b5e551` — feat(02-02): camada de serviço completa com 5 transições atômicas + testes
- `cdf1a52` — feat(02-02): forms, views, URLs, templates do Solicitante + testes

## Self-Check: PASSED
