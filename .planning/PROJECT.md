# ComprasNexos

## What This Is

Sistema de gestão de compras para cliente corporativo de pequeno porte (até 20 usuários). Permite que solicitantes abram requisições de compra, gestores e diretores aprovem em dois níveis, compradores gerenciem cotações com fornecedores, e que a empresa tenha visibilidade total dos gastos por categoria. Desenvolvido com Python/Django + HTMX, hospedado na AWS via Docker.

## Core Value

Dar ao comprador controle total do ciclo de compra — da requisição aprovada até a seleção do fornecedor — eliminando o fluxo manual por e-mail e planilha.

## Requirements

### Validated

(None yet — ship to validate)

### Active

**Autenticação e Perfis**
- [ ] Usuário faz login com e-mail e senha
- [ ] Sistema suporta 5 perfis: Solicitante, Gestor, Comprador, Diretor, Admin
- [ ] Admin gerencia usuários e configurações de alçadas

**Requisições de Compra**
- [ ] Solicitante abre requisição com descrição, categoria, valor estimado e justificativa
- [ ] Solicitante acompanha status da sua requisição em tempo real
- [ ] Sistema envia e-mail ao Gestor quando nova requisição é criada
- [ ] Gestor pode aprovar ou reprovar requisição (1º nível)
- [ ] Diretor pode aprovar ou reprovar requisição (2º nível, após Gestor)
- [ ] Admin configura alçadas de aprovação por valor (valores a definir com cliente)

**Fornecedores**
- [ ] Comprador cadastra fornecedores com CNPJ, categorias e dados de contato
- [ ] Sistema suporta categorias de fornecedores configuráveis
- [ ] Comprador registra avaliação de fornecedor após cada compra

**Cotações (RFQ)**
- [ ] Comprador cria RFQ vinculado a uma requisição aprovada
- [ ] Comprador registra cotações de múltiplos fornecedores
- [ ] Sistema exibe comparativo de preços entre cotações
- [ ] Comprador seleciona fornecedor vencedor com justificativa
- [ ] Histórico de cotações fica acessível para auditoria

**Relatórios**
- [ ] Dashboard com KPIs: requisições abertas, cotações em andamento, gasto do mês, fornecedores ativos
- [ ] Relatório de gasto por categoria e centro de custo no período
- [ ] Painel de status das requisições (abertas, em aprovação, aprovadas, reprovadas)
- [ ] Comparativo de cotações — menor preço vs. preço selecionado
- [ ] Exportação de relatórios em PDF com ReportLab

### Out of Scope

- Portal externo para fornecedores — sem acesso web; comprador é o ponto de contato
- Emissão de Ordem de Compra (PO) em PDF — fase futura após validação do fluxo
- Notificações por e-mail de aprovação/reprovação ao solicitante — v2
- Integração com ERP ou sistema financeiro — sistema identificado ainda não confirmado, fica pós-fase 1
- Orçamento automático por departamento — sem decisão do cliente, implementar como feature configurável futura
- 2FA e SSO — não requerido para porte atual

## Context

- Cliente de pequeno porte, ambiente corporativo interno, sem acesso externo ao sistema
- Fornecedores interagem somente com o Comprador fora do sistema (e-mail, telefone); o Comprador registra as cotações
- Alçadas de aprovação por valor ainda a serem definidas pelo cliente — sistema precisa ser flexível para que Admin configure os valores sem deploy
- Existe um sistema externo futuro a ser integrado (nome não confirmado ainda) — arquitetura deve prever APIs limpas
- Interface deve ser funcional e profissional; HTMX garante interatividade sem complexidade de SPA
- Deploy via Docker facilita portabilidade entre EC2 e ECS conforme cliente decidir

## Constraints

- **Tech Stack**: Python 3.12 + Django 5.x + HTMX + PostgreSQL + Docker — definido pelo cliente, não negociável
- **Escala**: Até 20 usuários simultâneos — não requer sharding, cache agressivo ou filas complexas no v1
- **Deploy**: AWS (configuração EC2 vs ECS a confirmar) — Docker é o contrato de entrega
- **Usuários**: Sistema interno corporativo — sem registro público, usuários criados pelo Admin
- **Relatórios**: ReportLab para PDF — biblioteca definida pelo cliente

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| HTMX em vez de React/Vue | Evita complexidade de SPA para 20 usuários; Django renderiza tudo no servidor | — Pending |
| Apps Django por módulo | Separação clara: requisicoes, aprovacoes, fornecedores, cotacoes, relatorios, accounts | — Pending |
| Alçadas configuráveis via Admin | Cliente ainda não definiu valores; Admin panel do Django resolve sem code change | — Pending |
| PostgreSQL no RDS | Banco gerenciado facilita backup e manutenção para cliente sem equipe técnica interna | — Pending |

## Evolution

Este documento evolui a cada transição de fase e milestone.

**Após cada fase** (via `/gsd-transition`):
1. Requisitos invalidados? → Mover para Out of Scope com motivo
2. Requisitos validados? → Mover para Validated com referência à fase
3. Novos requisitos emergiram? → Adicionar em Active
4. Decisões a registrar? → Adicionar em Key Decisions
5. "What This Is" ainda preciso? → Atualizar se mudou

**Após cada milestone** (via `/gsd-complete-milestone`):
1. Revisão completa de todas as seções
2. Core Value check — ainda é a prioridade certa?
3. Auditoria de Out of Scope — razões ainda válidas?
4. Atualizar Context com estado atual

---
*Last updated: 2026-06-09 after initialization*
