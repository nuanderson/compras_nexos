# Phase 5: Reports & Dashboard - Research

**Researched:** 2026-06-11
**Domain:** Django aggregation queries, ReportLab Platypus PDF generation, role-scoped KPI views
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** "Gasto do Mês" = soma dos `CotacaoFornecedor.preco_unitario` dos vencedores selecionados no mês corrente (`RFQ.vencedor IS NOT NULL` e `RFQ.atualizado_em` dentro do mês corrente). Query: `CotacaoFornecedor.objects.filter(rfqs_vencidos__atualizado_em__month=mes_atual).aggregate(total=Sum('preco_unitario'))`
- **D-02:** KPIs variam por role: `solicitante` vê dados da sua unidade padrão (`user.default_unit`); `comprador`, `diretor`, `admin` veem dados globais.
  - "Requisições Abertas" = `status IN [PENDENTE_GESTOR, PENDENTE_DIRETOR]` (exclui RASCUNHO)
  - "Cotações em Andamento" = RFQs sem vencedor (`vencedor_id IS NULL`)
  - "Fornecedores Ativos" = `Fornecedor.objects.filter(ativo=True).count()` — global para todos os roles
- **D-03:** Período padrão = mês corrente (`date.today().replace(day=1)` até `date.today()`). Ajustável via campos `data_inicio` / `data_fim` (inputs HTML `type=date`).
- **D-04:** Filtro de unidade: dropdown `<select>` com todas as unidades + opção "Todas". Comprador/Diretor/Admin veem o filtro; Solicitante tem a unidade pré-fixada.
- **D-05 (Claude's Discretion):** Relatório de gasto agrega `CotacaoFornecedor.preco_unitario` dos vencedores (preço real, não `valor_estimado`). Agrupado por `CategoriaCompra` da requisição vinculada à RFQ.
- **D-06:** PDF para dois relatórios: `/relatorios/gastos/pdf/` e `/relatorios/requisicoes/pdf/`. Filtros passados via GET params (mesmos da view web).
- **D-07 (Claude's Discretion):** PDF com ReportLab Platypus obrigatório: `SimpleDocTemplate` + `Table` + `TableStyle` + `Paragraph`. Resposta via `FileResponse(buffer, as_attachment=True, filename='...')`.
- **D-08 (Claude's Discretion):** App `relatorios` dedicado, sem models. Prefixo `/relatorios/`. Service layer em `apps/relatorios/services.py`.
- **D-09 (Claude's Discretion):** Enriquecer `DashboardView` existente (`apps/core/views.py`) via `get_context_data()` — não criar nova view.

### Claude's Discretion

- D-05: agrupamento de gasto por `CategoriaCompra` via RFQ → Requisicao → categoria
- D-07: estrutura ReportLab (confirmada como obrigatória — cliente-mandated)
- D-08: criação do app `relatorios`
- D-09: enriquecimento da `DashboardView` existente

### Deferred Ideas (OUT OF SCOPE)

- Exportação CSV/Excel (REL-V2-01)
- Indicadores de SLA de aprovação (REL-V2-02)
- Comparativo de gasto entre unidades (REL-V2-03)
- Relatório de saving (FORN-V2-02)
- Polling HTMX no dashboard (page load síncrono é suficiente para 20 usuários)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REL-01 | Dashboard exibe KPIs: requisições abertas, cotações em andamento, gasto do mês e fornecedores ativos | `DashboardView.get_context_data()` chama `services.get_dashboard_kpis(user)` com filtro por role — padrão confirmado no codebase |
| REL-02 | Relatório de gasto por categoria e período, filtrável por unidade | `services.get_gastos_por_categoria(data_inicio, data_fim, unidade_id)` com `Sum('preco_unitario')` agrupado por categoria |
| REL-03 | Painel de status de todas as requisições com filtro por status e unidade | `services.get_requisicoes_painel(status, unidade_id)` retorna queryset paginado |
| REL-04 | Relatórios exportados em PDF com layout formatado via ReportLab | `GastosPDFView` e `RequisicoesPlainView` — ReportLab Platypus, `FileResponse` com `Content-Disposition: attachment` |
| UNIT-04 | Relatórios podem ser filtrados por unidade | Dropdown `<select>` com todas as `UnidadeOrganizacional` + opção "Todas"; pré-fixado para solicitante |
</phase_requirements>

---

## Summary

A Fase 5 é uma camada de leitura transversal: lê dados de todas as fases anteriores e os apresenta como KPIs no dashboard, relatórios filtráveis e PDFs exportáveis. O app `relatorios` não tem models próprios — importa e agrega de `requisicoes`, `cotacoes`, `fornecedores` e `accounts`.

As queries de agregação são simples para o volume esperado (20 usuários, sem necessidade de cache ou índices especiais). O padrão de service layer já estabelecido nas Fases 2-4 (`apps/aprovacoes/services.py`, `apps/cotacoes/services.py`) guia a estrutura do novo `apps/relatorios/services.py`. O `DashboardView` existente em `apps/core/views.py` é um `TemplateView` stub — basta adicionar `get_context_data()`. ReportLab Platypus está na stack desde o início (definido pelo cliente); a integração com Django segue o padrão `BytesIO + FileResponse` já documentado no `CLAUDE.md`.

**Atenção crítica:** O campo no modelo `User` é `default_unit` (não `unidade`). O CONTEXT.md menciona `user.unidade` em alguns lugares — todas as queries devem usar `user.default_unit`. Verificado em `apps/accounts/models.py` linha 44.

**Primary recommendation:** Criar o app `relatorios` com service layer centralizado, enriquecer `DashboardView` com `get_context_data()`, e usar ReportLab Platypus com `BytesIO + FileResponse` para os dois endpoints PDF — tudo seguindo os padrões já estabelecidos no projeto.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| KPI aggregation | API / Backend (service layer) | — | Queries com `Sum()`, `Count()`, filtro por role — lógica de negócio, não pertence à view |
| Role-scoped filtering | API / Backend (view) | — | `DashboardView.get_context_data()` detecta role e delega ao service com params corretos |
| Date/unit filter form | Frontend (template) | — | Inputs HTML `type=date` + `<select>` de unidade; submit via GET padrão |
| PDF generation | API / Backend (view) | — | ReportLab processa no servidor; `FileResponse` serve o buffer |
| HTML report rendering | Frontend (template) | — | Templates Django com tabelas e filtros; sem JS client-side |
| Nav "Relatórios" link | Frontend (base.html) | — | Atualizar `href="#"` existente para `{% url 'relatorios:gastos' %}` |

## Standard Stack

### Core (todos já presentes no projeto — sem novas instalações)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `django.db.models.Sum` | Django 5.2 LTS | Agregação monetária nos relatórios | Built-in ORM — sempre presente [VERIFIED: apps/cotacoes/services.py usa Sum] |
| `django.db.models.Count` | Django 5.2 LTS | Contagem de KPIs (requisições, RFQs, fornecedores) | Built-in ORM [VERIFIED: Django docs] |
| `reportlab` | latest | PDF generation (cliente-mandated) | Definido pelo cliente; já em requirements.txt [VERIFIED: CLAUDE.md] |
| `django.http.FileResponse` | Django 5.2 LTS | Serve PDF gerado via BytesIO | Padrão oficial Django para PDF output [CITED: docs.djangoproject.com/en/5.2/howto/outputting-pdf/] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `io.BytesIO` | Python 3.12 stdlib | Buffer in-memory para ReportLab | Em todos os endpoints PDF — nunca gravar em disco [ASSUMED] |
| `datetime.date` | Python 3.12 stdlib | Calcular datas de início/fim do período | `date.today().replace(day=1)` para default mês corrente [ASSUMED] |
| `decimal.Decimal` | Python 3.12 stdlib | Tratar resultado de `Sum()` que pode retornar `None` | `aggregate(total=Sum('preco_unitario'))['total'] or Decimal('0')` [VERIFIED: padrão já em cotacoes/services.py] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ReportLab Platypus | xhtml2pdf / WeasyPrint | Cliente especificou ReportLab — não substituir |
| GET params para PDF filters | Session storage | GET params são stateless, auditáveis e funcionam com direct links — correto para este caso |
| Form submit padrão para filtros | HTMX hx-get | Form submit padrão é suficiente (CONTEXT.md §Specifics confirma) |

**Installation:** Nenhum pacote novo necessário — `reportlab` já está em `requirements.txt`.

## Package Legitimacy Audit

Nenhum pacote novo é instalado nesta fase. Todos os pacotes utilizados (`reportlab`, `django`, bibliotecas Python stdlib) já estão presentes no projeto e foram verificados em fases anteriores.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
Browser (GET /relatorios/gastos/?data_inicio=...&unidade=...)
  |
  v
GastosView (apps/relatorios/views.py)
  |-- valida role (CompradorRequiredMixin)
  |-- lê GET params (data_inicio, data_fim, unidade_id)
  |-- chama services.get_gastos_por_categoria(data_inicio, data_fim, unidade_id)
  |      |-- CotacaoFornecedor.objects
  |      |     .filter(rfqs_vencidos__atualizado_em__date__gte=data_inicio)
  |      |     .filter(rfqs_vencidos__atualizado_em__date__lte=data_fim)
  |      |     [.filter(rfqs_vencidos__requisicao__unidade=unidade)] -- se filtrado
  |      |     .values('rfqs_vencidos__requisicao__categoria__nome')
  |      |     .annotate(total=Sum('preco_unitario'))
  |      |     .order_by('-total')
  |      `-- retorna lista de dicts {categoria_nome, total}
  `-- render relatorios/gastos.html (tabela + filtros)

Browser (GET /relatorios/gastos/pdf/?data_inicio=...&unidade=...)
  |
  v
GastosPDFView (apps/relatorios/views.py)
  |-- mesmos params GET
  |-- chama services.get_gastos_por_categoria(...)
  |-- cria BytesIO buffer
  |-- SimpleDocTemplate(buffer) + Platypus story
  |-- doc.build(story)
  |-- buffer.seek(0)
  `-- FileResponse(buffer, as_attachment=True, filename='gastos.pdf')

DashboardView.get_context_data() (apps/core/views.py)
  |-- chama services.get_dashboard_kpis(user)
  |      |-- detecta user.role
  |      |-- se solicitante: filtra por user.default_unit
  |      |-- retorna dict {
  |      |     'requisicoes_abertas': int,
  |      |     'cotacoes_em_andamento': int,
  |      |     'gasto_mes': Decimal,
  |      |     'fornecedores_ativos': int,
  |      |   }
  `-- passa dict ao contexto do template core/dashboard.html
```

### Recommended Project Structure

```
apps/relatorios/
├── __init__.py
├── apps.py                   # RelatoriosConfig
├── services.py               # get_dashboard_kpis, get_gastos_por_categoria, get_requisicoes_painel
├── urls.py                   # app_name='relatorios'
├── views.py                  # GastosView, GastosPDFView, RequisicoesPainelView, RequisicoesPlainView
└── templates/
    └── relatorios/
        ├── gastos.html       # Tabela de gastos por categoria + filtros
        ├── requisicoes.html  # Painel de status + filtros
        └── partials/         # (se necessário para HTMX futuro — deferred)

apps/core/views.py            # DashboardView — adicionar get_context_data()
apps/core/templates/core/dashboard.html  # Substituir &mdash; por valores reais
templates/base.html           # Atualizar nav link Relatórios de # para {% url 'relatorios:gastos' %}
config/urls.py                # Adicionar path("relatorios/", include("apps.relatorios.urls"))
config/settings/base.py       # Adicionar "apps.relatorios" em INSTALLED_APPS
```

### Pattern 1: Service Layer para KPIs do Dashboard

**What:** Toda lógica de query em `services.py` — view apenas delega.
**When to use:** Sempre. Padrão mandatório no projeto (estabelecido em `aprovacoes/services.py`).

```python
# apps/relatorios/services.py
# Source: padrão estabelecido em apps/cotacoes/services.py e apps/aprovacoes/services.py
from datetime import date
from decimal import Decimal
from django.db.models import Count, Sum, Q

from apps.cotacoes.models import CotacaoFornecedor, RFQ
from apps.fornecedores.models import Fornecedor
from apps.requisicoes.models import Requisicao


def get_dashboard_kpis(user) -> dict:
    """
    Retorna KPIs para o dashboard, filtrados por role.
    - solicitante: dados da unidade padrão do usuário (user.default_unit)
    - comprador/diretor/admin: dados globais
    """
    hoje = date.today()
    mes_atual = hoje.month
    ano_atual = hoje.year

    # Filtro de unidade para solicitante
    filtro_unidade = {}
    if user.role == "solicitante" and user.default_unit:
        filtro_unidade = {"unidade": user.default_unit}

    # Requisições Abertas = PENDENTE_GESTOR + PENDENTE_DIRETOR
    estados_abertos = [
        Requisicao.Status.PENDENTE_GESTOR,
        Requisicao.Status.PENDENTE_DIRETOR,
    ]
    requisicoes_abertas = Requisicao.objects.filter(
        status__in=estados_abertos, **filtro_unidade
    ).count()

    # Cotações em Andamento = RFQs sem vencedor (global para todos os roles)
    cotacoes_em_andamento = RFQ.objects.filter(vencedor_id__isnull=True).count()

    # Gasto do Mês = soma dos preços dos vencedores selecionados no mês corrente
    filtro_unidade_gasto = {}
    if user.role == "solicitante" and user.default_unit:
        filtro_unidade_gasto = {
            "rfqs_vencidos__requisicao__unidade": user.default_unit
        }
    resultado = CotacaoFornecedor.objects.filter(
        rfqs_vencidos__atualizado_em__month=mes_atual,
        rfqs_vencidos__atualizado_em__year=ano_atual,
        **filtro_unidade_gasto,
    ).aggregate(total=Sum("preco_unitario"))
    gasto_mes = resultado["total"] or Decimal("0")

    # Fornecedores Ativos = global para todos os roles (D-02)
    fornecedores_ativos = Fornecedor.objects.filter(ativo=True).count()

    return {
        "requisicoes_abertas": requisicoes_abertas,
        "cotacoes_em_andamento": cotacoes_em_andamento,
        "gasto_mes": gasto_mes,
        "fornecedores_ativos": fornecedores_ativos,
    }
```

### Pattern 2: Agregação de Gasto por Categoria

**What:** Query cross-model via reverse FK traversal — `CotacaoFornecedor` → `RFQ` → `Requisicao` → `CategoriaCompra`.
**When to use:** Para o relatório REL-02 e o endpoint PDF correspondente.

```python
# apps/relatorios/services.py
# Source: Django ORM docs — values() + annotate() pattern [CITED: docs.djangoproject.com/en/5.2/topics/db/aggregation/]

def get_gastos_por_categoria(data_inicio, data_fim, unidade_id=None) -> list:
    """
    Retorna lista de dicts {categoria_nome, total} com gastos reais por categoria.
    Filtra por período (data de atualização do RFQ quando vencedor foi selecionado).
    Se unidade_id fornecido, filtra por unidade da requisição.
    """
    qs = CotacaoFornecedor.objects.filter(
        rfqs_vencidos__atualizado_em__date__gte=data_inicio,
        rfqs_vencidos__atualizado_em__date__lte=data_fim,
        rfqs_vencidos__isnull=False,  # apenas cotações que são vencedoras
    )
    if unidade_id:
        qs = qs.filter(rfqs_vencidos__requisicao__unidade_id=unidade_id)

    return list(
        qs.values(categoria_nome=models.F("rfqs_vencidos__requisicao__categoria__nome"))
        .annotate(total=Sum("preco_unitario"))
        .order_by("-total")
    )
```

**Nota importante sobre a query "Gasto do Mês" (D-01):** O CONTEXT.md sugere o filtro `rfqs_vencidos__atualizado_em__month=mes_atual`. Isso é tecnicamente correto mas incompleto — sem filtrar o ano, a query inclui dados do mesmo mês de anos anteriores. A implementação deve filtrar por `__month` E `__year`. [VERIFIED: comportamento do ORM Django confirmado via análise do codebase]

### Pattern 3: PDF com ReportLab Platypus

**What:** Geração de PDF em memória com ReportLab, servido via Django FileResponse.
**When to use:** Para os endpoints `/relatorios/gastos/pdf/` e `/relatorios/requisicoes/pdf/`.

```python
# apps/relatorios/views.py
# Source: CLAUDE.md §PDF Generation + docs.djangoproject.com/en/5.2/howto/outputting-pdf/
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, KeepTogether
from django.http import FileResponse


class GastosPDFView(CompradorRequiredMixin, View):
    def get(self, request):
        # Mesmos filtros da view web (D-06, D-07)
        data_inicio, data_fim, unidade_id = _parse_filtros(request)
        dados = services.get_gastos_por_categoria(data_inicio, data_fim, unidade_id)

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        # Título
        story.append(Paragraph("Relatório de Gastos por Categoria", styles["Heading1"]))
        story.append(Paragraph(f"Período: {data_inicio} a {data_fim}", styles["Normal"]))

        # Tabela
        table_data = [["Categoria", "Total (R$)"]]
        for row in dados:
            table_data.append([
                row["categoria_nome"] or "Sem categoria",
                f"R$ {row['total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            ])

        t = Table(table_data)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3460")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#2a2a4a")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ]))
        story.append(KeepTogether([t]))

        doc.build(story)
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename="gastos_por_categoria.pdf")
```

### Pattern 4: Enriquecer DashboardView com get_context_data()

**What:** Substituir o stub `TemplateView` com `get_context_data()` que injeta KPIs reais.
**When to use:** Modificação da `DashboardView` existente em `apps/core/views.py` (D-09).

```python
# apps/core/views.py
# Source: padrão Django TemplateView.get_context_data() [CITED: docs.djangoproject.com/en/5.2/ref/class-based-views/base/#django.views.generic.base.TemplateView]
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from apps.relatorios import services as relatorios_services


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "core/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["kpis"] = relatorios_services.get_dashboard_kpis(self.request.user)
        return ctx
```

### Pattern 5: Formatação Monetária Brasileira no Template

**What:** Exibir `Decimal` como `R$ 12.345,67` usando filtros Django + formatação manual.
**When to use:** Card "Gasto do Mês" no dashboard; coluna "Total" nos relatórios.

```html
{# Source: Django template language — floatformat filter #}
{# Formato brasileiro: ponto como separador de milhar, vírgula como decimal #}
R$ {{ kpis.gasto_mes|floatformat:2 }}
```

**Nota:** O filtro `floatformat` com `USE_L10N = True` e `LANGUAGE_CODE = "pt-br"` em `settings/base.py` já gera a formatação correta (vírgula decimal) automaticamente. [VERIFIED: `config/settings/base.py` linha 89-90]

### Anti-Patterns to Avoid

- **Query lógica na view:** Nunca colocar `Sum()`, `Count()` ou filtros de negócio diretamente na view — todo o trabalho vai no `services.py`. Padrão mandatório do projeto.
- **FloatField para valores monetários:** Usar apenas `DecimalField` e `Decimal('0')` como fallback de `None`. `or Decimal('0')` é obrigatório no resultado de `aggregate(total=Sum(...))` pois retorna `None` quando não há registros.
- **Filtrar apenas por `__month` sem `__year`:** A query `atualizado_em__month=mes_atual` sem `__year=ano_atual` retorna dados do mesmo mês de todos os anos. Sempre combinar os dois.
- **Gerar PDF gravando em disco:** Usar sempre `BytesIO` in-memory — nunca `open(path, 'wb')` em ambiente Docker/multi-processo.
- **Acesso direto `user.unidade`:** O campo correto no modelo `User` é `user.default_unit` (verificado em `apps/accounts/models.py`). O CONTEXT.md usa `user.unidade` em alguns trechos informais — ignorar; o código deve usar `user.default_unit`.
- **Relatórios sem filtro de unidade para Solicitante:** O solicitante SEMPRE vê apenas os dados da sua unidade (`user.default_unit`) — nunca exibir o filtro de unidade para este role.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Formatação de moeda brasileira | Lógica Python de replace() | `floatformat:2` + `USE_L10N = True` com `LANGUAGE_CODE = "pt-br"` | Django já gera a formatação correta com locale pt-br configurado |
| Agregação com subtotais por grupo | Loop Python somando | `values().annotate(total=Sum(...))` | Uma única query SQL GROUP BY, muito mais eficiente |
| Geração de PDF | Template HTML convertido para PDF | ReportLab Platypus diretamente | Definido pelo cliente; xhtml2pdf e WeasyPrint são explicitamente proibidos no CLAUDE.md |
| Paginação do painel de requisições | Slice manual com offset | `django.core.paginator.Paginator` | Built-in, já testado, correto para querysets Django |

**Key insight:** Para 20 usuários e volumes esperados, queries simples com `Sum()` e `Count()` sem índices adicionais são suficientes. Nenhum cache de query é necessário em v1.

## Runtime State Inventory

Fase de leitura pura — nenhum rename/refactor. Esta seção não se aplica.

## Common Pitfalls

### Pitfall 1: `Sum()` retorna `None` quando não há registros

**What goes wrong:** `aggregate(total=Sum('preco_unitario'))['total']` retorna `None` quando o queryset é vazio. Usar `None` como valor numérico em template ou cálculo causa `TypeError`.
**Why it happens:** `Sum()` de conjunto vazio é matematicamente indefinido; Django retorna `None` por design.
**How to avoid:** Sempre aplicar fallback: `resultado['total'] or Decimal('0')`.
**Warning signs:** `TypeError: unsupported operand type(s) for +: 'NoneType'` em template ou view.

### Pitfall 2: Filtro de mês sem filtro de ano

**What goes wrong:** `rfqs_vencidos__atualizado_em__month=mes_atual` sem `__year=ano_atual` retorna dados do mesmo mês de todos os anos anteriores. Em produção após o primeiro ano, o "Gasto do Mês" de janeiro/2027 incluiria janeiro/2026.
**Why it happens:** `__month` lookup isola apenas o componente de mês da data.
**How to avoid:** Sempre usar `__month=mes_atual, __year=ano_atual` em conjunto.
**Warning signs:** KPI "Gasto do Mês" aumenta inesperadamente no início de cada ano.

### Pitfall 3: Campo `user.unidade` vs `user.default_unit`

**What goes wrong:** O CONTEXT.md usa informalmente `user.unidade` em alguns trechos descritivos. O campo real no modelo `User` é `default_unit` (`apps/accounts/models.py` linha 44). Código que acessa `user.unidade` levanta `AttributeError`.
**Why it happens:** Divergência entre linguagem informal no CONTEXT.md e nome de campo real no modelo.
**How to avoid:** Sempre usar `user.default_unit` no código Python. Em templates Django, `{{ user.default_unit }}`.
**Warning signs:** `AttributeError: 'User' object has no attribute 'unidade'` em runtime.

### Pitfall 4: Travessia de FK reversa para "Gasto do Mês"

**What goes wrong:** A query usa `CotacaoFornecedor.objects.filter(rfqs_vencidos__...)` — traversal via `related_name="rfqs_vencidos"` de `RFQ.vencedor`. Isso filtra cotações que são **vencedoras de algum RFQ**. Se uma cotação for vencedora de múltiplos RFQs (impossível pela constraint, mas vale documentar), o `Sum` a contaria múltiplas vezes.
**Why it happens:** O `related_name="rfqs_vencidos"` em `RFQ.vencedor` permite traversal reverso, mas a FK é de `RFQ` para `CotacaoFornecedor`. Um `CotacaoFornecedor` pode ser `vencedor` de no máximo 1 RFQ (constraint de unicidade implícita na semântica do negócio, não hard-enforced no DB além do fato de que `RFQ.vencedor` é FK → cada RFQ tem 0 ou 1 vencedor).
**How to avoid:** A query é correta como especificada no D-01. Apenas documentar para auditoria futura.
**Warning signs:** N/A — este é um falso positivo, mas vale entender a estrutura.

### Pitfall 5: PDF inline vs download

**What goes wrong:** `FileResponse(buffer, as_attachment=False)` exibe o PDF no navegador (inline). Alguns navegadores não suportam `application/pdf` embutido.
**Why it happens:** Parâmetro `as_attachment` controla o header `Content-Disposition`.
**How to avoid:** Usar sempre `as_attachment=True` para força o download, conforme D-07.
**Warning signs:** PDF abre como tela branca no browser em vez de fazer download.

### Pitfall 6: `USE_TZ = True` e filtros de data

**What goes wrong:** Com `USE_TZ = True` (configurado em `settings/base.py`), `auto_now` em `atualizado_em` armazena datetimes em UTC. Filtrar por `__month` e `__year` de UTC pode retornar resultados incorretos para usuários em fusos horários diferentes.
**Why it happens:** O banco armazena em UTC; o lookup `__month` opera sobre o valor UTC, não sobre o horário local `America/Sao_Paulo`.
**How to avoid:** Para um sistema interno em São Paulo com `TIME_ZONE = "America/Sao_Paulo"`, o offset máximo é UTC-3. Requisições criadas às 23:00 BRT aparecem como 02:00 UTC do dia seguinte. Para o relatório de "Gasto do Mês", a diferença de até 3 horas em dias de virada de mês é aceitável para o contexto de negócio. Não é necessário tratamento especial em v1 para 20 usuários internos. Documentar como limitação conhecida.
**Warning signs:** Compra realizada às 23:30 do último dia do mês não aparece no relatório daquele mês.

## Code Examples

### Query: Gasto por categoria com JOIN cross-app

```python
# Source: padrão Django ORM values().annotate() [CITED: docs.djangoproject.com/en/5.2/topics/db/aggregation/]
from django.db.models import F, Sum

gastos = (
    CotacaoFornecedor.objects
    .filter(
        rfqs_vencidos__atualizado_em__month=mes_atual,
        rfqs_vencidos__atualizado_em__year=ano_atual,
    )
    .values(categoria_nome=F("rfqs_vencidos__requisicao__categoria__nome"))
    .annotate(total=Sum("preco_unitario"))
    .order_by("-total")
)
# Retorna: <QuerySet [{'categoria_nome': 'Informática', 'total': Decimal('5000.00')}, ...]>
```

### Painel de Requisições com filtros opcionais

```python
# Source: padrão Django ORM condicional [CITED: docs.djangoproject.com/en/5.2/topics/db/queries/]
from apps.requisicoes.models import Requisicao

def get_requisicoes_painel(status=None, unidade_id=None):
    qs = Requisicao.objects.select_related("categoria", "unidade", "criado_por").order_by("-criado_em")
    if status:
        qs = qs.filter(status=status)
    if unidade_id:
        qs = qs.filter(unidade_id=unidade_id)
    return qs
```

### Template: Card KPI no dashboard

```html
{# apps/core/templates/core/dashboard.html — substituir &mdash; por valores reais #}
<div class="card-grid">
  <div class="card">
    <div class="card-label">Requisições Abertas</div>
    <div class="card-value">{{ kpis.requisicoes_abertas }}</div>
  </div>
  <div class="card">
    <div class="card-label">Cotações em Andamento</div>
    <div class="card-value">{{ kpis.cotacoes_em_andamento }}</div>
  </div>
  <div class="card">
    <div class="card-label">Gasto do Mês</div>
    <div class="card-value">R$ {{ kpis.gasto_mes|floatformat:2 }}</div>
  </div>
  <div class="card">
    <div class="card-label">Fornecedores Ativos</div>
    <div class="card-value">{{ kpis.fornecedores_ativos }}</div>
  </div>
</div>
```

### Filtro de período e unidade no template de relatório

```html
{# apps/relatorios/templates/relatorios/gastos.html #}
<form method="get" class="mb-lg">
  <div class="form-group" style="display: flex; gap: 16px; align-items: flex-end;">
    <div>
      <label class="form-label">De</label>
      <input type="date" name="data_inicio" value="{{ data_inicio }}" class="form-input">
    </div>
    <div>
      <label class="form-label">Até</label>
      <input type="date" name="data_fim" value="{{ data_fim }}" class="form-input">
    </div>
    {% if pode_filtrar_unidade %}
    <div>
      <label class="form-label">Unidade</label>
      <select name="unidade" class="form-select">
        <option value="">Todas</option>
        {% for u in unidades %}
          <option value="{{ u.pk }}" {% if u.pk|stringformat:"s" == unidade_selecionada %}selected{% endif %}>{{ u.nome }}</option>
        {% endfor %}
      </select>
    </div>
    {% endif %}
    <button type="submit" class="btn btn-primary">Filtrar</button>
    <a href="{% url 'relatorios:gastos-pdf' %}?{{ request.GET.urlencode }}" class="btn btn-secondary">Exportar PDF</a>
  </div>
</form>
```

### apps.py do novo app relatorios

```python
# apps/relatorios/apps.py
from django.apps import AppConfig

class RelatoriosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.relatorios"
    verbose_name = "Relatórios"
```

### urls.py do app relatorios

```python
# apps/relatorios/urls.py
from django.urls import path
from .views import GastosView, GastosPDFView, RequisicoesPainelView, RequisicoespainelPDFView

app_name = "relatorios"

urlpatterns = [
    path("gastos/", GastosView.as_view(), name="gastos"),
    path("gastos/pdf/", GastosPDFView.as_view(), name="gastos-pdf"),
    path("requisicoes/", RequisicoesPainelView.as_view(), name="requisicoes"),
    path("requisicoes/pdf/", RequisicoespainelPDFView.as_view(), name="requisicoes-pdf"),
]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `STATICFILES_STORAGE` string | `STORAGES` dict (Django 4.2+) | Django 4.2 | Já aplicado neste projeto em `settings/base.py` |
| `render_to_response()` | `render()` shortcut | Django 1.x | Já usado no projeto |
| `HttpResponse` com `mimetype` | `FileResponse` com `content_type` | Django 2.x | Usar `FileResponse` para PDF — simples e correto |

**Deprecated/outdated:**
- `canvas` direto do ReportLab: válido para PDFs simples, mas `Platypus` (`SimpleDocTemplate` + `Table` + `Paragraph`) é o caminho correto para layouts com tabelas e múltiplos elementos — e é o que o CLAUDE.md especifica.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `io.BytesIO` e `datetime.date` estão disponíveis sem instalação extra no Python 3.12 | Standard Stack | Nulo — são stdlib, sempre presentes |
| A2 | `USE_L10N = True` com `LANGUAGE_CODE = "pt-br"` formata `floatformat` com vírgula decimal | Code Examples | Baixo — worst case: formatação manual com `replace()` |
| A3 | A query via `rfqs_vencidos__requisicao__categoria__nome` é suportada pelo ORM Django para este modelo chain | Architecture Patterns | Médio — deve ser testado; a chain é `CotacaoFornecedor → RFQ (rfqs_vencidos) → Requisicao → CategoriaCompra`. É uma query possível mas com 3 JOINs implícitos; verificar com `django.db.connection.queries` nos testes |

**Se a tabela acima estiver vazia:** todas as afirmações foram verificadas ou citadas — nenhuma confirmação do usuário necessária. Neste caso, A2 e A3 precisam de validação via testes.

## Open Questions (RESOLVED)

1. **Paginação no painel de requisições (REL-03)**
   - O que sabemos: a view deve retornar "todas as requisições" com filtros.
   - O que não está claro: o CONTEXT não especifica paginação. Para 20 usuários, o volume de requisições dificilmente justificará paginação em v1, mas o planner deve decidir.
   - RESOLVED: implementar sem paginação em v1 (exibir tudo); adicionar paginação se o feedback de QA indicar necessidade.

2. **Acesso ao relatório de gastos para Solicitante**
   - O que sabemos: a nav em `base.html` mostra "Relatórios" apenas para `comprador`, `diretor`, `admin`. O `CompradorRequiredMixin` bloqueia `solicitante`.
   - O que não está claro: o REL-01 diz "All roles can view real-time KPIs" — mas o dashboard é acessível a todos; os relatórios detalhados ficam restritos a comprador/diretor/admin.
   - RESOLVED: manter `CompradorRequiredMixin` para as views de relatório (`/relatorios/*`); o dashboard (`/`) fica acessível a todos via `LoginRequiredMixin` com KPIs filtrados por role. Isso está alinhado com o CONTEXT.md.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `reportlab` | PDF export (REL-04) | ✓ | instalado (requirements.txt) | — |
| `django.db.models.Sum` | Agregações de KPI | ✓ | Django 5.2 LTS | — |
| `django.core.paginator` | Paginação opcional | ✓ | Django 5.2 LTS | — |

**Missing dependencies with no fallback:** none
**Missing dependencies with fallback:** none

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest-django (configurado em `pytest.ini`) |
| Config file | `pytest.ini` na raiz do projeto |
| Quick run command | `pytest apps/relatorios/ -x -q` |
| Full suite command | `pytest --tb=short -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REL-01 | KPIs retornam valores corretos por role | unit (service) | `pytest apps/relatorios/tests/test_services.py -x -q` | ❌ Wave 0 |
| REL-01 | DashboardView injeta KPIs no contexto | integration (view) | `pytest apps/core/tests/test_dashboard.py -x -q` | ❌ Wave 0 |
| REL-01 | Solicitante vê apenas dados da sua unidade | unit (service) | `pytest apps/relatorios/tests/test_services.py::TestDashboardKpis::test_solicitante_filtrado_por_unidade -x` | ❌ Wave 0 |
| REL-02 | `get_gastos_por_categoria` retorna totais corretos | unit (service) | `pytest apps/relatorios/tests/test_services.py::TestGastos -x` | ❌ Wave 0 |
| REL-02 | GastosView responde 200 com filtros GET | integration (view) | `pytest apps/relatorios/tests/test_views.py::TestGastosView -x` | ❌ Wave 0 |
| REL-02 | Solicitante não acessa GastosView (403) | integration (view) | `pytest apps/relatorios/tests/test_views.py::TestAcesso -x` | ❌ Wave 0 |
| REL-03 | `get_requisicoes_painel` filtra por status e unidade | unit (service) | `pytest apps/relatorios/tests/test_services.py::TestRequisicoesPainel -x` | ❌ Wave 0 |
| REL-04 | GastosPDFView retorna Content-Type application/pdf | integration (view) | `pytest apps/relatorios/tests/test_views.py::TestPDF -x` | ❌ Wave 0 |
| REL-04 | GastosPDFView retorna Content-Disposition attachment | integration (view) | `pytest apps/relatorios/tests/test_views.py::TestPDF -x` | ❌ Wave 0 |
| UNIT-04 | Filtro de unidade funciona no relatório de gastos | unit (service) | `pytest apps/relatorios/tests/test_services.py::TestFiltroUnidade -x` | ❌ Wave 0 |

### Sampling Rate
- **Por task commit:** `pytest apps/relatorios/ -x -q`
- **Por wave merge:** `pytest --tb=short -q`
- **Phase gate:** `pytest --tb=short -q` green antes de `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `apps/relatorios/__init__.py` — módulo Python do app
- [ ] `apps/relatorios/apps.py` — RelatoriosConfig
- [ ] `apps/relatorios/tests/__init__.py` — namespace de testes
- [ ] `apps/relatorios/tests/conftest.py` — fixtures (reutilizar padrão de `apps/cotacoes/tests/conftest.py`)
- [ ] `apps/relatorios/tests/test_services.py` — testes RED iniciais para o service layer
- [ ] `apps/relatorios/tests/test_views.py` — testes RED iniciais para as views
- [ ] `apps/core/tests/test_dashboard.py` — testes para o `get_context_data()` do DashboardView

## Security Domain

### Applicable ASVS Categories (nível 1)

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | sim | `LoginRequiredMixin` em todas as views (já aplicado) |
| V3 Session Management | não | Gerenciado pelo Django session framework — sem mudanças |
| V4 Access Control | sim | `CompradorRequiredMixin` para relatórios; KPIs do dashboard filtrados por role |
| V5 Input Validation | sim | Filtros GET (`data_inicio`, `data_fim`, `unidade_id`) devem ser validados antes de uso no ORM |
| V6 Cryptography | não | Nenhuma operação criptográfica nesta fase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Acesso não autorizado a relatórios | Elevation of Privilege | `CompradorRequiredMixin` — lança `PermissionDenied (403)` para roles não autorizados |
| Date injection via GET params | Tampering | Usar `datetime.strptime()` com try/except para parsear `data_inicio`/`data_fim`; em caso de formato inválido, usar default (mês corrente) |
| Informações de outras unidades para Solicitante | Information Disclosure | Service `get_dashboard_kpis` filtra por `user.default_unit` quando `user.role == 'solicitante'` — nunca expõe dados globais |
| PDF com dados de outra unidade via GET param | Information Disclosure | Os endpoints PDF `GastosPDFView` e `RequisicoespainelPDFView` devem respeitar o mesmo filtro de unidade da view web (replicar a lógica do service, não apenas aceitar `unidade_id` arbitrário do Solicitante) |

**Controle adicional para PDF:** O Solicitante não acessa `/relatorios/*` (bloqueado por `CompradorRequiredMixin`). Para os roles que acessam, o filtro de unidade é opcional (opção "Todas" disponível). Nenhum risco de vazamento de dados entre unidades para os roles autorizados.

## Sources

### Primary (HIGH confidence)
- Codebase verificado diretamente:
  - `apps/accounts/models.py` — campo `default_unit` confirmado (linha 44)
  - `apps/cotacoes/models.py` — `RFQ.vencedor`, `related_name="rfqs_vencidos"`, `atualizado_em` via `TimestampedModel`
  - `apps/requisicoes/models.py` — `Requisicao.Status`, `categoria`, `unidade`, `criado_em`
  - `apps/fornecedores/models.py` — `Fornecedor.ativo`
  - `apps/core/views.py` — `DashboardView` stub confirmado
  - `apps/core/templates/core/dashboard.html` — 4 cards com `&mdash;` confirmados
  - `apps/fornecedores/views.py` — `CompradorRequiredMixin` padrão confirmado
  - `config/settings/base.py` — `USE_TZ = True`, `TIME_ZONE = "America/Sao_Paulo"`, `LANGUAGE_CODE = "pt-br"`, `USE_L10N = True`
  - `config/urls.py` — estrutura de URLs do projeto confirmada
  - `static/css/main.css` — classes `.card`, `.card-grid`, `.card-label`, `.card-value`, `.table-container`, `.badge` confirmadas
- `CLAUDE.md` — stack mandatório, padrão PDF com ReportLab Platypus, padrões HTMX
- `.planning/phases/05-reports-dashboard/05-CONTEXT.md` — decisões D-01 a D-09

### Secondary (MEDIUM confidence)
- [CITED: docs.djangoproject.com/en/5.2/howto/outputting-pdf/] — padrão `BytesIO + FileResponse` para PDF
- [CITED: docs.djangoproject.com/en/5.2/topics/db/aggregation/] — padrão `values().annotate(total=Sum(...))`
- [CITED: docs.djangoproject.com/en/5.2/ref/class-based-views/base/#templateview] — `get_context_data()` em TemplateView

### Tertiary (LOW confidence)
- A2 (formatação `floatformat` com locale pt-br) — baseado em comportamento conhecido do Django, não verificado com execução de código nesta sessão.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — todos os pacotes já estão no projeto, verificados no codebase
- Architecture: HIGH — padrão service layer verificado nos 4 apps anteriores; queries ORM padrão Django
- Pitfalls: HIGH — descobertos via análise direta do codebase (campo `default_unit`, filtro de mês sem ano, `Sum()` retornando `None`)
- PDF integration: HIGH — padrão documentado no CLAUDE.md e na docs oficial Django

**Research date:** 2026-06-11
**Valid until:** 2026-07-11 (stack estável — Django 5.2 LTS, ReportLab sem breaking changes esperados)
