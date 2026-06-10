# Phase 2: Requisitions & Approvals - Context

**Gathered:** 2026-06-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Solicitantes podem abrir requisições de compra com rascunho, enviá-las para aprovação e acompanhar o status. Gestores e Diretores aprovam ou reprovam em até 2 níveis conforme alçadas configuráveis por valor. Toda decisão fica registrada em log de auditoria com ator, timestamp e motivo.

**Entrega:** fluxo completo de requisição → aprovação funcionando end-to-end, com e-mail ao Gestor na criação e histórico visível ao Solicitante.

</domain>

<decisions>
## Implementation Decisions

### Categorias de Compra (REQ-01)

- **D-01:** Categorias são **cadastráveis pelo Admin via painel** — modelo separado `CategoriaCompra` (nome, ativo). Não é enum hardcoded.
- **D-02:** Volume esperado: ~3 categorias inicialmente (ex: Material de Escritório, Serviços, TI). O formulário de requisição usa um `<select>` com categorias ativas.
- **D-03:** `CategoriaCompra` vive em `apps/requisicoes`. Admin gerencia via Django admin (`/admin/`) ou painel HTMX dedicado — a decidir pelo planner conforme escopo do painel admin já existente.

### Roteamento do Gestor (REQ-04, APROV-01)

- **D-04:** "Gestor responsável" = todos os usuários com `role=gestor` cuja `default_unit` coincide com a unidade da requisição. Pode haver 0 ou N Gestores por unidade.
- **D-05:** Gestor vê **apenas** requisições cuja unidade bate com sua `default_unit`.
- **D-06:** Diretor e Admin veem requisições de **todas** as unidades.
- **D-07:** Quando nova requisição entra em `PENDENTE_GESTOR`, e-mail é enviado para **todos** os Gestores da unidade (via `transaction.on_commit()` + django-anymail SES).

### Alçadas por Valor (APROV-06)

- **D-08:** Modelo `ConfiguracaoAlcada` com campo `valor_maximo_gestor: DecimalField(max_digits=12, decimal_places=2)`. Admin e Diretor configuram via painel.
- **D-09:** Lógica de bypass:
  - `valor_estimado < valor_maximo_gestor` → apenas Gestor aprova → status vai direto para `APROVADO`
  - `valor_estimado >= valor_maximo_gestor` → Gestor aprova primeiro, depois Diretor
- **D-10:** Comportamento padrão (sem configuração ou `valor_maximo_gestor = None`) → **sempre 2 níveis** (fail-safe: exige Diretor).
- **D-11:** Configurável pelo Admin/Diretor via Django admin ou view dedicada — a decidir pelo planner.

### Estados da Requisição (REQ-02, ciclo de vida completo)

- **D-12:** Existe estado **RASCUNHO** — criação salva como rascunho, Solicitante envia explicitamente para aprovação (botão "Enviar para aprovação").
- **D-13:** Reprovação é **permanente** — sem revisão ou reenvio da mesma requisição. Estado terminal.
- **D-14:** Feature **"copiar dados"** ao criar nova requisição: ao abrir o formulário de nova requisição, Solicitante pode selecionar uma requisição existente para pré-preencher campos (descrição, categoria, valor estimado, justificativa, unidade).
- **D-15:** Solicitante pode cancelar em **RASCUNHO** ou **PENDENTE_GESTOR** apenas. Após aprovação de 1º nível, sem cancelamento.

**Máquina de estados:**

```
RASCUNHO
  ├─→ PENDENTE_GESTOR   [Solicitante envia]
  └─→ CANCELADO          [Solicitante cancela]

PENDENTE_GESTOR
  ├─→ CANCELADO          [Solicitante cancela]
  ├─→ REPROVADO          [Gestor reprova — motivo obrigatório]
  ├─→ APROVADO           [Gestor aprova + valor < alçada]
  └─→ PENDENTE_DIRETOR   [Gestor aprova + valor ≥ alçada]

PENDENTE_DIRETOR
  ├─→ APROVADO           [Diretor aprova]
  └─→ REPROVADO          [Diretor reprova — motivo obrigatório]

Terminais: APROVADO | REPROVADO | CANCELADO
```

### E-mail (REQ-04)

- **D-16:** Único e-mail de v1: notificação aos Gestor(es) da unidade quando requisição entra em `PENDENTE_GESTOR`.
- **D-17:** Notificação ao Solicitante sobre aprovação/reprovação está **fora do escopo v1** (ver REQUIREMENTS.md `Out of Scope` + v2 `NOTF-01`).
- **D-18:** Implementar com `transaction.on_commit()` — sem Celery (conforme CLAUDE.md).

### Estrutura de Apps

- **D-19:** Dois apps Django novos:
  - `apps/requisicoes` — modelos `CategoriaCompra`, `Requisicao`; formulários e views do Solicitante
  - `apps/aprovacoes` — modelos `AprovacaoLog`, `ConfiguracaoAlcada`; `services.py` com toda lógica de transição de estado (usando `select_for_update()` + `transaction.atomic()`)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requisitos e Roadmap
- `.planning/REQUIREMENTS.md` §Requisições de Compra, §Aprovações — REQ-01..04, APROV-01..06 (escopo completo)
- `.planning/ROADMAP.md` §Phase 2 — success criteria da fase

### Fundação existente (herança direta)
- `apps/accounts/models.py` — `User` com `role` + `default_unit` FK (roteamento do Gestor depende disto)
- `apps/core/models.py` — `AuditedModel` (base para `Requisicao`) e `TimestampedModel` (base para `AprovacaoLog`)
- `apps/accounts/views.py` — `AdminRequiredMixin` (padrão de mixin a replicar para `GestorRequiredMixin`, `DiretorRequiredMixin`)
- `apps/accounts/services.py` — padrão de service layer (views thin, lógica em services)

### Padrões técnicos mandatórios
- `CLAUDE.md` §Approval Workflow — `select_for_update()` + `transaction.atomic()` para transições de estado
- `CLAUDE.md` §Email Notifications — `transaction.on_commit()` + django-anymail (sem Celery)
- `CLAUDE.md` §HTMX Patterns — Pattern 3 (modal para ações de aprovação), Pattern 2 (badge de status)

### Segurança (Phase 1 findings — aplicáveis aqui)
- `.planning/phases/01-foundation/01-REVIEW.md` — CR-01..CR-05: open redirect, logout GET, account enumeration. Os novos formulários da Fase 2 devem evitar os mesmos antipadrões.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AuditedModel` (`apps/core/models.py`): `Requisicao` herda direto — campos `criado_por` + `criado_em` + `atualizado_em` gratuitos
- `AdminRequiredMixin` (`apps/accounts/views.py`): padrão para criar `GestorRequiredMixin` e `DiretorRequiredMixin`
- `User.default_unit` FK: roteamento do Gestor é uma query `User.objects.filter(role='gestor', default_unit=requisicao.unidade)`
- Fixtures de teste em `apps/accounts/tests/conftest.py`: `gestor_user` e `solicitante_user` já existem — reutilizáveis nos testes da Fase 2

### Established Patterns
- **Service layer:** toda lógica de negócio em `services.py`, views apenas delegam — obrigatório para `apps/aprovacoes/services.py`
- **HTMX partial responses:** views verificam `request.htmx` e retornam partial ou full template — manter padrão para filas e modais de aprovação
- **DecimalField:** todo campo monetário usa `DecimalField(max_digits=12, decimal_places=2)` — `valor_estimado` e `valor_maximo_gestor` seguem isso
- **Testes com pytest-django:** fixtures em `conftest.py`, `@pytest.mark.django_db`, `Client` para views

### Integration Points
- `Requisicao.unidade` FK → `UnidadeOrganizacional` (já em `apps/accounts`)
- `Requisicao.criado_por` FK → `User` (via `AuditedModel`)
- `AprovacaoLog.requisicao` FK → `Requisicao`
- `AprovacaoLog.aprovador` FK → `User`
- `ConfiguracaoAlcada` é um singleton (uma linha na tabela) — usar `get_or_create` + cache de instância

</code_context>

<specifics>
## Specific Ideas

- **"Copiar dados" na criação:** Ao abrir o formulário de nova requisição, exibir um campo opcional "Copiar de requisição existente" (select com requisições do próprio Solicitante). Ao selecionar, pré-preenche via HTMX os campos descrição, categoria, valor estimado, justificativa e unidade — sem redirecionar.
- **Estado "Rascunho" visível:** Na listagem de requisições do Solicitante, rascunhos devem ter badge visual distinto (ex: cinza) com botão "Editar e Enviar", diferente de requisições em aprovação.
- **Fila do Gestor:** Tabela com colunas: Solicitante, Unidade, Descrição, Categoria, Valor Estimado, Data de Criação, Ação (Aprovar/Reprovar via modal HTMX).
- **Modal de reprovação:** Ao clicar "Reprovar", exibir modal HTMX inline com campo de texto obrigatório para o motivo (APROV-05). Não redirecionar — atualizar a linha via `hx-swap`.

</specifics>

<deferred>
## Deferred Ideas

- **Notificação ao Solicitante por e-mail:** Quando aprovado ou reprovado — explicitamente em v2 (`NOTF-01` no REQUIREMENTS.md).
- **Histórico de versões de rascunho:** Não foi solicitado — se o Solicitante editar um rascunho, sobrescreve os dados sem versionamento.
- **Múltiplas configurações de alçada por categoria:** Apenas um threshold global por enquanto. Alçadas por categoria entram em v2 se necessário.
- **Delegação de aprovação (férias/ausência):** Fora do escopo v1 — Gestor ausente → Admin reatribui manualmente ou reprova para reabrir via nova requisição.

</deferred>

---

*Phase: 2-Requisitions-Approvals*
*Context gathered: 2026-06-10*
