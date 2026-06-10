# Requirements: ComprasNexos

**Defined:** 2026-06-10
**Core Value:** Dar ao comprador controle total do ciclo de compra — da requisição aprovada até a seleção do fornecedor — eliminando o fluxo manual por e-mail e planilha.

## v1 Requirements

### Autenticação e Perfis

- [ ] **AUTH-01**: Usuário faz login com e-mail e senha
- [ ] **AUTH-02**: Usuário recupera senha via link por e-mail
- [ ] **AUTH-03**: Sessão permanece ativa entre atualizações do navegador
- [ ] **AUTH-04**: Admin cria, edita e desativa contas de usuários
- [ ] **AUTH-05**: Sistema suporta 5 perfis: Solicitante, Gestor, Comprador, Diretor, Admin
- [ ] **AUTH-06**: Cada usuário está vinculado a uma unidade padrão

### Unidades

- [ ] **UNIT-01**: Admin cadastra unidades (nome, descrição, status ativo/inativo)
- [ ] **UNIT-02**: Admin vincula usuários a unidades
- [ ] **UNIT-03**: Usuário tem unidade padrão pré-selecionada ao abrir requisição, mas pode alterá-la
- [ ] **UNIT-04**: Relatórios podem ser filtrados por unidade

### Requisições de Compra

- [ ] **REQ-01**: Solicitante abre requisição com: descrição, categoria, valor estimado, justificativa e unidade
- [ ] **REQ-02**: Solicitante acompanha status da sua requisição em tempo real
- [ ] **REQ-03**: Sistema registra histórico de aprovações (quem aprovou/reprovou, quando e com qual motivo)
- [ ] **REQ-04**: Sistema envia e-mail ao Gestor responsável quando nova requisição é criada

### Aprovações

- [ ] **APROV-01**: Gestor visualiza fila de requisições aguardando seu parecer
- [ ] **APROV-02**: Gestor aprova ou reprova requisição (1º nível)
- [ ] **APROV-03**: Diretor visualiza fila de requisições aprovadas pelo Gestor aguardando seu parecer
- [ ] **APROV-04**: Diretor aprova ou reprova requisição (2º nível)
- [ ] **APROV-05**: Reprovação em qualquer nível exige motivo obrigatório
- [ ] **APROV-06**: Admin configura alçadas de aprovação por valor via painel administrativo (sem necessidade de deploy)

### Fornecedores

- [ ] **FORN-01**: Comprador cadastra fornecedores com CNPJ validado, razão social, e-mail e telefone
- [ ] **FORN-02**: Sistema valida CNPJ usando python-stdnum (suporta formato alfanumérico de julho/2026)
- [ ] **FORN-03**: Comprador organiza fornecedores por categorias configuráveis
- [ ] **FORN-04**: Comprador ativa ou inativa fornecedores sem perder histórico
- [ ] **FORN-05**: Comprador busca e filtra fornecedores por nome, CNPJ ou categoria

### Cotações (RFQ)

- [ ] **COT-01**: Comprador cria RFQ vinculado a uma requisição aprovada (um RFQ por requisição)
- [ ] **COT-02**: Comprador registra cotações de múltiplos fornecedores com: preço unitário, prazo de entrega e condições de pagamento
- [ ] **COT-03**: Sistema exibe comparativo de cotações com destaque automático do menor preço e delta percentual entre fornecedores
- [ ] **COT-04**: Comprador seleciona fornecedor vencedor com justificativa obrigatória (imutável após salvo)

### Estoque

- [ ] **EST-01**: Solicitante cadastra itens de estoque da sua unidade com: nome, unidade de medida e quantidade atual
- [ ] **EST-02**: Solicitante define quantidade mínima (ponto de pedido) por item
- [ ] **EST-03**: Solicitante atualiza quantidades de estoque manualmente
- [ ] **EST-04**: Sistema destaca itens abaixo da quantidade mínima configurada
- [ ] **EST-05**: Cada unidade vê somente o próprio estoque
- [ ] **EST-06**: Comprador e Admin têm visão consolidada do estoque de todas as unidades

### Relatórios

- [ ] **REL-01**: Dashboard exibe KPIs: requisições abertas, cotações em andamento, gasto do mês e fornecedores ativos
- [ ] **REL-02**: Relatório de gasto por categoria e período, filtrável por unidade
- [ ] **REL-03**: Painel de status de todas as requisições com filtro por status e unidade
- [ ] **REL-04**: Relatórios podem ser exportados em PDF com layout formatado via ReportLab

---

## v2 Requirements

### Notificações Expandidas

- **NOTF-01**: Solicitante recebe e-mail quando sua requisição é aprovada ou reprovada
- **NOTF-02**: Comprador recebe e-mail quando cotação aguarda conclusão com prazo próximo
- **NOTF-03**: Usuário configura preferências de notificação

### Estoque Avançado

- **EST-V2-01**: Histórico de movimentações de estoque (entrada/saída com data e responsável)
- **EST-V2-02**: Alerta automático de estoque baixo gera sugestão de requisição
- **EST-V2-03**: Valor unitário e cálculo de valor total do estoque

### Fornecedores Avançado

- **FORN-V2-01**: Avaliação de fornecedor após compra (rating com critérios configuráveis)
- **FORN-V2-02**: Relatório de saving (menor preço cotado vs. preço selecionado)

### Relatórios Avançados

- **REL-V2-01**: Exportação CSV/Excel dos relatórios
- **REL-V2-02**: Indicadores de SLA de aprovação (tempo médio por nível)
- **REL-V2-03**: Comparativo de gasto entre unidades

### Integração

- **INT-V2-01**: API para integração com sistema externo do instituto (a identificar)

---

## Out of Scope

| Feature | Motivo |
|---------|--------|
| Portal externo para fornecedores | Sistema interno; fornecedor interage somente com o Comprador fora do sistema |
| Emissão de Ordem de Compra (PO) em PDF | Fluxo validado primeiro; entra pós-fase 1 se necessário |
| Integração com ERP ou sistema financeiro | Sistema não identificado ainda; entrada por API em v2 |
| Orçamento automático por departamento (budget enforcement) | Cliente sem definição; implementar como feature configurável em v2 |
| Bloqueio de requisição por orçamento | Sem regra de negócio definida; sistema apenas informa, não bloqueia |
| 2FA / SSO | Não requerido para o porte atual (20 usuários internos) |
| App mobile | Web-first; responsividade via HTMX suficiente |
| NFe / SEFAZ | Responsabilidade do fornecedor; comprador apenas armazena chave de acesso se necessário (v2) |
| Notificação ao solicitante de aprovação/reprovação por e-mail | Acompanhamento via painel; e-mail entra em v2 |

---

## Traceability

Mapeamento atualizado após criação do roadmap — 2026-06-10.

| Requisito | Fase | Nome da Fase | Status |
|-----------|------|--------------|--------|
| AUTH-01 | Phase 1 | Foundation | Pending |
| AUTH-02 | Phase 1 | Foundation | Pending |
| AUTH-03 | Phase 1 | Foundation | Pending |
| AUTH-04 | Phase 1 | Foundation | Pending |
| AUTH-05 | Phase 1 | Foundation | Pending |
| AUTH-06 | Phase 1 | Foundation | Pending |
| UNIT-01 | Phase 1 | Foundation | Pending |
| UNIT-02 | Phase 1 | Foundation | Pending |
| UNIT-03 | Phase 1 | Foundation | Pending |
| REQ-01 | Phase 2 | Requisitions & Approvals | Pending |
| REQ-02 | Phase 2 | Requisitions & Approvals | Pending |
| REQ-03 | Phase 2 | Requisitions & Approvals | Pending |
| REQ-04 | Phase 2 | Requisitions & Approvals | Pending |
| APROV-01 | Phase 2 | Requisitions & Approvals | Pending |
| APROV-02 | Phase 2 | Requisitions & Approvals | Pending |
| APROV-03 | Phase 2 | Requisitions & Approvals | Pending |
| APROV-04 | Phase 2 | Requisitions & Approvals | Pending |
| APROV-05 | Phase 2 | Requisitions & Approvals | Pending |
| APROV-06 | Phase 2 | Requisitions & Approvals | Pending |
| FORN-01 | Phase 3 | Suppliers & Inventory | Pending |
| FORN-02 | Phase 3 | Suppliers & Inventory | Pending |
| FORN-03 | Phase 3 | Suppliers & Inventory | Pending |
| FORN-04 | Phase 3 | Suppliers & Inventory | Pending |
| FORN-05 | Phase 3 | Suppliers & Inventory | Pending |
| EST-01 | Phase 3 | Suppliers & Inventory | Pending |
| EST-02 | Phase 3 | Suppliers & Inventory | Pending |
| EST-03 | Phase 3 | Suppliers & Inventory | Pending |
| EST-04 | Phase 3 | Suppliers & Inventory | Pending |
| EST-05 | Phase 3 | Suppliers & Inventory | Pending |
| EST-06 | Phase 3 | Suppliers & Inventory | Pending |
| COT-01 | Phase 4 | Quotations (RFQ) | Pending |
| COT-02 | Phase 4 | Quotations (RFQ) | Pending |
| COT-03 | Phase 4 | Quotations (RFQ) | Pending |
| COT-04 | Phase 4 | Quotations (RFQ) | Pending |
| REL-01 | Phase 5 | Reports & Dashboard | Pending |
| REL-02 | Phase 5 | Reports & Dashboard | Pending |
| REL-03 | Phase 5 | Reports & Dashboard | Pending |
| REL-04 | Phase 5 | Reports & Dashboard | Pending |
| UNIT-04 | Phase 5 | Reports & Dashboard | Pending |

**Coverage:**
- v1 requirements: 39 total
- Mapped to phases: 39
- Unmapped: 0

---
*Requirements defined: 2026-06-10*
*Last updated: 2026-06-10 after roadmap creation — traceability finalized*
