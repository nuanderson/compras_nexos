# Phase 4: Quotations (RFQ) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-11
**Phase:** 4-Quotations-RFQ
**Areas discussed:** Campos da cotação, Ponto de entrada do RFQ

---

## Campos da Cotação

| Opção | Descrição | Selecionado |
|-------|-----------|-------------|
| Texto livre | CharField — Comprador digita "30 dias", "à vista", "30/60/90 DDL" | ✓ |
| Select configurável pelo Admin | Modelo separado de opções de pagamento | |
| Sem campo (opcional) | Apenas preço unitário e prazo de entrega | |

**Escolha do usuário:** Texto livre  
**Notas:** Flexibilidade necessária para a realidade brasileira de negociação.

---

| Opção | Descrição | Selecionado |
|-------|-----------|-------------|
| Número de dias | IntegerField — ex: 15 dias | |
| Data de entrega | DateField — data exata prometida | |
| Texto livre | CharField — "2 semanas", "imediato", "30 dias úteis" | ✓ |

**Escolha do usuário:** Texto livre  
**Notas:** Flexibilidade preferida sobre precisão estrutural.

---

| Opção | Descrição | Selecionado |
|-------|-----------|-------------|
| Só preço unitário | Simples — quantidade vem da requisição | ✓ |
| Preço unitário + quantidade cotada | Permite fornecedor cotar quantidade diferente | |

**Escolha do usuário:** Só preço unitário

---

## Ponto de Entrada do RFQ

| Opção | Descrição | Selecionado |
|-------|-----------|-------------|
| Tela de Cotações com botão "Nova Cotação" | /cotacoes/ como hub central do Comprador | ✓ |
| Botão na requisição aprovada | Na página de detalhe da requisição | |

**Escolha do usuário:** Tela de Cotações com botão "Nova Cotação"

---

| Opção | Descrição | Selecionado |
|-------|-----------|-------------|
| Só Comprador e Admin | Operação interna do Comprador | ✓ |
| Todos os perfis (leitura para outros) | Solicitante/Gestor acompanham o andamento | |

**Escolha do usuário:** Só Comprador e Admin

---

## Claude's Discretion

- **Mutabilidade das cotações:** cotações editáveis/removíveis antes da seleção do vencedor; RFQ somente leitura após seleção
- **Comparativo estático (não HTMX em tempo real):** página recarrega após adicionar cotação — complexidade não justificada para v1
- **Status do RFQ derivado:** propriedade `tem_vencedor` em vez de enum de status separado

## Deferred Ideas

- Notificação ao Solicitante quando RFQ é encerrado → v2
- Relatório de saving (menor preço vs. selecionado) → Fase 5 ou v2
- Múltiplos itens por RFQ → v2
- Importação de planilha de cotações → v2
