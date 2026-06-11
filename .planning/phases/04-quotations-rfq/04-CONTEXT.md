# Phase 4: Quotations (RFQ) - Context

**Gathered:** 2026-06-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Comprador executa o ciclo completo de RFQ — cria o processo vinculado a uma requisição aprovada, registra cotações de múltiplos fornecedores, visualiza comparativo de preços automático, e seleciona o vencedor com justificativa obrigatória (imutável após salvo). Tudo restrito a Comprador e Admin.

**Entrega:** fluxo completo de criação de RFQ → cotações → comparativo → seleção do vencedor funcionando end-to-end, auditável e sem possibilidade de edição do vencedor após seleção.

</domain>

<decisions>
## Implementation Decisions

### Campos da Cotação (COT-02)

- **D-01:** `condicoes_pagamento` = `CharField(max_length=200, blank=True)` — texto livre. O Comprador digita "à vista", "30/60/90 DDL", "30 dias" etc. Sem cadastro de opções.
- **D-02:** `prazo_entrega` = `CharField(max_length=100, blank=True)` — texto livre. Permite "imediato", "2 semanas", "30 dias úteis". Não ordena automaticamente no comparativo, mas é exibido lado a lado.
- **D-03:** Captura apenas `preco_unitario` (DecimalField) — sem campo de quantidade cotada. Quantidade vem da requisição. Campos completos da cotação: `fornecedor FK`, `preco_unitario`, `prazo_entrega`, `condicoes_pagamento`, `observacoes (TextField, blank=True)`.

### Ponto de Entrada e Acesso (COT-01)

- **D-04:** Tela principal `/cotacoes/` com listagem de RFQs do Comprador e botão "Nova Cotação". Ao criar, o Comprador seleciona a requisição num `<select>` filtrado por status=APROVADO e sem RFQ vinculado ainda. Nav lateral inclui "Cotações" visível apenas para Comprador e Admin.
- **D-05:** Acesso restrito a Comprador e Admin via `CompradorRequiredMixin` (já existe em `apps/fornecedores/views.py` — reutilizar diretamente).

### Estrutura do RFQ e Imutabilidade (COT-01, COT-04)

- **D-06:** `RFQ` tem `OneToOneField` para `Requisicao` — enforçado no DB. Tentativa de criar segundo RFQ para a mesma requisição levanta `IntegrityError` capturado na view.
- **D-07:** Vencedor armazenado como `RFQ.vencedor = FK(CotacaoFornecedor, null=True, blank=True)` + `RFQ.justificativa_selecao = TextField(blank=True)`. Após `rfq.vencedor` ser definido, qualquer tentativa de editar cotações ou selecionar novo vencedor é bloqueada na view (verificação `rfq.tem_vencedor`).
- **D-08 (Claude's discretion):** Cotações individuais (`CotacaoFornecedor`) podem ser adicionadas, editadas e removidas livremente **antes** da seleção do vencedor. Após seleção, RFQ fica somente leitura (sem DELETE/PUT nas cotações).

### Comparativo de Preços (COT-03)

- **D-09 (Claude's discretion):** Tabela comparativa renderizada na mesma página do RFQ (sem rota separada). Exibe colunas: Fornecedor, Preço Unitário, Prazo de Entrega, Condições de Pagamento, Delta %. Menor preço destacado com badge/cor de destaque (accent `#e94560` do dark theme). Delta calculado no template: `((preco - menor_preco) / menor_preco * 100)`. Botão "Selecionar Vencedor" em cada linha (inativo se já houver vencedor).
- **D-10 (Claude's discretion):** A tabela comparativa é estática (não atualiza via HTMX em tempo real). A página recarrega (ou usa hx-boost) após adicionar/remover cotação. Tabela vazia exibe mensagem orientativa "Adicione cotações de fornecedores para ver o comparativo".

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requisitos e Roadmap
- `.planning/REQUIREMENTS.md` §Cotações (RFQ) — COT-01..04 (escopo completo da fase)
- `.planning/ROADMAP.md` §Phase 4 — success criteria e dependências (depende de Phase 2 e Phase 3)

### Modelos existentes (integração direta)
- `apps/requisicoes/models.py` — `Requisicao` com `Status.APROVADO` (gatilho para criar RFQ) e campos `descricao`, `categoria`, `valor_estimado`, `unidade`
- `apps/fornecedores/models.py` — `Fornecedor` com `cnpj`, `razao_social`, `ativo` (FK em CotacaoFornecedor)
- `apps/core/models.py` — `TimestampedModel` (base para RFQ e CotacaoFornecedor), `AuditedModel` (se precisar rastrear criador)

### Padrões obrigatórios (fases anteriores)
- `apps/fornecedores/views.py` — `CompradorRequiredMixin` (reutilizar — não recriar)
- `apps/aprovacoes/services.py` — padrão de service layer: toda lógica de negócio em `services.py`, views apenas delegam. Usar `select_for_update()` na seleção do vencedor.
- `CLAUDE.md` §HTMX Patterns — Pattern 1 (form com feedback inline), Pattern 4 (live search para selecionar requisição e fornecedor no form)
- `apps/accounts/tests/conftest.py` — fixtures `comprador_user`, `solicitante_user` reutilizáveis nos testes

### Segurança
- `.planning/phases/01-foundation/01-REVIEW.md` — padrões de segurança a respeitar nos novos forms

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CompradorRequiredMixin` (`apps/fornecedores/views.py`): mixin pronto para restringir acesso — importar diretamente, não recriar
- `TimestampedModel` (`apps/core/models.py`): herdar para `RFQ` e `CotacaoFornecedor` — `criado_em` e `atualizado_em` gratuitos
- `get_queryset_fornecedores(apenas_ativos=True)` (`apps/fornecedores/views.py`): reutilizável no select de fornecedor do form de cotação
- Fixtures `comprador_user`, `fornecedor` em conftest: reutilizáveis nos testes da Fase 4
- Dark theme CSS: badge de menor preço usa `#e94560` (accent já definido no CSS)

### Established Patterns
- **Service layer:** toda lógica de negócio (validar vencedor único, bloquear edição pós-seleção) em `apps/cotacoes/services.py` — views finas
- **select_for_update + transaction.atomic:** obrigatório na seleção do vencedor para evitar race condition (dois Compradores selecionando simultaneamente)
- **DecimalField:** `preco_unitario = DecimalField(max_digits=12, decimal_places=2)` — nunca FloatField
- **HTMX partial responses:** adicionar cotação via POST HTMX e atualizar tabela comparativa via swap

### Integration Points
- `RFQ.requisicao` → `OneToOneField(Requisicao)` — garante unicidade no DB
- `CotacaoFornecedor.rfq` → `ForeignKey(RFQ, related_name='cotacoes')`
- `CotacaoFornecedor.fornecedor` → `ForeignKey(Fornecedor, on_delete=PROTECT)`
- `RFQ.vencedor` → `ForeignKey(CotacaoFornecedor, null=True, on_delete=SET_NULL)`
- Nav lateral em `templates/base.html` → adicionar link "Cotações" visível para `comprador` e `admin`
- `config/urls.py` → adicionar `path("cotacoes/", include("apps.cotacoes.urls"))`
- `config/settings/base.py` → adicionar `"apps.cotacoes"` em `INSTALLED_APPS`

</code_context>

<specifics>
## Specific Ideas

- O select de requisição no form "Nova Cotação" deve exibir: `#<pk> — <descrição[:40]> (R$ <valor_estimado>)` para que o Comprador identifique facilmente qual requisição cotar.
- Na listagem de RFQs (`/cotacoes/`), exibir status simplificado: "Em andamento" (sem vencedor) / "Encerrado" (vencedor selecionado) — não um campo de status separado, apenas propriedade derivada de `rfq.vencedor is not None`.
- Botão "Selecionar Vencedor" em cada linha da tabela comparativa deve abrir um modal de confirmação HTMX com campo de justificativa obrigatório (padrão modal já estabelecido na Fase 2 para aprovações).

</specifics>

<deferred>
## Deferred Ideas

- **Notificação ao Solicitante quando RFQ é encerrado** — v2 (NOTF-02 expandido)
- **Relatório de saving (menor preço vs. selecionado)** — Fase 5 ou v2 (FORN-V2-02)
- **Múltiplos itens por RFQ (linha por linha)** — v1 é um RFQ por requisição (item único); múltiplos itens seria extensão v2
- **Status explícito de RFQ (enum)** — derivado de `vencedor is not None`; se precisar de mais estados (ex: CANCELADO), entra em v2
- **Importação de planilha de cotações** — v2

</deferred>

---

*Phase: 4-Quotations-RFQ*
*Context gathered: 2026-06-11*
