---
phase: 03-suppliers-inventory
verified: 2026-06-11T12:00:00Z
status: human_needed
score: 11/11 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 10/11
  gaps_closed:
    - "Comprador pode inativar/reativar fornecedor via HTMX sem perder o registro (FORN-04)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Acessar /fornecedores/ como comprador, digitar um nome parcial no campo de busca"
    expected: "Lista atualiza dinamicamente sem reload após 300ms de inatividade"
    why_human: "django-htmx + HtmxMiddleware necessários; comportamento de request.htmx não verificável por grep"
  - test: "Clicar em 'Inativar' em um fornecedor da lista, confirmar o diálogo, depois marcar 'Mostrar fornecedores inativos' e clicar em 'Reativar'"
    expected: "Ao inativar: linha atualiza via outerHTML swap, status muda para 'Inativo'. Ao mostrar inativos: fornecedor inativado aparece na lista. Ao reativar: status volta a 'Ativo'."
    why_human: "Comportamento de swap HTMX, confirmação JS, e visibilidade condicional requerem navegador"
  - test: "Na listagem de estoque, alterar o valor no campo de quantidade de um item abaixo do mínimo e clicar em Salvar"
    expected: "A linha atualiza via HTMX outerHTML swap; se item ficar acima do mínimo, destaque vermelho desaparece"
    why_human: "Comportamento de swap HTMX e estilo condicional requerem navegador"
---

# Fase 03: Suppliers & Inventory — Relatório de Verificação

**Objetivo da Fase:** Cadastro de fornecedores com validação de CNPJ, busca/filtro, e controle de estoque por unidade com alertas de quantidade mínima
**Verificado em:** 2026-06-11
**Status:** human_needed
**Re-verificação:** Sim — após fechamento do gap FORN-04

---

## Conquista do Objetivo

### Verdades Observáveis

| #  | Verdade | Status | Evidência |
|----|---------|--------|-----------|
| 1  | Comprador cadastra fornecedor com CNPJ válido (numérico e alfanumérico Jul/2026) | VERIFICADO | `forms.py:55` `cnpj_lib.validate(valor)` via `stdnum.br.cnpj`; `models.py:25` cnpj=CharField(max_length=14, unique=True) |
| 2  | Formulário rejeita CNPJ inválido com mensagem clara e rejeita CNPJ duplicado | VERIFICADO | `forms.py:57` `raise forms.ValidationError("CNPJ inválido. Verifique os dígitos.")` e `forms.py:64` mensagem de unicidade; captura apenas `StdnumValidationError` |
| 3  | Comprador busca fornecedores por nome (fuzzy pg_trgm) ou CNPJ (exato) | VERIFICADO | `views.py:70-73` TrigramSimilarity anotado com threshold 0.1; busca exata por CNPJ de 14 chars; truncamento a 100 chars anti-DoS |
| 4  | Comprador filtra fornecedores por categoria | VERIFICADO | `views.py:60-61` `qs.filter(categoria_id=categoria_pk)`; select de categoria em `lista.html:43-58` com hx-trigger="change" |
| 5  | Comprador pode inativar/reativar fornecedor via HTMX sem perder o registro | VERIFICADO | `views.py:44` `apenas_ativos=True` (padrão); `views.py:94-98` lê `mostrar_inativos` do GET e passa `apenas_ativos=not mostrar_inativos`; `lista.html:63-78` checkbox "Mostrar fornecedores inativos" com name="mostrar_inativos" value="1"; `fornecedor_row.html:32` botão condicional "Inativar"/"Reativar" |
| 6  | CNPJ exibido formatado nos templates via filtro cnpj_format | VERIFICADO | `templatetags/fornecedor_tags.py` filtro registrado; `fornecedor_row.html:4` `{{ fornecedor.cnpj|cnpj_format }}`; `fornecedor_list.html:1` `{% load fornecedor_tags %}` |
| 7  | Solicitante recebe 403 em qualquer URL de fornecedores — CompradorRequiredMixin | VERIFICADO | `views.py:25-41` CompradorRequiredMixin.dispatch() lança PermissionDenied se role not in ("comprador","admin") e not is_superuser |
| 8  | Item de estoque com quantidade_atual < quantidade_minima tem abaixo_do_minimo=True | VERIFICADO | `estoque/models.py:68-71` `@property abaixo_do_minimo` retorna `self.quantidade_atual < self.quantidade_minima` |
| 9  | Atualização de quantidade usa select_for_update() dentro de transaction.atomic() | VERIFICADO | `estoque/views.py:127-137` `with transaction.atomic()` + `ItemEstoque.objects.select_for_update()` |
| 10 | Solicitante NÃO acessa itens de outra unidade via URL manipulation | VERIFICADO | `estoque/views.py:91-95` `get_object_or_404(ItemEstoque, pk=pk, unidade_organizacional=user.default_unit)`; Comprador/Admin sem restrição conforme spec |
| 11 | Comprador vê itens de todas as unidades na visão consolidada | VERIFICADO | `estoque/views.py:154-179` VisaoConsolidadaView com dispatch() que lança PermissionDenied para não-comprador/admin; queryset sem filtro de unidade |

**Pontuação:** 11/11 verdades verificadas

---

## Gap Fechado: FORN-04

A re-verificação confirma que todos os três componentes do fix foram implementados corretamente:

1. **`get_queryset_fornecedores()` recebe parâmetro `apenas_ativos=True`** (linha 44 de `views.py`) — o padrão `True` preserva o comportamento anterior para todos os usos existentes, e o bloco `if apenas_ativos: qs = qs.filter(ativo=True)` (linha 57-58) só aplica o filtro quando necessário.

2. **`ListaFornecedoresView.get()` lê `mostrar_inativos` do GET** (linha 94) — `mostrar_inativos = request.GET.get("mostrar_inativos", "") == "1"` e passa `apenas_ativos=not mostrar_inativos` (linha 98), expondo corretamente inativos quando o parâmetro está ativo.

3. **`templates/fornecedores/lista.html` tem checkbox de inativos** (linhas 63-78) — `<input type="checkbox" name="mostrar_inativos" value="1">` com `{% if mostrar_inativos %}checked{% endif %}`, integrado ao HTMX via `hx-include="[name='q'],[name='categoria']"`. O campo de busca e o select de categoria também incluem `[name='mostrar_inativos']` via `hx-include`, garantindo que todos os filtros HTMX mantenham o estado do checkbox.

---

## Artefatos Obrigatórios

| Artefato | Esperado | Status | Detalhes |
|----------|----------|--------|----------|
| `apps/fornecedores/models.py` | Fornecedor(TimestampedModel) com cnpj, razao_social, email, telefone, categoria FK, ativo | VERIFICADO | Todos os campos presentes; `on_delete=PROTECT`; `ordering=["razao_social"]` |
| `apps/fornecedores/forms.py` | FornecedorForm com clean_cnpj via stdnum.validate | VERIFICADO | `from stdnum.br import cnpj as cnpj_lib`; captura `StdnumValidationError`; unicidade com exclusão do pk próprio |
| `apps/fornecedores/views.py` | CompradorRequiredMixin + 4 views + apenas_ativos param | VERIFICADO | ListaFornecedoresView, CadastrarFornecedorView, EditarFornecedorView, ToggleAtivoView; todos com CompradorRequiredMixin; `get_queryset_fornecedores` com `apenas_ativos=True` padrão e lógica condicional |
| `apps/fornecedores/templatetags/fornecedor_tags.py` | Filtro cnpj_format | VERIFICADO | `@register.filter(name="cnpj_format")` usando `cnpj_lib.format()` com fallback seguro |
| `apps/fornecedores/migrations/0001_initial.py` | Migration do modelo Fornecedor | VERIFICADO | Depende de accounts+requisicoes; cria tabela com todos os campos; índices em ativo e categoria |
| `templates/fornecedores/lista.html` | Página de listagem com HTMX live search e toggle inativos | VERIFICADO | hx-get, hx-trigger="input delay:300ms, search", hx-target="#fornecedores-list"; checkbox "Mostrar fornecedores inativos" com name="mostrar_inativos" |
| `templates/fornecedores/partials/fornecedor_list.html` | Partial retornada pelo HTMX | VERIFICADO | `{% load fornecedor_tags %}`; tabela com cnpj_format; mensagem vazio presente |
| `apps/estoque/models.py` | UnidadeMedida + ItemEstoque(TimestampedModel) | VERIFICADO | Ambos os modelos; abaixo_do_minimo property; UniqueConstraint |
| `apps/estoque/forms.py` | ItemEstoqueForm + AtualizarQuantidadeForm | VERIFICADO | clean_quantidade_atual valida >= 0 em ambos os forms; unidade_medida filtrada por ativo=True |
| `apps/estoque/views.py` | 4+ views com isolamento de unidade | VERIFICADO | select_for_update em AtualizarQuantidadeView; IDOR guard; PermissionDenied em VisaoConsolidadaView |
| `apps/estoque/migrations/0001_initial.py` | Tabelas UnidadeMedida e ItemEstoque | VERIFICADO | UniqueConstraint unique_item_por_unidade criada via AddConstraint |
| `apps/estoque/migrations/0002_seed_unidades.py` | Seed das 8 unidades de medida | VERIFICADO | UN, KG, CX, L, M, PAR, PCT, RES via get_or_create; RunPython com reverse |
| `templates/estoque/lista.html` | Listagem com highlight abaixo do mínimo | VERIFICADO | CSS .abaixo-minimo com rgba(233,69,96,0.15); include de item_row.html |
| `templates/estoque/visao_consolidada.html` | Visão consolidada Comprador/Admin | VERIFICADO | Titulo correto; todas unidades; abaixo_do_minimo destacado com badge-danger |
| `templates/base.html` | Links de navegação para ambos os apps | VERIFICADO | Link Fornecedores condicional (comprador/admin/superuser) linha 63; link Estoque para todos linha 71 |

---

## Verificação de Links-Chave (Wiring)

| De | Para | Via | Status | Detalhes |
|----|------|-----|--------|----------|
| `apps/fornecedores/forms.py` | `stdnum.br.cnpj.validate` | `from stdnum.br import cnpj as cnpj_lib` | CONECTADO | Linha 12; `cnpj_lib.validate(valor)` na linha 55 |
| `apps/fornecedores/views.py` | `TrigramSimilarity` | `django.contrib.postgres.search` | CONECTADO | Linha 14; usado em `views.py:70` |
| `templates/fornecedores/partials/fornecedor_list.html` | `fornecedor_tags` | `{% load fornecedor_tags %}` | CONECTADO | Linha 1; filtro cnpj_format em `fornecedor_row.html:4` |
| `apps/fornecedores/views.py` | `get_queryset_fornecedores` | `apenas_ativos=not mostrar_inativos` | CONECTADO | Linha 94-98; GET param "mostrar_inativos" controla o parâmetro |
| `templates/fornecedores/lista.html` | `mostrar_inativos` checkbox | `hx-include` em busca e select de categoria | CONECTADO | Linhas 33, 49, 67-75; estado do checkbox propagado em todos os requests HTMX |
| `apps/estoque/views.py` | `select_for_update()` | `transaction.atomic()` | CONECTADO | `views.py:127-131`; bloco with atomic envolve o select_for_update |
| `apps/estoque/views.py` | `request.user.default_unit` | filtro unidade_organizacional | CONECTADO | `views.py:72,94,133` — nunca vem do formulário |
| `templates/estoque/lista.html` | `item.abaixo_do_minimo` | include item_row.html | CONECTADO | `item_row.html:4` classe condicional; `item_row.html:10` badge visual |
| `templates/base.html` | `fornecedores:lista` | `{% url 'fornecedores:lista' %}` | CONECTADO | `base.html:64` |
| `templates/base.html` | `estoque:lista` | `{% url 'estoque:lista' %}` | CONECTADO | `base.html:71` |

---

## Rastreamento de Fluxo de Dados (Nível 4)

| Artefato | Variável de Dados | Fonte | Produz Dados Reais | Status |
|----------|-------------------|-------|--------------------|--------|
| `templates/fornecedores/lista.html` | `fornecedores` | `get_queryset_fornecedores(apenas_ativos=not mostrar_inativos)` → `Fornecedor.objects.select_related()` com filtro condicional | Sim | FLUINDO |
| `templates/estoque/lista.html` | `itens` | `ListaEstoqueView.get_queryset()` → `ItemEstoque.objects.filter(unidade_organizacional=...)` | Sim | FLUINDO |
| `templates/estoque/visao_consolidada.html` | `itens` | `VisaoConsolidadaView.get_queryset()` → `ItemEstoque.objects.select_related()` sem filtro | Sim | FLUINDO |
| `templates/estoque/partials/item_row.html` | `item` | `AtualizarQuantidadeView` → `ItemEstoque.objects.select_for_update().get()` | Sim | FLUINDO |

---

## Verificação de Cobertura de Requisitos

| Requisito | Plano | Descrição | Status | Evidência |
|-----------|-------|-----------|--------|-----------|
| FORN-01 | 03-01 | Comprador cadastra fornecedores com CNPJ validado, razão social, e-mail e telefone | SATISFEITO | `models.py` campos cnpj, razao_social, email, telefone; CadastrarFornecedorView funcional |
| FORN-02 | 03-01 | Sistema valida CNPJ usando python-stdnum (suporta formato alfanumérico Jul/2026) | SATISFEITO | `forms.py:12-55` `stdnum.br.cnpj.validate()`; `requirements.txt` python-stdnum==2.2 |
| FORN-03 | 03-01 | Comprador organiza fornecedores por categorias configuráveis | SATISFEITO | `models.py:29-33` FK CategoriaCompra com PROTECT; form filtra categorias ativas |
| FORN-04 | 03-01 | Comprador ativa ou inativa fornecedores sem perder histórico | SATISFEITO | ToggleAtivoView correto; registro preservado (`ativo=False`); `get_queryset_fornecedores(apenas_ativos=True/False)` controla visibilidade; checkbox "Mostrar inativos" na UI permite reativação via web |
| FORN-05 | 03-01 | Comprador busca e filtra fornecedores por nome, CNPJ ou categoria | SATISFEITO | TrigramSimilarity em razao_social; busca exata por CNPJ; filtro categoria via GET |
| EST-01 | 03-02 | Solicitante cadastra itens de estoque da sua unidade com: nome, unidade de medida e quantidade atual | SATISFEITO | CadastrarItemEstoqueView atribui `item.unidade_organizacional = request.user.default_unit` |
| EST-02 | 03-02 | Solicitante define quantidade mínima (ponto de pedido) por item | SATISFEITO | `models.py:44` quantidade_minima=IntegerField; `forms.py:28` incluso nos fields |
| EST-03 | 03-02 | Solicitante atualiza quantidades de estoque manualmente | SATISFEITO | AtualizarQuantidadeView com HTMX POST; `item_row.html:19-40` form inline por linha |
| EST-04 | 03-02 | Sistema destaca itens abaixo da quantidade mínima configurada | SATISFEITO | `models.py:68-71` property abaixo_do_minimo; `item_row.html:4` classe CSS condicional; badge vermelho |
| EST-05 | 03-02 | Cada unidade vê somente o próprio estoque | SATISFEITO | `views.py:91-95` IDOR guard com filtro unidade_organizacional; ListaEstoqueView isola por unidade |
| EST-06 | 03-02 | Comprador e Admin têm visão consolidada do estoque de todas as unidades | SATISFEITO | VisaoConsolidadaView com PermissionDenied para roles não autorizados; queryset sem filtro de unidade |

**Cobertura:** 11/11 requisitos satisfeitos

---

## Anti-Padrões Encontrados

| Arquivo | Linha | Padrão | Severidade | Impacto |
|---------|-------|--------|------------|---------|
| — | — | — | — | Nenhum anti-padrão encontrado |

Nenhum marcador TBD/FIXME/XXX encontrado nos arquivos modificados.
Nenhum stub de implementação (return null, return [], placeholder) encontrado.
O fix de FORN-04 não introduziu nenhum padrão problemático.

---

## Verificações Comportamentais (Spot-Checks)

| Comportamento | Verificação | Resultado | Status |
|---------------|-------------|-----------|--------|
| Importação stdnum disponível | `requirements.txt` python-stdnum==2.2 presente | Encontrado | PASS |
| CompradorRequiredMixin bloqueia solicitante | `views.py:37-41` PermissionDenied se role not in ("comprador","admin") e not is_superuser | Implementado | PASS |
| select_for_update dentro de atomic | `estoque/views.py:127` `with transaction.atomic()` envolve `select_for_update().get()` | Implementado | PASS |
| apenas_ativos=False expõe inativos | `views.py:57-58` `if apenas_ativos: qs = qs.filter(ativo=True)` — quando False, filtro não aplicado | Implementado | PASS |
| mostrar_inativos propagado em HTMX | `lista.html:33,49` `hx-include` em busca e select incluem `[name='mostrar_inativos']` | Conectado | PASS |
| Botão Reativar condicional no row | `fornecedor_row.html:32` `{% if fornecedor.ativo %}Inativar{% else %}Reativar{% endif %}` | Implementado | PASS |
| Fornecedores inativos visíveis com toggle | `views.py:94` `mostrar_inativos = request.GET.get("mostrar_inativos", "") == "1"` controla queryset | Implementado | PASS |

---

## Verificação Humana Necessária

### 1. HTMX Live Search em Navegador Real

**Teste:** Acessar /fornecedores/ como comprador, digitar um nome parcial no campo de busca
**Esperado:** Lista atualiza dinamicamente sem reload após 300ms de inatividade
**Por que humano:** django-htmx + HtmxMiddleware necessários; comportamento do request.htmx não verificável por grep

### 2. Fluxo Completo de Inativação e Reativação (FORN-04)

**Teste:** (a) Clicar em "Inativar" em um fornecedor e confirmar o diálogo. (b) Marcar o checkbox "Mostrar fornecedores inativos". (c) Localizar o fornecedor inativado na lista. (d) Clicar em "Reativar".
**Esperado:** (a) Linha atualiza via outerHTML swap, status muda para "Inativo". (b) Lista recarrega via HTMX e inclui inativos com status visível. (c) Fornecedor aparece com botão "Reativar". (d) Status volta a "Ativo" após swap.
**Por que humano:** Comportamento de swap HTMX, confirmação JS, e propagação do estado do checkbox entre requests requerem navegador

### 3. Atualização de Quantidade Inline com Highlight

**Teste:** Na listagem de estoque, alterar o valor no campo de quantidade de um item e clicar em Salvar
**Esperado:** A linha atualiza via HTMX outerHTML swap; se item ficar abaixo do mínimo, linha fica com fundo vermelho; se sair do estado crítico, destaque desaparece
**Por que humano:** Comportamento de swap HTMX e estilo condicional requerem navegador

---

## Resumo dos Gaps

Nenhum gap bloqueante. A re-verificação confirma que o gap FORN-04 da verificação anterior foi corretamente fechado com uma implementação completa de três camadas:

1. Lógica de filtragem condicional em `get_queryset_fornecedores(apenas_ativos=True)` — quando `False`, o filtro `ativo=True` não é aplicado.
2. View `ListaFornecedoresView` lê o parâmetro GET `mostrar_inativos=1` e o converte para `apenas_ativos=False`.
3. Template `lista.html` expõe um checkbox "Mostrar fornecedores inativos" que propaga o estado via `hx-include` em todos os filtros HTMX da página.

Todos os 11 requisitos (FORN-01..05, EST-01..06) estão satisfeitos com evidências diretas no código.

---

_Verificado em: 2026-06-11_
_Verificador: Claude (gsd-verifier)_
