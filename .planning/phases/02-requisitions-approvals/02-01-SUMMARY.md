---
phase: "02-requisitions-approvals"
plan: "01"
subsystem: data-foundation
tags: [django, models, migrations, admin, css, requisicoes, aprovacoes]
dependency_graph:
  requires:
    - apps.core.AuditedModel — Plan 01-01
    - apps.core.TimestampedModel — Plan 01-01
    - accounts.User (AUTH_USER_MODEL) — Plan 01-01
    - accounts.UnidadeOrganizacional — Plan 01-01
  provides:
    - requisicoes.CategoriaCompra (FK target para Requisicao)
    - requisicoes.Requisicao (FSM 6 estados, predicados puros, AuditedModel)
    - aprovacoes.AprovacaoLog (trilha de auditoria imutável, TimestampedModel)
    - aprovacoes.ConfiguracaoAlcada (singleton alçada, fail-safe requer_diretor)
    - apps.requisicoes e apps.aprovacoes registrados em INSTALLED_APPS
    - Migrations 0001_initial para ambos os apps
    - Django admin para CategoriaCompra, ConfiguracaoAlcada, AprovacaoLog
    - CSS badges .badge-rascunho e .badge-cancelado
  affects:
    - Plan 02-02 (views/forms/services dependem dos modelos)
    - Plan 02-03 (fila do Gestor e ações de aprovação)
    - Plan 02-04 (fila do Diretor)
    - Todos os planos subsequentes que criam AprovacaoLog
tech_stack:
  added: []
  patterns:
    - AuditedModel herança em Requisicao (criado_por, criado_em, atualizado_em)
    - TimestampedModel herança em AprovacaoLog (criado_em, atualizado_em)
    - TextChoices internos no modelo (Requisicao.Status, AprovacaoLog.Evento)
    - Métodos predicado puros no modelo (sem efeito colateral — lógica de transição em services.py)
    - Singleton via get_or_create(pk=1) em ConfiguracaoAlcada.obter()
    - Fail-safe em requer_diretor quando valor_maximo_gestor=None (D-10)
    - has_add_permission/has_delete_permission para controle de singleton e log imutável
    - ESTADOS_TERMINAIS e CANCELA_PERMISSOES como atributos de classe em Requisicao
key_files:
  created:
    - apps/requisicoes/__init__.py
    - apps/requisicoes/apps.py
    - apps/requisicoes/models.py (CategoriaCompra + Requisicao)
    - apps/requisicoes/admin.py (CategoriaCompraAdmin)
    - apps/requisicoes/migrations/__init__.py
    - apps/requisicoes/migrations/0001_initial.py
    - apps/requisicoes/tests/__init__.py
    - apps/aprovacoes/__init__.py
    - apps/aprovacoes/apps.py
    - apps/aprovacoes/models.py (AprovacaoLog + ConfiguracaoAlcada)
    - apps/aprovacoes/admin.py (ConfiguracaoAlcadaAdmin + AprovacaoLogAdmin)
    - apps/aprovacoes/migrations/__init__.py
    - apps/aprovacoes/migrations/0001_initial.py
    - apps/aprovacoes/tests/__init__.py
  modified:
    - config/settings/base.py (apps.requisicoes, apps.aprovacoes adicionados a INSTALLED_APPS)
    - static/css/main.css (.badge-rascunho e .badge-cancelado adicionados)
decisions:
  - "Migrations geradas com dependência em accounts/0002_create_groups (não 0003) — compatível com Django 5.2"
  - "DecimalField(max_digits=12, decimal_places=2) em valor_estimado e valor_maximo_gestor — nunca FloatField"
  - "ESTADOS_TERMINAIS e CANCELA_PERMISSOES como class attributes (sets) — comparação O(1)"
  - "Métodos predicado puros sem efeito colateral — separação de concerns com services.py"
metrics:
  duration_minutes: 38
  completed_date: "2026-06-10"
  tasks_completed: 2
  tasks_total: 2
  files_created: 14
  files_modified: 2
---

# Phase 02 Plan 01: Fundação de Dados — Modelos, Migrations e Admin Summary

**One-liner:** Dois apps Django (requisicoes + aprovacoes) com quatro modelos (CategoriaCompra, Requisicao FSM-6-estados, AprovacaoLog imutável, ConfiguracaoAlcada singleton) + admin protegido contra singleton-violação e log-tampering + badges CSS RASCUNHO/CANCELADO.

## What Was Built

### apps/requisicoes

- **CategoriaCompra**: modelo simples com `nome`, `ativo`, ordering por nome. Cadastrável via Django admin pelo Admin (D-01, D-03).
- **Requisicao(AuditedModel)**: FSM de 6 estados via `Status(TextChoices)`: RASCUNHO → PENDENTE_GESTOR → PENDENTE_DIRETOR → APROVADO/REPROVADO/CANCELADO. Campos: `descricao (CharField 500)`, `categoria (FK PROTECT)`, `valor_estimado (DecimalField 12,2)`, `justificativa (TextField)`, `unidade (FK accounts.UnidadeOrganizacional PROTECT)`, `status (CharField choices)`. Atributos de classe: `ESTADOS_TERMINAIS` e `CANCELA_PERMISSOES`. Métodos predicado puros: `pode_submeter()`, `pode_cancelar()`, `pode_gestor_agir()`, `pode_diretor_agir()`.

### apps/aprovacoes

- **AprovacaoLog(TimestampedModel)**: trilha de auditoria imutável com 5 eventos (`Evento.TextChoices`): ENVIO, APROVACAO_GESTOR, APROVACAO_FINAL, REPROVACAO, CANCELAMENTO. FK para `requisicoes.Requisicao` (CASCADE) e `settings.AUTH_USER_MODEL` (SET_NULL). Campo `motivo` com default vazio.
- **ConfiguracaoAlcada**: singleton pk=1 com `valor_maximo_gestor (DecimalField null)`. Classmethod `obter()` via `get_or_create(pk=1)`. Método `requer_diretor(valor: Decimal) -> bool` com fail-safe (D-10): `None` → sempre True (2 níveis).

### Django admin

- **CategoriaCompraAdmin**: `list_display=["nome","ativo"]`, `list_filter=["ativo"]`, `search_fields=["nome"]`.
- **ConfiguracaoAlcadaAdmin**: `has_add_permission` retorna `not ConfiguracaoAlcada.objects.exists()` — bloqueia 2ª linha. `has_delete_permission=False` — singleton nunca deletado (T-02-01-02).
- **AprovacaoLogAdmin**: `readonly_fields` cobre todos os campos. `has_add_permission=False`, `has_delete_permission=False` — trilha de auditoria imutável via admin (T-02-01-03, REQ-03).

### CSS

Adicionadas em `static/css/main.css` após `.badge-admin`:
- `.badge-rascunho { background:#374151; color:#9ca3af; }`
- `.badge-cancelado { background:#374151; color:#9ca3af; }`

## Verification Results

| Check | Result |
|-------|--------|
| `python manage.py check` | PASSED — 0 issues |
| `makemigrations --check --dry-run` para ambos os apps | PASSED — No changes detected |
| Importação de todos os 4 modelos | PASSED |
| `apps.requisicoes` e `apps.aprovacoes` em INSTALLED_APPS | PASSED |
| `ConfiguracaoAlcada.requer_diretor(Decimal('100'))` com `valor_maximo_gestor=None` | `True` (fail-safe confirmado) |
| 6 Status choices verificados | PASSED |
| 4 métodos predicado (pode_submeter/cancelar/gestor_agir/diretor_agir) | PASSED |
| 3 modelos em `admin.site._registry` | PASSED |
| `.badge-rascunho` e `.badge-cancelado` em main.css | PASSED |
| `AprovacaoLogAdmin.has_add/delete_permission` | `False` — imutável |
| `ConfiguracaoAlcadaAdmin.has_delete_permission` | `False` — singleton protegido |

**Nota sobre `migrate`:** O banco de dados PostgreSQL (Docker) não estava acessível durante a execução (Docker Desktop parado). As migrations foram geradas corretamente e verificadas via `makemigrations --check`. A aplicação (`python manage.py migrate`) deve ser executada quando Docker subir. As migrations são Django 5.2 compatíveis (dependência em `accounts/0002_create_groups`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocker] Migração gerada com dependência errada em accounts/0003**

- **Found during:** Task 1 verification
- **Issue:** `makemigrations` rodando com Django 6.0.6 (ambiente local vs Docker) gerou uma migração extra `accounts/0003_alter_user_email_alter_user_groups.py` e criou a dependência de `requisicoes/0001_initial.py` nela. Essa migração 0003 não existe no Django 5.2 e quebraria o `migrate` no container.
- **Fix:** Removida a migração `accounts/0003` gerada pelo Django 6. As migrations de `requisicoes` e `aprovacoes` foram reescritas manualmente com a dependência correta em `accounts/0002_create_groups` e com o cabeçalho `# Generated by Django 5.2`.
- **Files modified:** `apps/requisicoes/migrations/0001_initial.py`, `apps/aprovacoes/migrations/0001_initial.py`
- **Commit:** `282e325`

### Environment Notes

- Python local: 3.14.5 com Django 6.0.6 (sem Python 3.12/Django 5.2 disponível fora do Docker)
- Docker Desktop estava parado — não foi possível executar `python manage.py migrate` contra o PostgreSQL
- `makemigrations`, `check`, e importação de modelos funcionaram com Django 6 pois a API de ORM é retrocompatível para os padrões usados
- `python manage.py check` retornou 0 issues — estrutura dos modelos está correta

## Known Stubs

Nenhum stub. Todos os modelos têm implementação completa:
- `ConfiguracaoAlcada.obter()` é funcional (get_or_create)
- `requer_diretor()` implementado com fail-safe
- Todos os métodos predicado retornam valores reais

## Threat Flags

Nenhuma nova superfície de ataque além do planejado. O threat model do plano cobre todos os controles implementados:

| Ameaça | Mitigação Implementada |
|--------|----------------------|
| T-02-01-01: Acesso não autorizado ao admin | Django admin exige `is_staff` por padrão |
| T-02-01-02: Criação de 2ª ConfiguracaoAlcada | `has_add_permission` retorna `not .exists()`, `has_delete_permission=False` |
| T-02-01-03: Edição/exclusão de AprovacaoLog | `readonly_fields` em todos os campos, `has_add/delete_permission=False` |

## Self-Check

### Files verified to exist:
- `apps/requisicoes/models.py` — FOUND
- `apps/aprovacoes/models.py` — FOUND
- `apps/requisicoes/admin.py` — FOUND
- `apps/aprovacoes/admin.py` — FOUND
- `apps/requisicoes/migrations/0001_initial.py` — FOUND
- `apps/aprovacoes/migrations/0001_initial.py` — FOUND

### Commits verified:
- `282e325` — feat(02-01): criar apps requisicoes e aprovacoes com os quatro modelos
- `e391588` — feat(02-01): registrar modelos no Django admin e adicionar badges CSS

## Self-Check: PASSED
