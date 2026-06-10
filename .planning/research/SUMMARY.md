# Research Summary — ComprasNexos

**Synthesized:** 2026-06-10
**Overall Confidence:** HIGH (core stack e domain patterns), MEDIUM (detalhes fiscais/regulatórios brasileiros)

---

## Executive Summary

ComprasNexos é um sistema de gestão de compras para cliente corporativo de pequeno porte (~20 usuários internos), cobrindo o ciclo completo: criação de requisição, aprovação em dois níveis com alçadas configuráveis, gestão de fornecedores, RFQ/comparativo de cotações, seleção de vencedor e relatórios.

Stack mandatada pelo cliente: Python 3.12 + Django 5.2 LTS + HTMX + PostgreSQL + Docker + AWS. Não negociável.

Arquitetura: monolito Django clássico com apps por domínio (`accounts`, `core`, `requisicoes`, `aprovacoes`, `fornecedores`, `cotacoes`, `relatorios`), templates server-rendered com partials HTMX, sem infra async no v1. Com 20 usuários, Celery, Redis, WebSockets e DRF são overhead sem benefício correspondente.

---

## Stack Recomendada (Versões Específicas)

| Tecnologia | Versão | Justificativa |
|-----------|--------|--------------|
| Python | 3.12 | Mandatado pelo cliente; suportado até 2028 |
| Django | 5.2 LTS | LTS atual (abril 2025); suportado até abril 2028 |
| HTMX | 2.0.x | Decisão do cliente; event model mais limpo que 1.x |
| django-htmx | 1.x (latest) | Obrigatório — fornece `request.htmx` + HtmxMiddleware |
| PostgreSQL | 15 | Escolha segura para AWS RDS; extensões `pg_trgm` + `unaccent` obrigatórias |
| psycopg2-binary | 2.9.x | Binary para Docker (evita deps de build C) |
| django-anymail + SES | latest | Backend de email; substituível sem mudança de código |
| ReportLab | latest | Mandatado pelo cliente para PDF; usar Platypus, não canvas raw |
| whitenoise | 6.x | Arquivos estáticos — elimina complexidade do Nginx no v1 |
| gunicorn | latest | WSGI; 3 workers em t3.small (2 vCPU) |
| python-stdnum | latest | Validação de CNPJ — suporta formato numérico e novo alfanumérico (julho 2026) |
| python-decouple | 3.x | Gestão de variáveis de ambiente |
| django-debug-toolbar | latest | Apenas dev — obrigatório para detectar queries N+1 |

**Rejeições explícitas:** django-allauth, Celery + Redis, Django Channels, django-guardian, django-fsm/viewflow, DRF, SQLite em qualquer ambiente, WeasyPrint/xhtml2pdf.

---

## Features Confirmadas para v1

1. Auth + RBAC (5 perfis: Solicitante, Gestor, Comprador, Diretor, Admin — contas criadas pelo Admin)
2. Criação de requisição de compra + acompanhamento de status (estados em PT: Rascunho, Aguardando Gestor, Em Aprovação, Aprovada, Reprovada)
3. Workflow de aprovação em dois níveis com alçadas configuráveis via Django Admin (`RegraDeAlcada`)
4. Cadastro de fornecedores com validação de CNPJ via `python-stdnum` (formato alfanumérico julho 2026 pronto), categorias, status ativo/inativo
5. Criação de RFQ vinculado a requisição aprovada (OneToOneField: um RFQ por requisição)
6. Entrada de cotações de múltiplos fornecedores (preço unitário, prazo de entrega, condições de pagamento, validade, observações)
7. Comparativo lado a lado com destaque do menor preço e delta percentual
8. Seleção de vencedor com campo de justificativa obrigatório (imutável após salvo)
9. Dashboard com KPIs (requisições abertas, RFQs ativos, gasto do mês, tempo médio de aprovação)
10. Relatório de gasto por categoria com exportação PDF via ReportLab Platypus
11. Notificação por e-mail ao aprovador quando ação necessária (via SES + `on_commit()`)
12. Formatação BRL (R$ 1.234,56) em todo o sistema — server-rendered, nunca JavaScript

**Confirmados para v2:** Rating de fornecedor (modelo criado no v1), relatório de saving, exportação CSV/Excel, indicadores de SLA de aprovação, busca full-text em requisições.

**Anti-features confirmadas:** Portal de fornecedor, PO em PDF, integração ERP/NFe, bloqueio por orçamento, 2FA/SSO, IA, multi-tenant, estoque.

---

## Decisões Arquiteturais Críticas

1. **Custom User model primeiro** — `accounts.User(AbstractUser)` + `AUTH_USER_MODEL = 'accounts.User'` antes de qualquer `migrate`. Inclui `department` e `centro_de_custo` como campos nullable desde o início.

2. **Apps com dependências unidirecionais:**
   ```
   accounts, core  ←  todos os apps
   fornecedores    ←  requisicoes, cotacoes
   requisicoes     ←  aprovacoes, cotacoes, relatorios
   aprovacoes      ←  cotacoes (check de conclusão), relatorios
   cotacoes        ←  relatorios
   relatorios      (importa tudo — única exceção intencional)
   ```

3. **Camada de serviço obrigatória** — lógica de negócio em `services.py`. Views são finas: validar, chamar serviço, retornar resposta.

4. **Transições de estado somente via métodos do model** — `req.submeter()`, `req.reprovar(motivo)`. Nunca `req.status = 'X'; req.save()` fora desses métodos.

5. **`select_for_update()` em toda transição de estado** — dentro de `transaction.atomic()`, retorna 409 em conflito. Previne race conditions de aprovação simultânea.

6. **`transaction.on_commit()` para todos os efeitos colaterais** — e-mail, audit log. Previne notificações fantasmas em caso de rollback.

7. **Django Groups como perfis** — migração de dados cria 5 Groups em `accounts`. `PermissionRequiredMixin` em todas as CBVs.

8. **`RegraDeAlcada` como model configurável via Admin** — alçadas editáveis pelo Admin sem deploy.

9. **HTMX via troca de template base** — uma view, um template, `{% extends base_template %}` onde `base_template` muda conforme `request.htmx`. URLs sempre servem página completa em navegação direta.

10. **`DecimalField(max_digits=12, decimal_places=2)` em todo campo monetário** — sem exceções, sem FloatField.

---

## Top Pitfalls (Priorizados)

### Críticos (causam rewrites ou corrupção de dados)

| # | Pitfall | Fase | Prevenção |
|---|--------|------|----------|
| C1 | Sem Custom User model antes da primeira migration | Fase 1 | `accounts.User(AbstractUser)` + `AUTH_USER_MODEL` antes de qualquer `migrate` |
| C2 | Race condition de aprovação sem lock de DB | Fase 2 | Toda transição: `transaction.atomic()` + `select_for_update()` + 409 em conflito |
| C3 | CNPJ armazenado não-normalizado / novo formato alfanumérico rejeitado | Fase 3 | `python-stdnum` validar + compactar na escrita; `unique=True` no campo compactado |
| C4 | Valores monetários BRL como FloatField | Fase 1 | `DecimalField(max_digits=12, decimal_places=2)` em todo lugar |

### Moderados (degradam UX ou bloqueiam features)

| # | Pitfall | Fase | Prevenção |
|---|--------|------|----------|
| M1 | Queries N+1 em list views | Fase 2 | `select_related` + `prefetch_related` em todos os querysets de lista; Debug Toolbar desde o dia 1 |
| M2 | CSRF 403 em todas as requisições HTMX POST | Fase 1 | `hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'` no `<body>` do `base.html` |
| M4 | Workflow de aprovação bypassado via endpoints desprotegidos | Fase 2 | Guard de pré-condição server-side em toda view que muda estado |
| M5 | E-mail indo para spam ou usando console backend em produção | Fase 2 | SES + verificação de domínio (SPF/DKIM); testar envio em todo deploy |
| M6 | Formulário de RFQ com fricção causa abandono pelo comprador | Fase 4 | Auto-save rascunho; linhas inline HTMX; `hx-preserve` em file inputs |
| M8 | Relatórios inúteis por dados nulos | Model na Fase 2 | `categoria` e `centro_de_custo` required (não-nullable) no model |

---

## Ordem de Build Recomendada

**Fase 1 — Foundation**
Scaffold do projeto, app `core` (modelos base abstratos), app `accounts` (User customizado + migration dos 5 Groups), login/logout, templates base com HTMX + CSRF configurados globalmente, Docker dev/prod com restart policy, extensões PostgreSQL (`pg_trgm`, `unaccent`), spec de variáveis de ambiente.
Gate: Custom User migrado, login funciona, requests HTMX incluem CSRF token.

**Fase 2 — Requisições e Workflow de Aprovação**
Model `Categoria` (em `fornecedores`), state machine `Requisicao`, views do Solicitante, models `RegraDeAlcada` + `AprovacaoRegistro`, filas de aprovação do Gestor/Diretor, serviço de roteamento, e-mail via `on_commit()` + SES.
Gate: Fluxo de aprovação end-to-end testável; e-mail chega em inbox real; todas as fronteiras de permissão enforçadas server-side.

**Fase 3 — Cadastro de Fornecedores**
Model `Fornecedor` com validação CNPJ (`python-stdnum`, alfanumérico pronto), M2M de categorias, views CRUD do Comprador, model `AvaliacaoFornecedor`, busca com trigram `pg_trgm`.
Gate: Fornecedores existem e são buscáveis; unicidade e normalização de CNPJ enforçadas.

**Fase 4 — RFQ e Gestão de Cotações**
Model `RFQ` (OneToOneField à `Requisicao` aprovada), `EntradaCotacao`, views do Comprador, adição/remoção de linhas inline via HTMX com auto-save, comparativo de preços (destaque menor preço, delta), seleção de vencedor com justificativa obrigatória.
Gate: Ciclo completo de procurement funciona end-to-end; comprador conclui RFQ sem reloads ou perda de dados.

**Fase 5 — Relatórios e Dashboard**
App `relatorios` (sem models), views de KPI do dashboard, relatório de gasto por categoria, painel de status de requisições, comparativo de cotações, exportação PDF via ReportLab Platypus com layout profissional.
Gate: Relatórios mostram dados precisos de transações reais das Fases 2-4; saída PDF aprovada pelo cliente.

---

## Perguntas em Aberto (Precisam de Input do Cliente)

| Pergunta | Necessária em | Risco se Adiada |
|---------|--------------|----------------|
| Valores das alçadas em BRL | Fase 2 | Baixo — `RegraDeAlcada` projetado para Admin configurar pós-deploy |
| Domínio de envio SES + acesso DNS para SPF/DKIM | Fase 2 (notificações) | **Bloqueante** — sem e-mail sem domínio verificado |
| EC2 vs ECS deployment final | Fase 1 (deployment) | Baixo para código; afeta Docker Compose vs ECS task definition |
| Centro de custo: lista fixa ou texto livre? | Fase 2 | Afeta o model — `CharField` vs FK para model configurável |
| Lista inicial de categorias de fornecedores | Fase 3 | Necessária para seed data; Admin pode adicionar mais pós-deploy |
| Range padrão dos relatórios: ano fiscal ou últimos 30 dias? | Fase 5 | Baixo — default configurável |
| Rating pós-RFQ: obrigatório no v1 ou estritamente v2? | Fase 4 | Model criado de qualquer forma; a pergunta é sobre o prompt de UI |
