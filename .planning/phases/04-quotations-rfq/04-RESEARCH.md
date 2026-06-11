# Phase 4: Quotations (RFQ) - Research

**Researched:** 2026-06-11
**Domain:** Django + HTMX — RFQ cycle (create, quote entry, price comparison, winner selection)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** `condicoes_pagamento` = `CharField(max_length=200, blank=True)` — texto livre
- **D-02:** `prazo_entrega` = `CharField(max_length=100, blank=True)` — texto livre
- **D-03:** Campos da cotação: `fornecedor FK`, `preco_unitario (DecimalField)`, `prazo_entrega`, `condicoes_pagamento`, `observacoes (TextField, blank=True)` — sem campo de quantidade cotada
- **D-04:** Tela principal `/cotacoes/` com listagem de RFQs e botão "Nova Cotação"; `<select>` filtrado por `status=APROVADO` sem RFQ vinculado; nav lateral "Cotações" visível para Comprador e Admin
- **D-05:** Acesso restrito via `CompradorRequiredMixin` de `apps/fornecedores/views.py` — importar, não recriar
- **D-06:** `RFQ` tem `OneToOneField` para `Requisicao` — `IntegrityError` capturado na view ao tentar segundo RFQ
- **D-07:** Vencedor: `RFQ.vencedor = FK(CotacaoFornecedor, null=True)` + `RFQ.justificativa_selecao = TextField(blank=True)`; após definido, qualquer edição é bloqueada na view via `rfq.tem_vencedor`
- **D-08 (Claude's discretion):** Cotações individuais livres para adicionar/editar/remover antes da seleção; RFQ somente leitura após seleção
- **D-09 (Claude's discretion):** Tabela comparativa na mesma página do RFQ; colunas: Fornecedor, Preço Unitário, Prazo, Condições, Delta %; menor preço com badge `#e94560`; delta calculado no template; botão "Selecionar Vencedor" inativo se já houver vencedor
- **D-10 (Claude's discretion):** Tabela comparativa é estática; atualiza via reload/hx-boost após add/remove cotação

### Claude's Discretion

- D-08: Cotações editáveis/removíveis antes da seleção
- D-09: Layout da tabela comparativa, forma de destacar o menor preço, cálculo de delta no template
- D-10: Tabela estática (não atualização em tempo real)

### Deferred Ideas (OUT OF SCOPE)

- Notificação ao Solicitante quando RFQ é encerrado (v2)
- Relatório de saving (menor preço vs. selecionado) — Fase 5 ou v2
- Múltiplos itens por RFQ — v2
- Status explícito de RFQ (enum com CANCELADO etc.) — v2
- Importação de planilha de cotações — v2
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| COT-01 | Comprador cria RFQ vinculado a uma requisição aprovada (um RFQ por requisição) | OneToOneField + IntegrityError guard; select filtrado em `get_queryset` |
| COT-02 | Comprador registra cotações de múltiplos fornecedores (preço, prazo, condições) sem reload total | HTMX Pattern: POST via `hx-post` + `hx-swap="beforeend"` ou `hx-target` para atualizar `<tbody>` de cotações |
| COT-03 | Sistema exibe comparativo com destaque automático do menor preço e delta % | Calcular `menor_preco` na view, passar ao template; `{{ ((preco - menor_preco) / menor_preco * 100)|floatformat:1 }}%` no template |
| COT-04 | Comprador seleciona fornecedor vencedor com justificativa obrigatória (imutável após salvo) | `select_for_update` + `transaction.atomic` no service; `rfq.tem_vencedor` guard na view; modal HTMX com form de justificativa |
</phase_requirements>

---

## Summary

A Fase 4 adiciona o app `apps/cotacoes/` ao projeto ComprasNexos, implementando o ciclo completo de RFQ — da criação à seleção do fornecedor vencedor. O padrão arquitetural está completamente estabelecido pelas fases anteriores: service layer obrigatório (`services.py`), `CompradorRequiredMixin` importado de `apps/fornecedores/views.py`, `TimestampedModel` herdado de `apps/core/models.py`, e modais HTMX com `#modal-container` e `retarget/reswap` já em uso em `apps/aprovacoes/views.py`.

O único comportamento novo desta fase em relação às anteriores é a dinâmica de adicionar/remover linhas de cotação sem reload de página (COT-02) e o cálculo de delta percentual no comparativo (COT-03). Ambos são implementáveis com os padrões HTMX já estabelecidos: POST retornando partial + swap. A imutabilidade do vencedor (COT-04) segue exatamente o mesmo padrão de `select_for_update` já em `apps/aprovacoes/services.py`.

O `base.html` já tem o link "Cotações" no sidebar com o guard de role correto (`comprador` ou `admin`), apontando para `#` — a única alteração necessária é trocar o `href="#"` pelo `{% url 'cotacoes:lista' %}`.

**Recomendação principal:** Estruturar a fase em 2 planos — Plan 1 (modelos, service layer, views de RFQ e cotação) e Plan 2 (nav fix, testes completos e validação da suite).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Criar RFQ (COT-01) | API / Backend (Django view + service) | — | Validação de unicidade OneToOneField + IntegrityError é responsabilidade do servidor |
| Filtrar requisições aprovadas sem RFQ | API / Backend | — | Query ORM com annotate/exclude; não expõe dados além do necessário |
| Adicionar/remover cotações (COT-02) | API / Backend | Browser (HTMX swap) | POST HTTP no servidor; resposta partial injeta/remove linha via HTMX |
| Tabela comparativa + delta % (COT-03) | Frontend Server (template Django) | — | `menor_preco` calculado na view; delta renderizado no template com `widthratio` ou filter |
| Seleção do vencedor (COT-04) | API / Backend (service) | Browser (modal HTMX) | `select_for_update + transaction.atomic` obrigatório; modal abre via GET HTMX |
| Controle de acesso comprador/admin | API / Backend (mixin) | — | `CompradorRequiredMixin` no dispatch de cada view |
| Nav "Cotações" | Frontend Server (template base.html) | — | Guard de role já existe em base.html; apenas ativar `href` |

---

## Standard Stack

### Core (sem novas dependências — reutiliza stack existente)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django 5.2 LTS | 5.2.x | ORM, views, migrations | Já instalado — mandato do cliente [CITED: CLAUDE.md] |
| django-htmx | 1.x | `request.htmx`, `retarget`, `reswap` | Já instalado; usado em aprovacoes/views.py [VERIFIED: codebase] |
| psycopg2-binary | 2.9.x | PostgreSQL adapter | Já instalado [VERIFIED: codebase] |

**Nenhum novo pacote necessário para esta fase.** Toda a funcionalidade é implementada com as bibliotecas já presentes no projeto.

### Padrões de Template Django para delta %

O template Django não tem operador de divisão nativo. Duas abordagens:

**Opção A — `widthratio` tag (built-in):**
```django
{# delta = ((preco - menor_preco) / menor_preco) * 100 #}
{% widthratio cotacao.preco_unitario menor_preco 100 as delta_bruto %}
{# Limitação: widthratio arredonda para inteiro e calcula (value/max)*scale #}
{# Para delta = (preco/menor_preco - 1)*100: requer cálculo auxiliar na view #}
```

**Opção B — Calcular na view (RECOMENDADO):** [ASSUMED]
```python
# Em services.py ou na view get_context_data
from decimal import Decimal

def calcular_comparativo(rfq):
    cotacoes = rfq.cotacoes.select_related("fornecedor").order_by("preco_unitario")
    if not cotacoes:
        return []
    menor = cotacoes[0].preco_unitario
    result = []
    for c in cotacoes:
        if menor and menor > 0:
            delta = ((c.preco_unitario - menor) / menor * Decimal("100")).quantize(Decimal("0.01"))
        else:
            delta = Decimal("0")
        result.append({"cotacao": c, "delta": delta, "is_menor": c.preco_unitario == menor})
    return result
```

**Motivo:** Manter a lógica de negócio fora do template Django. Calcular na view é testável, mais limpo e evita limitações do `widthratio` com decimais. [ASSUMED]

## Package Legitimacy Audit

> Nenhum novo pacote externo é instalado nesta fase. Todas as dependências já estão no `requirements.txt` do projeto.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
Comprador (Browser)
        │
        │  GET /cotacoes/                     → Lista RFQs (hub)
        │  POST /cotacoes/nova/               → Cria RFQ (verifica unicidade)
        │  GET /cotacoes/<pk>/                → Detalhe RFQ + tabela comparativa
        │  POST /cotacoes/<rfq_pk>/cotacoes/adicionar/  → Adiciona linha cotação (HTMX)
        │  POST /cotacoes/<rfq_pk>/cotacoes/<cot_pk>/remover/  → Remove linha (HTMX)
        │  GET /cotacoes/<rfq_pk>/selecionar-vencedor/<cot_pk>/  → Modal justificativa (HTMX)
        │  POST /cotacoes/<rfq_pk>/selecionar-vencedor/<cot_pk>/  → Confirma vencedor
        ▼
  CompradorRequiredMixin (dispatch)
        │
        ▼
  apps/cotacoes/views.py  (views finas — delegam ao service)
        │                │
        │                └──▶  apps/cotacoes/services.py
        │                           │  criar_rfq()          → OneToOneField guard
        │                           │  adicionar_cotacao()  → valida duplicidade fornecedor
        │                           │  remover_cotacao()    → bloqueia se vencedor definido
        │                           │  selecionar_vencedor() → select_for_update + atomic
        │
        ▼
  ORM / PostgreSQL
  ┌─────────────────┐     ┌──────────────────────────┐
  │  RFQ            │1───1│  Requisicao (app req.)    │
  │  - requisicao   │     └──────────────────────────┘
  │  - vencedor FK  │◀─┐
  │  - justificativa│  │
  └────────┬────────┘  │
           │1          │
           │*          │
  ┌────────▼──────────┐│
  │  CotacaoFornecedor││
  │  - rfq FK         ││
  │  - fornecedor FK  ││  ┌─────────────────────┐
  │  - preco_unitario │└──┤  RFQ.vencedor FK     │
  │  - prazo_entrega  │   └─────────────────────┘
  │  - cond_pagamento │
  │  - observacoes    │   ┌─────────────────────┐
  └───────────────────┘   │  Fornecedor (app f.) │
           │FK────────────▶  razao_social, ativo │
                           └─────────────────────┘
```

### Recommended Project Structure

```
apps/cotacoes/
├── __init__.py
├── apps.py
├── admin.py
├── forms.py          # RFQForm, CotacaoFornecedorForm
├── models.py         # RFQ, CotacaoFornecedor
├── services.py       # criar_rfq, adicionar_cotacao, remover_cotacao, selecionar_vencedor
├── urls.py
├── views.py
├── migrations/
│   └── 0001_initial.py
├── templates/
│   └── cotacoes/
│       ├── rfq_list.html       # hub /cotacoes/
│       ├── rfq_form.html       # nova cotação
│       ├── rfq_detail.html     # detalhe + tabela comparativa
│       └── partials/
│           ├── cotacao_row.html         # linha da tabela (HTMX swap)
│           ├── cotacao_form_inline.html # form inline de adição de cotação
│           └── modal_selecionar.html    # modal de confirmação do vencedor
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_models.py
    ├── test_services.py
    └── test_views.py
```

### Pattern 1: Adição de linha de cotação sem reload (COT-02)

O padrão estabelecido no projeto para operações HTMX de POST que retornam partial é o mesmo utilizado em `ToggleAtivoView` (fornecedores) e nas views de aprovação.

**Abordagem: form inline + swap `beforeend` no `<tbody>`**

```html
<!-- rfq_detail.html — form inline de adição -->
<form id="form-add-cotacao"
      hx-post="{% url 'cotacoes:adicionar-cotacao' rfq.pk %}"
      hx-target="#cotacoes-tbody"
      hx-swap="beforeend"
      hx-on::after-request="if(event.detail.successful) this.reset()">
  {% csrf_token %}
  <!-- campos: fornecedor select, preco_unitario, prazo_entrega, condicoes_pagamento, observacoes -->
</form>

<table>
  <tbody id="cotacoes-tbody">
    {% for item in comparativo %}
      {% include "cotacoes/partials/cotacao_row.html" %}
    {% endfor %}
  </tbody>
</table>
```

```python
# views.py — AdicionarCotacaoView
class AdicionarCotacaoView(CompradorRequiredMixin, View):
    def post(self, request, rfq_pk):
        rfq = get_object_or_404(RFQ, pk=rfq_pk)
        if rfq.tem_vencedor:
            return HttpResponse("RFQ encerrado.", status=403)
        form = CotacaoFornecedorForm(request.POST)
        if form.is_valid():
            cotacao = services.adicionar_cotacao(rfq, form.cleaned_data)
            # Recalcular comparativo para atualizar deltas
            # Opção simples: retornar toda a tabela atualizada
            comparativo = services.calcular_comparativo(rfq)
            return render(request, "cotacoes/partials/cotacao_row.html", {
                "item": comparativo[-1],  # última linha adicionada
                "rfq": rfq,
            })
        return render(request, "cotacoes/partials/cotacao_form_inline.html",
                      {"form": form, "rfq": rfq}, status=422)
```

**Nota sobre delta ao adicionar:** Ao adicionar uma nova cotação, os deltas de TODAS as linhas existentes precisam ser recalculados (o menor preço pode mudar). A solução mais simples é, após POST bem-sucedido, usar `HX-Trigger` para recarregar a tabela inteira — ou redirecionar via `HX-Redirect` para a página de detalhe. [ASSUMED — decisão de design a confirmar no plano]

**Abordagem alternativa (mais simples):** Após adicionar/remover cotação, retornar `HX-Redirect` para `/cotacoes/<pk>/` (reload da página de detalhe). A tabela comparativa sendo estática (D-10) justifica esse reload. Isso elimina a complexidade de manter deltas sincronizados via DOM. [ASSUMED — recomendada como mais simples e consistente com D-10]

### Pattern 2: Remoção de linha de cotação (COT-02)

```html
<!-- cotacao_row.html -->
<tr id="cotacao-row-{{ item.cotacao.pk }}">
  <td>{{ item.cotacao.fornecedor.razao_social }}</td>
  <td>R$ {{ item.cotacao.preco_unitario }}</td>
  ...
  {% if not rfq.tem_vencedor %}
  <td>
    <button
      hx-post="{% url 'cotacoes:remover-cotacao' rfq.pk item.cotacao.pk %}"
      hx-target="#cotacao-row-{{ item.cotacao.pk }}"
      hx-swap="outerHTML"
      hx-confirm="Remover esta cotação?">
      Remover
    </button>
  </td>
  {% endif %}
</tr>
```

```python
# views.py — RemoverCotacaoView
class RemoverCotacaoView(CompradorRequiredMixin, View):
    def post(self, request, rfq_pk, cotacao_pk):
        rfq = get_object_or_404(RFQ, pk=rfq_pk)
        if rfq.tem_vencedor:
            return HttpResponse("RFQ encerrado.", status=403)
        cotacao = get_object_or_404(CotacaoFornecedor, pk=cotacao_pk, rfq=rfq)
        cotacao.delete()
        return HttpResponse("")  # outerHTML swap vazio remove a linha
```

### Pattern 3: Modal de seleção de vencedor (COT-04)

Segue exatamente o mesmo padrão do `ModalReprovarView` de `apps/aprovacoes/views.py`:

```python
# views.py — ModalSelecionarVencedorView
class ModalSelecionarVencedorView(CompradorRequiredMixin, View):
    def get(self, request, rfq_pk, cotacao_pk):
        rfq = get_object_or_404(RFQ, pk=rfq_pk)
        if rfq.tem_vencedor:
            return HttpResponse("Vencedor já definido.", status=409)
        cotacao = get_object_or_404(CotacaoFornecedor, pk=cotacao_pk, rfq=rfq)
        return render(request, "cotacoes/partials/modal_selecionar.html", {
            "rfq": rfq,
            "cotacao": cotacao,
        })
```

```html
<!-- No rfq_detail.html, container do modal (mesmo padrão de fila_gestor.html) -->
<div id="modal-container"></div>

<!-- Botão em cada linha da tabela comparativa -->
{% if not rfq.tem_vencedor %}
<button
  hx-get="{% url 'cotacoes:modal-selecionar' rfq.pk item.cotacao.pk %}"
  hx-target="#modal-container"
  hx-swap="innerHTML">
  Selecionar Vencedor
</button>
{% endif %}
```

```html
<!-- modal_selecionar.html — mesmo padrão de modal_reprovar.html -->
<div class="card" style="margin-bottom:16px;border-color:var(--color-accent);">
  <p><strong>Selecionar vencedor:</strong> {{ cotacao.fornecedor.razao_social }}</p>
  <form
    hx-post="{% url 'cotacoes:selecionar-vencedor' rfq.pk cotacao.pk %}"
    hx-target="body"
    hx-push-url="true"
    hx-on::after-request="if(event.detail.successful) document.getElementById('modal-container').innerHTML=''">
    {% csrf_token %}
    <div class="form-group">
      <label class="form-label">Justificativa *</label>
      <textarea name="justificativa" rows="3" required class="form-input"></textarea>
    </div>
    <div style="display:flex;gap:8px;">
      <button type="submit" class="btn btn-primary">Confirmar Seleção</button>
      <button type="button" onclick="document.getElementById('modal-container').innerHTML=''"
              class="btn btn-secondary">Cancelar</button>
    </div>
  </form>
</div>
```

### Pattern 4: Service layer — selecionar_vencedor (COT-04)

Segue exatamente o padrão de `aprovar_gestor` em `apps/aprovacoes/services.py`:

```python
# apps/cotacoes/services.py
from django.db import transaction
from .models import RFQ, CotacaoFornecedor

def selecionar_vencedor(rfq_pk: int, cotacao_pk: int, justificativa: str, comprador) -> RFQ:
    """
    Define o vencedor do RFQ. Imutável após salvo. (COT-04, D-07)

    Levanta:
        ValueError  — se justificativa vazia
        ValueError  — se RFQ já tem vencedor
        ValueError  — se cotacao não pertence ao RFQ
    """
    if not justificativa or not justificativa.strip():
        raise ValueError("Justificativa é obrigatória para selecionar o vencedor.")

    with transaction.atomic():
        rfq = RFQ.objects.select_for_update().get(pk=rfq_pk)

        if rfq.tem_vencedor:
            raise ValueError("Vencedor já foi definido para este RFQ.")

        cotacao = CotacaoFornecedor.objects.get(pk=cotacao_pk, rfq=rfq)
        rfq.vencedor = cotacao
        rfq.justificativa_selecao = justificativa.strip()
        rfq.save(update_fields=["vencedor", "justificativa_selecao", "atualizado_em"])

    return rfq
```

### Anti-Patterns to Avoid

- **Lógica de negócio na view:** Nunca checar `rfq.tem_vencedor` apenas na view sem também validar no service. Defense in depth (padrão `reprovar_requisicao` já faz isso).
- **FloatField para preço:** `preco_unitario = FloatField(...)` causa erro de arredondamento. Sempre `DecimalField(max_digits=12, decimal_places=2)`.
- **Delta calculado só no template com `widthratio`:** `widthratio` arredonda para inteiro. Calcular na view com `Decimal` preserva precisão.
- **GET para operações de escrita (remover cotação, selecionar vencedor):** Usar sempre POST para mutações. GET apenas para carregar modais.
- **Adicionar nova cotação com mesmo fornecedor duas vezes:** Considerar `unique_together = [("rfq", "fornecedor")]` no model ou validação no form/service — decisão de design para o plano.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Race condition em seleção de vencedor | Guard manual com `if rfq.vencedor:` | `select_for_update() + transaction.atomic()` | Dois Compradores simultâneos passariam pelo guard sem o lock |
| CSRF em formulários HTMX | Header manual via JavaScript | Padrão já em `base.html` (evento `htmx:configRequest`) | Já está configurado globalmente — não duplicar |
| Bloqueio de edição pós-seleção | Campo de status separado | Propriedade `tem_vencedor = rfq.vencedor is not None` | Mais simples, derivado do dado já existente (D-07) |
| Controle de acesso | Mixin próprio | `CompradorRequiredMixin` de `apps/fornecedores/views.py` | Importar, não recriar (D-05) |
| retarget/reswap de modal com erros | JavaScript manual | `from django_htmx.http import retarget, reswap` | Já em uso em `apps/aprovacoes/views.py`; evita HTML inválido na tabela |

**Key insight:** Esta fase é quase inteiramente composição de padrões já estabelecidos. O único elemento genuinamente novo é o cálculo de comparativo com delta percentual, que deve ser encapsulado em `services.calcular_comparativo()` e testado unitariamente.

---

## Common Pitfalls

### Pitfall 1: Delta % quebrado quando `menor_preco == 0`

**What goes wrong:** Divisão por zero se um fornecedor cotar `preco_unitario=0`.
**Why it happens:** Dados inválidos passam pelo form se não houver validação de `preco_unitario > 0`.
**How to avoid:** Adicionar `MinValueValidator(Decimal("0.01"))` ao `preco_unitario` no model/form + guard `if menor > 0` no service de comparativo.
**Warning signs:** `ZeroDivisionError` no template ou no service.

### Pitfall 2: Tabela comparativa com deltas desatualizados após operação HTMX

**What goes wrong:** Após adicionar uma cotação mais barata via HTMX (sem reload), as linhas anteriores ainda mostram o delta relativo ao preço mínimo antigo.
**Why it happens:** Ao usar `hx-swap="beforeend"` apenas na nova linha, as linhas antigas não são re-renderizadas.
**How to avoid:** Usar `HX-Redirect` (redirect via header) após adição bem-sucedida para recarregar a página de detalhe completa. Isso é consistente com D-10 ("tabela estática, reload após add/remove").
**Warning signs:** Delta % nas linhas antigas permanece incorreto após novo fornecedor mais barato ser adicionado.

### Pitfall 3: `IntegrityError` não tratado ao criar segundo RFQ para a mesma requisição

**What goes wrong:** Django lança `IntegrityError` (constraint `OneToOneField`) que resulta em 500.
**Why it happens:** Dois Compradores simultâneos tentam criar RFQ para a mesma requisição.
**How to avoid:** Capturar `IntegrityError` na view e retornar mensagem de erro adequada:
```python
from django.db import IntegrityError
try:
    rfq = services.criar_rfq(requisicao_pk, request.user)
except IntegrityError:
    # Mensagem amigável: "Já existe uma cotação para esta requisição."
    form.add_error("requisicao", "Já existe uma cotação para esta requisição.")
    return render(request, "cotacoes/rfq_form.html", {"form": form}, status=409)
```
**Warning signs:** HTTP 500 ao submeter o form de nova cotação com requisição já cotada.

### Pitfall 4: `<select>` de requisições inclui requisições já vinculadas a um RFQ

**What goes wrong:** Comprador seleciona requisição que já tem RFQ — resulta em `IntegrityError` ou UX confusa.
**Why it happens:** Queryset do form não exclui requisições com RFQ existente.
**How to avoid:**
```python
# forms.py
class RFQForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["requisicao"].queryset = Requisicao.objects.filter(
            status=Requisicao.Status.APROVADO
        ).filter(rfq__isnull=True)  # exclude já cotadas
```
**Warning signs:** Lista de requisições inclui itens já cotados.

### Pitfall 5: Vencedor apontando para cotação de fornecedor inativo

**What goes wrong:** Fornecedor é inativado após seleção do vencedor; `on_delete=PROTECT` bloqueia a inativação ou `SET_NULL` anula o vencedor.
**Why it happens:** `CotacaoFornecedor.fornecedor` usa `on_delete=PROTECT` (conforme CONTEXT.md).
**How to avoid:** `on_delete=PROTECT` é correto — impede exclusão de fornecedor com cotações ativas. O toggle `ativo=False` não afeta a FK. Não há problema com `ativo=False` após seleção; apenas garantir que a view de detalhes exiba o fornecedor mesmo inativo.

### Pitfall 6: `unique_together` em CotacaoFornecedor e formulário inline

**What goes wrong:** Se adicionar `unique_together = [("rfq", "fornecedor")]`, o form de adição levanta `IntegrityError` ao duplicar fornecedor.
**Why it happens:** Formulário não valida duplicidade antes do save.
**How to avoid:** Adicionar `validate_unique()` no form ou `unique_together` no model + capturar `IntegrityError` no service. Decidir no plano se duplicidade de fornecedor é proibida ou permitida (duas cotações do mesmo fornecedor em rounds diferentes).

---

## Code Examples

### Model RFQ e CotacaoFornecedor

```python
# apps/cotacoes/models.py
# Source: codebase patterns (TimestampedModel, AuditedModel) [VERIFIED: codebase]
from django.db import models
from apps.core.models import TimestampedModel


class RFQ(TimestampedModel):
    """
    Processo de cotação vinculado a uma Requisicao aprovada.
    OneToOneField garante unicidade no DB (D-06).
    """
    requisicao = models.OneToOneField(
        "requisicoes.Requisicao",
        on_delete=models.PROTECT,
        related_name="rfq",
    )
    criado_por = models.ForeignKey(
        "accounts.User",
        null=True,
        on_delete=models.SET_NULL,
        related_name="rfqs_criados",
    )
    vencedor = models.ForeignKey(
        "CotacaoFornecedor",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="rfqs_vencidos",
    )
    justificativa_selecao = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "RFQ"
        verbose_name_plural = "RFQs"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"RFQ #{self.pk} — {self.requisicao.descricao[:40]}"

    @property
    def tem_vencedor(self) -> bool:
        """Propriedade derivada — RFQ está encerrado quando vencedor definido (D-07)."""
        return self.vencedor_id is not None

    @property
    def status_display(self) -> str:
        return "Encerrado" if self.tem_vencedor else "Em andamento"


class CotacaoFornecedor(TimestampedModel):
    """
    Cotação de um fornecedor específico para um RFQ.
    preco_unitario: DecimalField — nunca FloatField (constraint arquitetural).
    """
    rfq = models.ForeignKey(
        RFQ,
        on_delete=models.CASCADE,
        related_name="cotacoes",
    )
    fornecedor = models.ForeignKey(
        "fornecedores.Fornecedor",
        on_delete=models.PROTECT,
        related_name="cotacoes",
    )
    preco_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    prazo_entrega = models.CharField(max_length=100, blank=True, default="")
    condicoes_pagamento = models.CharField(max_length=200, blank=True, default="")
    observacoes = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Cotação de Fornecedor"
        verbose_name_plural = "Cotações de Fornecedores"
        ordering = ["preco_unitario"]
```

### Calcular comparativo com delta %

```python
# apps/cotacoes/services.py
# Source: codebase pattern (services.py de aprovacoes) [VERIFIED: codebase]
from decimal import Decimal
from typing import List, Dict, Any

def calcular_comparativo(rfq) -> List[Dict[str, Any]]:
    """
    Retorna lista de dicts com cotacao, delta_percentual e is_menor.
    Ordenada por preco_unitario ASC.
    """
    cotacoes = list(rfq.cotacoes.select_related("fornecedor").order_by("preco_unitario"))
    if not cotacoes:
        return []
    menor = cotacoes[0].preco_unitario
    result = []
    for c in cotacoes:
        if menor and menor > 0:
            delta = ((c.preco_unitario - menor) / menor * Decimal("100")).quantize(Decimal("0.1"))
        else:
            delta = Decimal("0")
        result.append({
            "cotacao": c,
            "delta": delta,
            "is_menor": c.preco_unitario == menor,
        })
    return result
```

### select de requisição no form — display customizado

```python
# forms.py
from django import forms
from apps.requisicoes.models import Requisicao
from .models import RFQ, CotacaoFornecedor
from apps.fornecedores.models import Fornecedor


class RFQForm(forms.ModelForm):
    class Meta:
        model = RFQ
        fields = ["requisicao"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Requisicao.objects.filter(
            status=Requisicao.Status.APROVADO,
            rfq__isnull=True,
        ).select_related("categoria")
        self.fields["requisicao"].queryset = qs
        # Label customizado: "#<pk> — <descricao[:40]> (R$ <valor_estimado>)"
        self.fields["requisicao"].label_from_instance = lambda obj: (
            f"#{obj.pk} — {obj.descricao[:40]} (R$ {obj.valor_estimado:,.2f})"
        )
        self.fields["requisicao"].widget.attrs.update({"class": "form-select"})
```

### Nav fix em base.html

```html
<!-- Trocar href="#" pelo url real (já existe o guard de role correto) -->
{% if request.user.role == 'comprador' or request.user.role == 'admin' %}
<a href="{% url 'cotacoes:lista' %}"
   class="nav-item {% if 'cotacoes' in request.path %}is-active{% endif %}">
  Cotações
</a>
{% endif %}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Forms tradicionais com reload completo | HTMX partial swap para add/remove linhas | Estabelecido na Fase 2 (aprovações) | COT-02 implementado com padrão já testado |
| JavaScript customizado para modais | Modal via HTMX GET + innerHTML swap em `#modal-container` | Estabelecido na Fase 2 | COT-04 segue exatamente o mesmo padrão |
| FloatField para valores monetários | DecimalField(max_digits=12, decimal_places=2) | Fase 1 (constraint arquitetural) | Evita erros de arredondamento em comparativo de preços |

**Sem deprecações relevantes** para esta fase — a stack é estável e todos os padrões foram validados nas fases anteriores.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Calcular comparativo na view (não no template) é a abordagem recomendada | Standard Stack / Code Examples | Baixo — alternativa é `widthratio` no template, mas perde precisão decimal |
| A2 | Usar `HX-Redirect` após adicionar/remover cotação (reload completo da página de detalhe) é mais simples que atualizar deltas via DOM | Pitfall 2 / Pattern 1 | Baixo — D-10 já define tabela estática; ambas as abordagens funcionam |
| A3 | Não é necessário `unique_together = [("rfq", "fornecedor")]` — múltiplas cotações do mesmo fornecedor podem ser permitidas | Anti-Patterns | Médio — se regra de negócio proibir duplicidade, precisa de constraint |

---

## Open Questions

1. **Duplicidade de fornecedor por RFQ**
   - O que sabemos: CONTEXT.md não define unicidade de fornecedor por RFQ
   - O que está incerto: Múltiplas cotações do mesmo fornecedor (ex: rounds de negociação) devem ser permitidas?
   - Recomendação: Implementar sem `unique_together` inicialmente (mais flexível); adicionar validação no form com mensagem de erro se a regra de negócio for confirmada como proibitiva

2. **Feedback visual após adicionar cotação via HTMX**
   - O que sabemos: D-10 define tabela estática; reload após add/remove é aceitável
   - O que está incerto: Usar `HX-Redirect` (reload total) ou `hx-swap` + trigger para refresh da tabela inteira?
   - Recomendação: `HX-Redirect` para `/cotacoes/<pk>/` após POST bem-sucedido — mais simples, garantidamente correto nos deltas, consistente com D-10

---

## Environment Availability

Step 2.6: SKIPPED — nenhuma dependência externa nova. A fase usa exclusivamente o stack já instalado (Docker + PostgreSQL + Django + django-htmx). Verificado via `config/settings/base.py` INSTALLED_APPS e `requirements.txt` do projeto.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest-django (configurado em `pytest.ini`) |
| Config file | `pytest.ini` (raiz do projeto) |
| Quick run command | `pytest apps/cotacoes/ -x -q` |
| Full suite command | `pytest --tb=short -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| COT-01 | Criar RFQ vinculado a requisição aprovada | unit | `pytest apps/cotacoes/tests/test_services.py::TestCriarRFQ -x` | ❌ Wave 0 |
| COT-01 | OneToOneField: segundo RFQ levanta IntegrityError | unit | `pytest apps/cotacoes/tests/test_services.py::TestCriarRFQDuplicado -x` | ❌ Wave 0 |
| COT-01 | View `/cotacoes/nova/` exige Comprador (403 para Solicitante) | unit | `pytest apps/cotacoes/tests/test_views.py::TestNovaRFQView::test_acesso_negado_solicitante -x` | ❌ Wave 0 |
| COT-01 | Select de requisições filtra por APROVADO e sem RFQ vinculado | unit | `pytest apps/cotacoes/tests/test_views.py::TestNovaRFQView::test_select_filtra_aprovadas_sem_rfq -x` | ❌ Wave 0 |
| COT-02 | Adicionar cotação retorna partial HTMX (ou redirect) | unit | `pytest apps/cotacoes/tests/test_views.py::TestAdicionarCotacaoView -x` | ❌ Wave 0 |
| COT-02 | Remover cotação remove linha (outerHTML swap vazio) | unit | `pytest apps/cotacoes/tests/test_views.py::TestRemoverCotacaoView -x` | ❌ Wave 0 |
| COT-02 | Bloquear add/remove após vencedor definido (403) | unit | `pytest apps/cotacoes/tests/test_views.py::TestBloqueioPosSeletcao -x` | ❌ Wave 0 |
| COT-03 | calcular_comparativo retorna menor preço com is_menor=True | unit | `pytest apps/cotacoes/tests/test_services.py::TestCalcularComparativo -x` | ❌ Wave 0 |
| COT-03 | Delta % calculado corretamente para 2+ fornecedores | unit | `pytest apps/cotacoes/tests/test_services.py::TestDeltaPercentual -x` | ❌ Wave 0 |
| COT-03 | Delta % = 0 quando preco_unitario = 0 (guard) | unit | `pytest apps/cotacoes/tests/test_services.py::TestDeltaZero -x` | ❌ Wave 0 |
| COT-04 | selecionar_vencedor usa select_for_update + atomic | unit | `pytest apps/cotacoes/tests/test_services.py::TestSelecionarVencedor -x` | ❌ Wave 0 |
| COT-04 | selecionar_vencedor levanta ValueError se já há vencedor | unit | `pytest apps/cotacoes/tests/test_services.py::TestVencedorImutavel -x` | ❌ Wave 0 |
| COT-04 | Justificativa vazia levanta ValueError | unit | `pytest apps/cotacoes/tests/test_services.py::TestJustificativaObrigatoria -x` | ❌ Wave 0 |
| COT-04 | Modal de seleção: GET retorna partial; POST confirma e redireciona | unit | `pytest apps/cotacoes/tests/test_views.py::TestModalSelecionarVencedor -x` | ❌ Wave 0 |

### Sampling Rate
- **Por task commit:** `pytest apps/cotacoes/ -x -q`
- **Por wave merge:** `pytest --tb=short -q`
- **Phase gate:** Suite completa verde antes do `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `apps/cotacoes/tests/__init__.py`
- [ ] `apps/cotacoes/tests/conftest.py` — fixtures `rfq`, `cotacao_fornecedor`, `requisicao_aprovada`, `comprador_user`, `fornecedor`
- [ ] `apps/cotacoes/tests/test_models.py`
- [ ] `apps/cotacoes/tests/test_services.py`
- [ ] `apps/cotacoes/tests/test_views.py`
- [ ] Framework já instalado — nenhuma nova instalação necessária

---

## Security Domain

> `security_enforcement: true`, `security_asvs_level: 1` em `.planning/config.json`.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | `LoginRequiredMixin` via `CompradorRequiredMixin` — já em uso |
| V3 Session Management | yes | Django session backend — já configurado na Fase 1 |
| V4 Access Control | yes | `CompradorRequiredMixin` bloqueia Solicitante/Gestor/Diretor com 403 |
| V5 Input Validation | yes | `DecimalField` + `MinValueValidator` em `preco_unitario`; `max_length` em CharField; Django forms com `full_clean()` |
| V6 Cryptography | no | Sem dados sensíveis de criptografia nesta fase |

### Known Threat Patterns for this Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| IDOR — Comprador A acessa RFQ do Comprador B via pk URL | Elevation of Privilege | `get_object_or_404(RFQ, pk=rfq_pk)` — RFQ não tem isolamento por usuário (global para Compradores), mas `CompradorRequiredMixin` restringe ao papel correto |
| Race condition em seleção de vencedor simultânea | Tampering | `select_for_update() + transaction.atomic()` no `selecionar_vencedor()` service |
| Modificação de vencedor já definido via POST direto | Tampering | Guard `if rfq.tem_vencedor: return HttpResponse(status=403)` + validação no service com `ValueError` |
| Cotação com `preco_unitario=0` causando divisão por zero | Tampering | `MinValueValidator(Decimal("0.01"))` no model + guard `if menor > 0` no service |
| CSRF em forms HTMX | Forgery | Já mitigado globalmente em `base.html` via `htmx:configRequest` event |
| Injeção via `justificativa_selecao` | Tampering | Django ORM parameteriza queries; template auto-escapa HTML — sem risco adicional |

---

## Sources

### Primary (HIGH confidence)
- `apps/aprovacoes/views.py` — padrão de modal HTMX (`ModalReprovarView`, `retarget`, `reswap`) [VERIFIED: codebase]
- `apps/aprovacoes/services.py` — padrão de `select_for_update + transaction.atomic` [VERIFIED: codebase]
- `apps/fornecedores/views.py` — `CompradorRequiredMixin`, `get_queryset_fornecedores` [VERIFIED: codebase]
- `apps/core/models.py` — `TimestampedModel`, `AuditedModel` [VERIFIED: codebase]
- `apps/requisicoes/models.py` — `Requisicao.Status.APROVADO`, `OneToOneField` destino [VERIFIED: codebase]
- `templates/base.html` — nav sidebar com guard de role e `#modal-container` padrão [VERIFIED: codebase]
- `static/css/main.css` — `--color-accent: #e94560`, classes `.badge`, `.table-container`, `.btn` [VERIFIED: codebase]
- `pytest.ini` — configuração de teste [VERIFIED: codebase]
- `CLAUDE.md` — stack mandatório, `DecimalField`, service layer, HTMX patterns [VERIFIED: codebase]

### Secondary (MEDIUM confidence)
- Padrão `label_from_instance` em ModelChoiceField — documentação Django padrão [ASSUMED]
- `HX-Redirect` como resposta após POST HTMX bem-sucedido — padrão HTMX documentado [ASSUMED]

---

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — sem novos pacotes; reutilização de stack verificado em codebase
- Architecture: HIGH — todos os padrões (service layer, modais HTMX, mixins) verificados na codebase
- Pitfalls: HIGH para pitfalls 1-5 (verificados via análise de código); MEDIUM para pitfall 6 (depende de decisão de negócio)
- Testes: HIGH — padrão pytest-django verificado em 4 apps existentes

**Research date:** 2026-06-11
**Valid until:** 2026-09-11 (stack estável; sem dependências externas novas)
