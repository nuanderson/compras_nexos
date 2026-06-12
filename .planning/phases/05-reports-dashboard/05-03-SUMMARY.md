---
phase: 05-reports-dashboard
plan: "03"
subsystem: relatorios/pdf
tags: [pdf, reportlab, platypus, relatorios, download]
dependency_graph:
  requires: ["05-01", "05-02"]
  provides: ["apps/relatorios/pdf.py", "GastosPDFView real", "RequisicoesPDFView real"]
  affects: ["apps/relatorios/views.py"]
tech_stack:
  added: ["reportlab==4.5.1"]
  patterns: ["ReportLab Platypus BytesIO", "FileResponse as_attachment"]
key_files:
  created:
    - apps/relatorios/pdf.py
  modified:
    - apps/relatorios/views.py
    - requirements.txt
decisions:
  - "reportlab adicionado a requirements.txt (ausente — desvio Rule 2)"
  - "HttpResponse removida de views.py após remoção dos stubs 501"
metrics:
  duration: "11 minutos"
  completed: "2026-06-12"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 3
---

# Phase 05 Plan 03: PDF Export — Exportação PDF dos Relatórios

**One-liner:** Exportação PDF via ReportLab Platypus (SimpleDocTemplate + Table + KeepTogether) em BytesIO, servida por FileResponse com Content-Disposition attachment para gastos por categoria e painel de requisições.

## Summary

Terceira fatia vertical da Fase 5. Substituiu os stubs HTTP 501 em `GastosPDFView` e `RequisicoesPDFView` por implementações reais que:

1. Reutilizam o mesmo parsing de filtros GET (`_parse_filtros`) e o mesmo service layer das views web (D-06).
2. Delegam a geração do PDF ao novo módulo `apps/relatorios/pdf.py` — isolado da camada de views.
3. Servem o buffer BytesIO via `FileResponse(as_attachment=True)` — forçando download com Content-Disposition attachment (D-07, T-05-09).

`apps/relatorios/pdf.py` criado do zero como o primeiro módulo PDF do projeto, seguindo o padrão CLAUDE.md §PDF Generation. As views permanecem finas — chamam o service e o builder, nada mais.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Builders de PDF (ReportLab Platypus) em apps/relatorios/pdf.py | b04284d | apps/relatorios/pdf.py, requirements.txt |
| 2 | Implementar GastosPDFView e RequisicoesPDFView (substituir stubs) | 220310b | apps/relatorios/views.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Dependency] reportlab ausente do requirements.txt**

- **Found during:** Task 1 — verificação automatizada (`docker compose exec web python -c "from apps.relatorios import pdf"`) falhou com `ModuleNotFoundError: No module named 'reportlab'`.
- **Issue:** O plano afirma "reportlab is already in requirements.txt — no new packages needed", mas o arquivo `requirements.txt` não continha `reportlab`. O pacote é definido pelo cliente como mandatório (CLAUDE.md §PDF Generation) e é crítico para a funcionalidade REL-04.
- **Fix:** Adicionado `reportlab` ao `requirements.txt` na seção `# PDF`. Instalado no container em execução via `pip install reportlab` (versão 4.5.1 instalada).
- **Files modified:** `requirements.txt`
- **Commit:** b04284d

**2. [Rule 1 - Cleanup] Removido import HttpResponse desnecessário**

- **Found during:** Task 2 — após substituição dos stubs, `HttpResponse` não era mais referenciada em nenhum lugar do arquivo.
- **Fix:** Removido do import em `views.py`.
- **Files modified:** `apps/relatorios/views.py`
- **Commit:** 220310b

## Verification Results

| Check | Result |
|-------|--------|
| `pdf.build_gastos_pdf(...)` retorna bytes `%PDF` | PASSOU |
| `_formato_brl(Decimal('1500.00'))` == `'R$ 1.500,00'` | PASSOU |
| `_formato_brl(Decimal('12345.67'))` == `'R$ 12.345,67'` | PASSOU |
| `pytest apps/relatorios/tests/test_views.py` — 12/12 | PASSOU |
| Suite completa `pytest` — 199/199 | PASSOU (sem regressão) |

### TestPDF — GREEN

- `test_pdf_gastos_content_type` — Content-Type: application/pdf
- `test_pdf_gastos_attachment` — Content-Disposition: attachment
- `test_pdf_requisicoes_content_type` — Content-Type: application/pdf

## Known Stubs

Nenhum. Os dois endpoints PDF geram conteúdo real (ReportLab Platypus, BytesIO), as views chamam o service layer real, e os testes passam com dados reais de banco.

## Threat Flags

Nenhuma nova superfície de segurança introduzida. Os endpoints PDF reutilizam:
- `RelatorioRequiredMixin` (403 para solicitante/gestor) — T-05-07
- `_parse_filtros` com validação strptime — T-05-08
- BytesIO in-memory, sem escrita em disco — T-05-09

## Self-Check: PASSED
