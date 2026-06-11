---
phase: 04
slug: quotations-rfq
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-11
---

# Phase 04 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest-django (configurado em `pytest.ini`) |
| **Config file** | `pytest.ini` (raiz do projeto) |
| **Quick run command** | `pytest apps/cotacoes/ -x -q` |
| **Full suite command** | `pytest --tb=short -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest apps/cotacoes/ -x -q`
- **After every plan wave:** Run `pytest --tb=short -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | COT-01 | T-04-01 | CompradorRequiredMixin → 403 para Solicitante | unit | `pytest apps/cotacoes/tests/test_views.py::TestNovaRFQView::test_acesso_negado_solicitante -x` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | COT-01 | T-04-02 | OneToOneField → IntegrityError em segundo RFQ | unit | `pytest apps/cotacoes/tests/test_services.py::TestCriarRFQDuplicado -x` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 1 | COT-01 | — | Select filtra apenas APROVADO e sem RFQ | unit | `pytest apps/cotacoes/tests/test_views.py::TestNovaRFQView::test_select_filtra_aprovadas_sem_rfq -x` | ❌ W0 | ⬜ pending |
| 04-01-04 | 01 | 1 | COT-02 | T-04-03 | Bloquear add/remove após vencedor (403) | unit | `pytest apps/cotacoes/tests/test_views.py::TestBloqueioPosSeletcao -x` | ❌ W0 | ⬜ pending |
| 04-01-05 | 01 | 1 | COT-02 | — | Adicionar cotação retorna HX-Redirect para detalhe | unit | `pytest apps/cotacoes/tests/test_views.py::TestAdicionarCotacaoView -x` | ❌ W0 | ⬜ pending |
| 04-01-06 | 01 | 1 | COT-02 | — | Remover cotação retorna HX-Redirect para detalhe | unit | `pytest apps/cotacoes/tests/test_views.py::TestRemoverCotacaoView -x` | ❌ W0 | ⬜ pending |
| 04-01-07 | 01 | 1 | COT-03 | T-04-04 | Delta % = 0 quando preco=0 (guard divisão por zero) | unit | `pytest apps/cotacoes/tests/test_services.py::TestDeltaZero -x` | ❌ W0 | ⬜ pending |
| 04-01-08 | 01 | 1 | COT-03 | — | calcular_comparativo retorna menor preço com is_menor=True | unit | `pytest apps/cotacoes/tests/test_services.py::TestCalcularComparativo -x` | ❌ W0 | ⬜ pending |
| 04-01-09 | 01 | 1 | COT-03 | — | Delta % correto para 2+ fornecedores | unit | `pytest apps/cotacoes/tests/test_services.py::TestDeltaPercentual -x` | ❌ W0 | ⬜ pending |
| 04-01-10 | 01 | 1 | COT-04 | T-04-05 | selecionar_vencedor usa select_for_update + atomic | unit | `pytest apps/cotacoes/tests/test_services.py::TestSelecionarVencedor -x` | ❌ W0 | ⬜ pending |
| 04-01-11 | 01 | 1 | COT-04 | T-04-06 | ValueError se já há vencedor (imutabilidade) | unit | `pytest apps/cotacoes/tests/test_services.py::TestVencedorImutavel -x` | ❌ W0 | ⬜ pending |
| 04-01-12 | 01 | 1 | COT-04 | — | Justificativa vazia levanta ValueError | unit | `pytest apps/cotacoes/tests/test_services.py::TestJustificativaObrigatoria -x` | ❌ W0 | ⬜ pending |
| 04-01-13 | 01 | 1 | COT-04 | — | Modal seleção: GET partial, POST confirma e redireciona | unit | `pytest apps/cotacoes/tests/test_views.py::TestModalSelecionarVencedor -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/cotacoes/__init__.py`
- [ ] `apps/cotacoes/tests/__init__.py`
- [ ] `apps/cotacoes/tests/conftest.py` — fixtures `rfq`, `cotacao_fornecedor`, `requisicao_aprovada`, `comprador_user`, `fornecedor`
- [ ] `apps/cotacoes/tests/test_models.py` — stubs para COT-01..04
- [ ] `apps/cotacoes/tests/test_services.py` — stubs para lógica de negócio
- [ ] `apps/cotacoes/tests/test_views.py` — stubs para views
- [ ] Framework já instalado — nenhuma nova instalação necessária

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Tabela comparativa destaca menor preço visualmente | COT-03 | Verificação visual de CSS/badge | Acesse /cotacoes/<pk>/ com 2+ cotações, confirmar badge accent (#e94560) na linha menor |
| Add/remove cotação sem reload de página | COT-02 | Comportamento HTMX no browser | Adicionar cotação e confirmar que apenas a tabela atualiza via HX-Redirect |
| Botão "Selecionar Vencedor" fica desabilitado após seleção | COT-04 | Comportamento visual | Selecionar vencedor, confirmar que botões de seleção ficam ocultos/desabilitados |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
