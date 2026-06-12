# ComprasNexos

Sistema de gestão de compras para empresa de pequeno porte (até 20 usuários). Permite que solicitantes abram requisições de compra, gestores e diretores aprovem em dois níveis, compradores gerenciem cotações com fornecedores, e que a empresa tenha visibilidade total dos gastos por categoria.

**Stack:** Python 3.12 · Django 5.2 LTS · HTMX 2.0 · PostgreSQL 15 · Docker

---

## Funcionalidades por fase

### ✅ Fase 1 — Fundação
- Login com e-mail e senha
- Recuperação de senha por e-mail
- 5 perfis de usuário: Solicitante, Gestor, Comprador, Diretor, Admin
- Cadastro e gestão de unidades organizacionais
- Painel administrativo completo

### ✅ Fase 2 — Requisições & Aprovações
- Solicitante cria requisições de compra como rascunho e envia para aprovação
- "Copiar dados" de requisição anterior para agilizar preenchimento
- Gestor aprova ou reprova (1º nível) com fila filtrada pela própria unidade
- Diretor aprova ou reprova (2º nível) com visão de todas as unidades
- Alçadas de aprovação configuráveis por valor (sem deploy)
- E-mail automático ao Gestor quando nova requisição é submetida
- Histórico de auditoria completo por requisição
- Acompanhamento de status em tempo real

### ✅ Fase 3 — Fornecedores & Estoque
- Cadastro de fornecedores com validação de CNPJ (incluindo formato alfanumérico jul/2026)
- Busca fuzzy por nome (pg_trgm) e busca exata por CNPJ, com filtro por categoria
- Inativação/reativação de fornecedor sem perda de histórico
- Cadastro de itens de estoque por unidade organizacional com unidade de medida configurável
- Alertas visuais de quantidade abaixo do mínimo
- Atualização de quantidade inline via HTMX com proteção contra concorrência (select_for_update)
- Visão consolidada de estoque para Comprador/Admin

### ✅ Fase 4 — Cotações (RFQ)
- RFQ vinculado a requisição aprovada (OneToOne, unicidade no DB)
- Registro de propostas de múltiplos fornecedores com preço unitário, prazo e condições
- Comparativo automático de preços com destaque do menor preço e delta percentual
- Seleção de vencedor com justificativa obrigatória e imutabilidade pós-seleção
- Acesso restrito a Comprador e Admin via CompradorRequiredMixin

### ✅ Fase 5 — Relatórios & Dashboard
- Dashboard com KPIs reais: requisições abertas, cotações em andamento, gasto do mês e fornecedores ativos
- Relatório de gasto por categoria filtrável por período e unidade organizacional
- Painel de status de requisições com filtro por período e unidade
- Exportação em PDF de ambos os relatórios via ReportLab (layouts tabulares com cabeçalho e rodapé)
- Acesso restrito a `/relatorios/*`: Comprador, Diretor e Admin (Solicitante e Gestor não têm acesso)
- Dashboard acessível a todos os perfis autenticados

---

## Rodando localmente

### Pré-requisitos
- Docker e Docker Compose

### Subir o ambiente

```bash
git clone https://github.com/nuanderson/compras_nexos.git
cd compras_nexos
cp .env.example .env   # ajuste as variáveis se necessário
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

Acesse: [http://localhost:8002](http://localhost:8002)

### Rodar os testes

```bash
docker compose exec web python -m pytest
```

---

## Variáveis de ambiente

Crie um arquivo `.env` na raiz com as seguintes variáveis:

```env
DJANGO_SETTINGS_MODULE=config.settings.dev
SECRET_KEY=sua-chave-secreta-aqui
DB_NAME=compras_nexos
DB_USER=compras
DB_PASSWORD=dev_password
DB_HOST=db
DB_PORT=5432
DEFAULT_FROM_EMAIL=noreply@comprasnexos.com
```

---

## Estrutura do projeto

```
compras_nexos/
├── apps/
│   ├── accounts/        # Usuários, perfis, unidades organizacionais
│   ├── aprovacoes/      # Fluxo de aprovação, logs de auditoria, alçadas
│   ├── core/            # Dashboard com KPIs reais, models base (TimestampedModel, AuditedModel)
│   ├── cotacoes/        # RFQ: criar processo, cotações de fornecedores, comparativo, vencedor
│   ├── estoque/         # Itens de estoque por unidade, UnidadeMedida
│   ├── fornecedores/    # Cadastro de fornecedores com validação CNPJ
│   ├── relatorios/      # Relatórios de gastos e requisições, exportação PDF (ReportLab)
│   └── requisicoes/     # Requisições de compra
├── config/              # Settings (base, dev, prod), URLs, WSGI
├── static/              # CSS, HTMX vendorizado
├── templates/           # Base template e templates globais
├── docker-compose.yml
├── Dockerfile.dev
└── requirements.txt
```

---

## Progresso

| Fase | Descrição | Status |
|------|-----------|--------|
| 1 | Fundação | ✅ Completa |
| 2 | Requisições & Aprovações | ✅ Completa |
| 3 | Fornecedores & Estoque | ✅ Completa |
| 4 | Cotações (RFQ) | ✅ Completa |
| 5 | Relatórios & Dashboard | ✅ Completa |
