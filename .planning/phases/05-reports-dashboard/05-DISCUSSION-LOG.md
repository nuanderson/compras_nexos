# Phase 5: Reports & Dashboard - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-11
**Phase:** 5-Reports-Dashboard
**Areas discussed:** KPI "Gasto do Mês", Dashboard por role, Período padrão, Escopo PDF

---

## KPI "Gasto do Mês"

| Opção | Descrição | Selecionada |
|-------|-----------|-------------|
| Preço real (vencedor da cotação) | Soma dos preco_unitario dos vencedores selecionados no mês | ✓ |
| Valor estimado (aprovações) | Soma do valor_estimado das requisições aprovadas no mês | |

**Escolha do usuário:** Preço real (vencedor da cotação)
**Notas:** Reflete o valor efetivamente comprometido para compra. Requer que a RFQ tenha vencedor definido.

---

## Dashboard com filtro de unidade (KPIs por role)

| Opção | Descrição | Selecionada |
|-------|-----------|-------------|
| Igual para todos (dados globais) | Todos veem os mesmos números — total geral da empresa | |
| Filtrado pela unidade do usuário | Solicitante vê dados da sua unidade; admin/comprador/diretor veem globais | ✓ |

**Escolha do usuário:** Filtrado pela unidade do usuário
**Notas:** Mais contextual — solicitante vê apenas sua unidade, roles de gestão veem visão global.

---

## Período padrão do relatório de gastos

| Opção | Descrição | Selecionada |
|-------|-----------|-------------|
| Mês corrente (padrão ajustável) | Abre com mês atual, usuário ajusta via campos de data | ✓ |
| Últimos 30 dias fixo | Janela deslizante de 30 dias sem ajuste de data de início | |
| Ano corrente até hoje | Acumulado anual | |

**Escolha do usuário:** Mês corrente (padrão ajustável)
**Notas:** Campos `data_inicio` e `data_fim` do tipo `<input type="date">` permitem ajuste livre.

---

## Escopo PDF

| Opção | Descrição | Selecionada |
|-------|-----------|-------------|
| Ambos: gastos e painel de requisições | Cada relatório tem seu próprio botão "Exportar PDF" | ✓ |
| Apenas relatório de gastos | Painel de requisições sem PDF | |

**Escolha do usuário:** Ambos os relatórios exportam PDF
**Notas:** Dois endpoints: `/relatorios/gastos/pdf/` e `/relatorios/requisicoes/pdf/`. Filtros passados como GET params.

---

## Claude's Discretion

- **App `relatorios`:** app Django dedicado sem models — importa de todos os outros apps
- **Service layer:** `apps/relatorios/services.py` centraliza todas as queries de agregação
- **Dashboard:** atualizar `DashboardView` existente com `get_context_data()` — não criar nova view
- **Agrupamento de gastos:** por `CategoriaCompra` da requisição vinculada à RFQ
- **PDF:** ReportLab Platypus com `SimpleDocTemplate` + `Table` + `FileResponse`

## Deferred Ideas

- Exportação CSV/Excel — v2 (REL-V2-01)
- Indicadores de SLA de aprovação — v2 (REL-V2-02)
- Comparativo de gasto entre unidades — v2 (REL-V2-03)
- Relatório de saving — v2 (FORN-V2-02)
