---
phase: 02-requisitions-approvals
plan: "03"
subsystem: aprovacoes
tags: [gestor, fila-aprovacao, htmx-modal, email-transacional, fsm]
dependency_graph:
  requires: ["02-02"]
  provides: ["fila-gestor", "aprovar-gestor", "reprovar-gestor", "email-notificacao-gestores"]
  affects: ["apps/aprovacoes", "config/urls.py", "templates/base.html"]
tech_stack:
  added: []
  patterns:
    - "GestorRequiredMixin replicando AdminRequiredMixin com role in (gestor, admin)"
    - "ListView com get_queryset filtrando por default_unit (fail-safe para None)"
    - "HTMX outerHTML swap vazio para remover linha da fila apos aprovacao/reprovacao"
    - "HTMX hx-get para carregar modal no #modal-container, hx-post para confirmar"
    - "send_mail com fail_silently=True via transaction.on_commit (D-07, D-18)"
    - "Import tardio de Requisicao em _notificar_gestores para evitar circular import"
key_files:
  created:
    - apps/aprovacoes/forms.py
    - apps/aprovacoes/views.py
    - apps/aprovacoes/urls.py
    - apps/aprovacoes/templates/aprovacoes/fila_gestor.html
    - apps/aprovacoes/templates/aprovacoes/partials/fila_row.html
    - apps/aprovacoes/templates/aprovacoes/partials/modal_reprovar.html
    - apps/aprovacoes/tests/test_views.py
  modified:
    - apps/aprovacoes/services.py
    - apps/aprovacoes/tests/test_services.py
    - config/urls.py
    - templates/base.html
decisions:
  - "Modal de reprovacao carregado via hx-get no #modal-container, POST com hx-swap=outerHTML para remover linha"
  - "AprovarGestorView e ReprovarGestorView retornam HttpResponse vazio para remover linha da fila (outerHTML swap)"
  - "Stub test de _notificar_gestores atualizado para verificar comportamento real (falha silenciosa com pk inexistente)"
metrics:
  duration: "~35 minutos"
  completed: "2026-06-10T23:54:12Z"
  tasks_completed: 2
  files_changed: 11
---

# Phase 02 Plan 03: Slice Vertical do Gestor Summary

**One-liner:** Fila de aprovacao PENDENTE_GESTOR filtrada por unidade com modal HTMX de reprovacao e e-mail transacional real aos Gestores via send_mail + on_commit.

## What Was Built

Slice vertical completo do Gestor: a fila de requisicoes aguardando 1o nivel de aprovacao filtrada pela unidade do usuario, as acoes de aprovar (com roteamento por alcada D-09) e reprovar (com motivo obrigatorio via modal HTMX), e a implementacao real de `_notificar_gestores` substituindo o stub do Plano 02.

### Task 1: Implementar _notificar_gestores real (GREEN)

Substituiu o stub com `logger.warning("STUB...")` pela implementacao real:
- Busca Gestores ativos da unidade da requisicao (`role=GESTOR, default_unit=req.unidade, is_active=True`)
- Falha silenciosa quando sem destinatarios (D-07) ou requisicao nao encontrada
- `send_mail` com `fail_silently=True`, chamado via `transaction.on_commit`
- Import tardio de `Requisicao` evita circular import
- 5 testes de e-mail passando

### Task 2: Fila do Gestor e acoes HTMX

**Views criadas:**
- `GestorRequiredMixin`: bloqueia Solicitante com 403 (T-03-02)
- `FilaGestorView`: ListView filtrando `status=PENDENTE_GESTOR, unidade=default_unit`; retorna `objects.none()` quando `default_unit=None` (Armadilha 3)
- `AprovarGestorView`: POST chama `services.aprovar_gestor`, retorna 409 em estado invalido, verifica ownership de unidade (T-03-01)
- `ModalReprovarView`: GET retorna partial modal com `ReprovaForm`
- `ReprovarGestorView`: POST valida motivo via `ReprovaForm`, chama `services.reprovar_requisicao`

**Forms:** `ReprovaForm` com `clean_motivo` rejeitando string em branco (APROV-05, T-03-03)

**Templates:** `fila_gestor.html` (tabela com estado vazio), `partials/fila_row.html` (botoes Aprovar/Reprovar HTMX), `partials/modal_reprovar.html` (form com `{% csrf_token %}` e textarea motivo, T-03-06)

**10 testes de view passando** cobrindo filtro de unidade, `default_unit=None`, so PENDENTE_GESTOR, 403 para Solicitante, aprovacao baixo/alto valor, 409 em estado invalido, GET modal, reprovacao sem motivo rejeitada, reprovacao com motivo.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrigido literal de string com quebra de linha em services.py**
- **Found during:** Pre-execucao (diagnostico de falha de coleta de testes)
- **Issue:** O arquivo `apps/aprovacoes/services.py` no working directory do repositorio principal tinha `corpo = "\n".join(...)` escrito com quebra de linha literal no codigo-fonte, causando `SyntaxError: unterminated string literal` na linha 250. Isso impedia a coleta de qualquer teste do modulo.
- **Fix:** O worktree foi resetado para o commit `4a8910b` (HEAD do master), obtendo o stub limpo. A implementacao real foi escrita corretamente com `"\n"`.
- **Files modified:** `apps/aprovacoes/services.py`
- **Commit:** `55223ed`

**2. [Rule 1 - Bug] Atualizado test_notificar_gestores_stub_emite_warning em test_services.py**
- **Found during:** Task 1 — execucao do suite completo `apps/aprovacoes/tests/`
- **Issue:** `TestNotificarGestoresStub.test_notificar_gestores_stub_emite_warning` verificava que `_notificar_gestores` emitia `logger.warning("STUB...")`. Com a implementacao real, esse comportamento foi removido, quebrando o teste.
- **Fix:** Renomeado e reescrito para `test_notificar_gestores_pk_inexistente_nao_levanta_excecao`, que verifica o comportamento correto atual: falha silenciosa com pk inexistente (D-07).
- **Files modified:** `apps/aprovacoes/tests/test_services.py`
- **Commit:** `34bee65`

**3. [Rule 3 - Blocking] Criado .env no worktree com DB_HOST=127.0.0.1**
- **Found during:** Task 1 — primeira execucao de testes no worktree
- **Issue:** O worktree nao tinha `.env`. O `config/settings/base.py` usa `DB_HOST=config("DB_HOST", default="db")`, e sem `.env` local tentava conectar ao hostname Docker `db`, falhando com `psycopg2.OperationalError: could not translate host name "db"`.
- **Fix:** Criado `.env` no worktree com `DB_HOST=127.0.0.1` (PostgreSQL nativo no Windows, conforme especificado no plano).
- **Files modified:** `.env` (nao rastreado no git — gitignored)

## Known Stubs

Nenhum stub nas areas entregues por este plano. Todos os dados sao buscados do banco de dados real.

Itens pendentes em outros planos (fora do escopo):
- Nav: "Cotacoes", "Fornecedores", "Relatorios" ainda apontam para `href="#"` (planejados em fases futuras)

## Threat Surface Scan

Nenhuma nova superficie de seguranca introduzida alem do mapeado no `<threat_model>` do plano.

Todas as mitigacoes do threat register foram implementadas:
- T-03-01: verificacao `req.unidade != request.user.default_unit` em todas as views de acao
- T-03-02: `GestorRequiredMixin` em todas as views de aprovacao
- T-03-03: `ReprovaForm.clean_motivo` + validacao no service (defense in depth)
- T-03-04: `select_for_update()` no service (Plano 02) + retorno 409 via ValueError
- T-03-05: `_notificar_gestores` filtra `default_unit=req.unidade, is_active=True`
- T-03-06: `{% csrf_token %}` no form do modal + meta csrf-token em base.html + htmx:configRequest handler

## Self-Check: PASSED

| Item | Status |
|------|--------|
| apps/aprovacoes/forms.py | FOUND |
| apps/aprovacoes/views.py | FOUND |
| apps/aprovacoes/urls.py | FOUND |
| apps/aprovacoes/templates/aprovacoes/fila_gestor.html | FOUND |
| apps/aprovacoes/templates/aprovacoes/partials/fila_row.html | FOUND |
| apps/aprovacoes/templates/aprovacoes/partials/modal_reprovar.html | FOUND |
| apps/aprovacoes/tests/test_views.py | FOUND |
| Commit 55223ed (feat: _notificar_gestores) | FOUND |
| Commit 34bee65 (feat: fila gestor + views + templates) | FOUND |
| 52 tests passing (apps/aprovacoes + apps/requisicoes) | CONFIRMED |
| python manage.py check | 0 issues |
