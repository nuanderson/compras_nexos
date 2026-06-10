# Fase 2: Requisições & Aprovações — Pesquisa

**Pesquisado:** 2026-06-10
**Domínio:** Django state machine, approval workflows, HTMX modals, transactional email
**Confiança Geral:** HIGH

---

<user_constraints>
## Restrições do Usuário (de CONTEXT.md)

### Decisões Travadas

- **D-01:** `CategoriaCompra` é um modelo separado e cadastrável via Admin — não enum hardcoded. Vive em `apps/requisicoes`.
- **D-02:** Volume inicial: ~3 categorias. Formulário de requisição usa `<select>` com categorias ativas.
- **D-03:** `CategoriaCompra` gerenciada via Django admin (`/admin/`). Painel HTMX dedicado: a cargo do planner.
- **D-04:** Roteamento do Gestor: todos os `User` com `role='gestor'` e `default_unit == requisicao.unidade`.
- **D-05:** Gestor vê apenas requisições da própria unidade (`default_unit`).
- **D-06:** Diretor e Admin veem requisições de todas as unidades.
- **D-07:** Ao entrar em `PENDENTE_GESTOR`, e-mail para **todos** os Gestores da unidade via `transaction.on_commit()` + django-anymail SES.
- **D-08:** `ConfiguracaoAlcada` com `valor_maximo_gestor: DecimalField(max_digits=12, decimal_places=2)`.
- **D-09:** `valor_estimado < valor_maximo_gestor` → só Gestor aprova → `APROVADO`. `valor_estimado >= valor_maximo_gestor` → Gestor + Diretor.
- **D-10:** Sem configuração ou `valor_maximo_gestor = None` → sempre 2 níveis (fail-safe).
- **D-11:** `ConfiguracaoAlcada` configurável pelo Admin/Diretor via Django admin ou view dedicada.
- **D-12:** Estado `RASCUNHO` existe. Criação salva como rascunho. Solicitante envia explicitamente ("Enviar para aprovação").
- **D-13:** Reprovação é permanente — estado terminal, sem reenvio.
- **D-14:** Feature "copiar dados" ao criar nova requisição — pré-preenche campos via HTMX a partir de requisição existente.
- **D-15:** Solicitante cancela em `RASCUNHO` ou `PENDENTE_GESTOR` apenas.
- **D-16:** Único e-mail de v1: notificação aos Gestores quando entra em `PENDENTE_GESTOR`.
- **D-17:** Notificação ao Solicitante sobre aprovação/reprovação está **fora do escopo v1**.
- **D-18:** `transaction.on_commit()` — sem Celery.
- **D-19:** Dois apps Django novos: `apps/requisicoes` e `apps/aprovacoes`.

**Máquina de estados:**
```
RASCUNHO
  ├─→ PENDENTE_GESTOR   [Solicitante envia]
  └─→ CANCELADO          [Solicitante cancela]

PENDENTE_GESTOR
  ├─→ CANCELADO          [Solicitante cancela]
  ├─→ REPROVADO          [Gestor reprova — motivo obrigatório]
  ├─→ APROVADO           [Gestor aprova + valor < alçada]
  └─→ PENDENTE_DIRETOR   [Gestor aprova + valor ≥ alçada]

PENDENTE_DIRETOR
  ├─→ APROVADO           [Diretor aprova]
  └─→ REPROVADO          [Diretor reprova — motivo obrigatório]

Terminais: APROVADO | REPROVADO | CANCELADO
```

### Áreas de Discrição do Claude

- Estrutura exata de URLs e nomes de views em `apps/requisicoes` e `apps/aprovacoes`.
- Se `CategoriaCompra` e `ConfiguracaoAlcada` usam o Django admin nativo ou view HTMX dedicada.
- Estrutura de templates e partials para a fila do Gestor e detalhe da requisição.
- Estratégia de paginação para listas de requisições.

### Ideias Adiadas (FORA DO ESCOPO)

- Notificação ao Solicitante por e-mail em aprovação/reprovação (v2, `NOTF-01`).
- Histórico de versões de rascunho.
- Múltiplas configurações de alçada por categoria.
- Delegação de aprovação (férias/ausência).
</user_constraints>

---

<phase_requirements>
## Requisitos da Fase

| ID | Descrição | Suporte da Pesquisa |
|----|-----------|---------------------|
| REQ-01 | Solicitante abre requisição com: descrição, categoria, valor estimado, justificativa e unidade | Padrão `ModelForm` + `AuditedModel` herança; `CategoriaCompra` como FK |
| REQ-02 | Solicitante acompanha status em tempo real | Badge de status via HTMX polling (Pattern 2 de CLAUDE.md); `AprovacaoLog` visível na tela de detalhe |
| REQ-03 | Sistema registra histórico de aprovações (ator, timestamp, motivo) | Modelo `AprovacaoLog` com FK para `Requisicao` e `User`; herda `TimestampedModel` |
| REQ-04 | Sistema envia e-mail ao Gestor quando nova requisição é criada | `transaction.on_commit()` + django-anymail; roteamento via `User.default_unit` |
| APROV-01 | Gestor visualiza fila de requisições aguardando seu parecer | View filtrada por `requisicao.unidade == request.user.default_unit` e `status=PENDENTE_GESTOR` |
| APROV-02 | Gestor aprova ou reprova requisição (1º nível) | `apps/aprovacoes/services.py` com `select_for_update()` + `transaction.atomic()` |
| APROV-03 | Diretor visualiza fila de requisições aguardando seu parecer | View sem filtro de unidade; filtra `status=PENDENTE_DIRETOR` |
| APROV-04 | Diretor aprova ou reprova requisição (2º nível) | Mesma camada de serviço, transição diferente na FSM |
| APROV-05 | Reprovação exige motivo obrigatório em qualquer nível | Campo `motivo` obrigatório em `AprovacaoForm`; validação no form e no service |
| APROV-06 | Admin configura alçadas por valor via painel sem deploy | Modelo `ConfiguracaoAlcada` singleton; registrado no Django admin; lido por `services.py` |
</phase_requirements>

---

## Sumário

A Fase 2 introduz o núcleo de negócio do ComprasNexos: o ciclo de vida completo de uma requisição de compra com aprovação em dois níveis. O desafio técnico central é a **máquina de estados concorrente** — múltiplos Gestores podem visualizar a mesma requisição simultaneamente, e a transição de estado deve ser atômica. O padrão `select_for_update()` + `transaction.atomic()` já está documentado em `STATE.md` como constraint arquitetural e é a abordagem correta.

O segundo desafio é o **roteamento de visibilidade**: Gestores veem somente requisições da sua `default_unit`, enquanto Diretores e Admins veem tudo. Isso afeta queries em três lugares — fila do Gestor, fila do Diretor e listagem do Solicitante. O modelo de `User` existente (`apps/accounts/models.py`) já tem `role` e `default_unit` como FK, então o roteamento é uma query simples `filter(unidade=request.user.default_unit)`.

O terceiro desafio é a **lógica de alçada configurável**: a decisão de encaminhar para o Diretor ou finalizar em APROVADO após o Gestor aprovar depende de `ConfiguracaoAlcada.valor_maximo_gestor`. Essa leitura precisa ser cacheada ou pelo menos eficiente (uma linha na tabela, sempre via `get_or_create`).

**Recomendação principal:** Implementar a FSM como métodos no modelo `Requisicao` (`submeter()`, `aprovar_gestor()`, `reprovar(motivo)`, `cancelar()`), delegados por `apps/aprovacoes/services.py`. O service cria o `AprovacaoLog` e dispara o e-mail via `on_commit`. As views apenas chamam o service e retornam a resposta HTMX adequada.

---

## Mapa de Responsabilidade Arquitetural

| Capacidade | Camada Primária | Camada Secundária | Racional |
|------------|----------------|------------------|---------|
| Formulário de requisição | Frontend (Django template + HTMX) | Backend (forms.py) | Entrada de dados pelo Solicitante; validação no servidor |
| Máquina de estados | Backend (`apps/aprovacoes/services.py`) | Modelo (`Requisicao` methods) | Lógica de transição é negócio puro — nunca no template |
| Auditoria de aprovações | Backend (`AprovacaoLog` model) | — | Persistência imutável; nenhuma view altera logs existentes |
| Fila do Gestor (filtragem) | Backend (queryset no `get_queryset`) | — | Dados sensíveis de negócio não devem vazar ao cliente |
| Roteamento de e-mail | Backend (`services.py` + `on_commit`) | Email backend (anymail) | Efeito colateral transacional — só após commit |
| Badge de status | Frontend (HTMX polling ou `hx-trigger`) | Backend (view de partial) | Estado visível ao Solicitante; backend retorna o fragment |
| Configuração de alçada | Backend (`ConfiguracaoAlcada`) + Django Admin | — | Configurável sem deploy; lida no service de aprovação |
| "Copiar dados" de requisição | Frontend (HTMX `hx-get` de partial) | Backend (view que retorna JSON/form partial) | Enriquecimento de formulário sem page reload |

---

## Stack Padrão

### Core (todos já em requirements.txt ou mandatórios por CLAUDE.md)

| Biblioteca | Versão | Propósito | Por Que é Padrão |
|-----------|--------|-----------|-----------------|
| Django | 5.2.* LTS | Framework, ORM, admin | Mandatório pelo cliente [VERIFIED: CLAUDE.md] |
| django-htmx | 1.x | `request.htmx` + `HtmxMiddleware` | Já instalado; necessário para partial responses [VERIFIED: CLAUDE.md] |
| django-anymail | latest | SES/SMTP backend para e-mail | Já em requirements.txt [VERIFIED: requirements.txt] |
| psycopg2-binary | 2.9.* | Adaptador PostgreSQL | Já instalado [VERIFIED: requirements.txt] |
| `django.contrib.postgres` | (embutido no Django) | `TrigramExtension`, JSON fields | Já em `INSTALLED_APPS` [VERIFIED: config/settings/base.py] |

### Nenhum Pacote Novo Necessário

A Fase 2 não adiciona dependências Python ao projeto. Toda a lógica necessária (ORM, admin, formulários, e-mail, HTMX) já está disponível na stack instalada.

**Verificação:**
- `django-anymail` para e-mail transacional: `pip3 show django-anymail` retorna versão 15.0 [VERIFIED: ambiente]
- `django-htmx` 1.27.0 instalado [VERIFIED: ambiente]
- Django `select_for_update()` e `transaction.atomic()` são APIs nativas do Django ORM [VERIFIED: CLAUDE.md + STATE.md]

---

## Auditoria de Legitimidade de Pacotes

Nenhum pacote externo novo é introduzido nesta fase. Todos os pacotes utilizados já estão em `requirements.txt` e foram validados na Fase 1. Auditoria de legitimidade não aplicável.

---

## Padrões de Arquitetura

### Diagrama de Fluxo do Sistema

```
Solicitante (Browser)
        │
        │  POST /requisicoes/nova/
        ▼
  requisicoes/views.py
    RequisicaoCreateView
        │
        │  services.criar_requisicao(data, user)
        ▼
  aprovacoes/services.py
    criar_requisicao()
        │
        ├─► Cria Requisicao (status=RASCUNHO)
        └─► Retorna objeto

        │
        │  POST /requisicoes/<pk>/enviar/
        ▼
  aprovacoes/services.py
    submeter_requisicao()
        │
        ├─► SELECT FOR UPDATE → Requisicao
        ├─► req.status = PENDENTE_GESTOR
        ├─► req.save()
        ├─► AprovacaoLog.create(evento='ENVIO', ...)
        └─► transaction.on_commit → enviar_email_gestores()
                                          │
                                          ▼
                                   django-anymail → AWS SES
                                   (para todos os Gestores da unidade)

Gestor (Browser)
        │
        │  GET /aprovacoes/fila/
        ▼
  aprovacoes/views.py
    FilaGestorView
    .get_queryset() → Requisicao.objects.filter(
                        status='PENDENTE_GESTOR',
                        unidade=request.user.default_unit
                      )
        │
        │  POST /aprovacoes/<pk>/aprovar/ (via HTMX modal)
        ▼
  aprovacoes/services.py
    aprovar_gestor()
        │
        ├─► SELECT FOR UPDATE → Requisicao
        ├─► Lê ConfiguracaoAlcada (singleton)
        ├─► Se valor < threshold → status = APROVADO
        ├─► Se valor >= threshold → status = PENDENTE_DIRETOR
        ├─► AprovacaoLog.create(evento='APROVACAO_GESTOR', ...)
        └─► Retorna requisicao atualizada

        │
        │  POST /aprovacoes/<pk>/reprovar/ (via HTMX modal)
        ▼
  aprovacoes/services.py
    reprovar_requisicao()
        │
        ├─► SELECT FOR UPDATE → Requisicao
        ├─► Valida: motivo obrigatório
        ├─► status = REPROVADO
        ├─► AprovacaoLog.create(evento='REPROVACAO', motivo=motivo, ...)
        └─► Retorna requisicao atualizada

Diretor (Browser)
        │  (fluxo idêntico ao Gestor, mas filtra PENDENTE_DIRETOR, sem filtro de unidade)
        ▼
  aprovacoes/services.py
    aprovar_diretor() / reprovar_requisicao()
```

### Estrutura de Projeto Recomendada

```
apps/
├── requisicoes/
│   ├── __init__.py
│   ├── apps.py
│   ├── admin.py           # CategoriaCompra no Django admin
│   ├── forms.py           # RequisicaoForm (criar/editar rascunho)
│   ├── models.py          # CategoriaCompra, Requisicao
│   ├── urls.py
│   ├── views.py           # Views do Solicitante
│   ├── migrations/
│   └── templates/
│       └── requisicoes/
│           ├── requisicao_list.html      # Lista do Solicitante
│           ├── requisicao_form.html      # Criar/Editar rascunho
│           ├── requisicao_detail.html    # Detalhe + histórico
│           └── partials/
│               ├── requisicao_row.html   # Linha de tabela (HTMX swap)
│               ├── status_badge.html     # Badge de status (HTMX polling)
│               ├── historico.html        # Log de aprovações
│               └── copiar_dados.html     # Partial pré-preenchimento
│
├── aprovacoes/
│   ├── __init__.py
│   ├── apps.py
│   ├── admin.py           # ConfiguracaoAlcada no Django admin
│   ├── forms.py           # AprovacaoForm (motivo), ReprovaForm
│   ├── models.py          # AprovacaoLog, ConfiguracaoAlcada
│   ├── services.py        # TODA lógica de transição de estado
│   ├── urls.py
│   ├── views.py           # FilaGestor, FilaDiretor, ações de aprovação
│   ├── migrations/
│   └── templates/
│       └── aprovacoes/
│           ├── fila_gestor.html
│           ├── fila_diretor.html
│           └── partials/
│               ├── modal_aprovar.html    # Modal HTMX
│               ├── modal_reprovar.html   # Modal HTMX com campo motivo
│               └── fila_row.html         # Linha de tabela após swap
```

---

### Padrão 1: Modelo Requisicao com FSM via Métodos

**O que é:** A lógica de transição de estado fica em métodos do modelo. O service orquestra a chamada atômica.

**Quando usar:** Sempre que uma transição precisa de validação de estado anterior + efeito colateral (log + email).

```python
# apps/requisicoes/models.py
# Source: STATE.md arquitetural constraint + Django docs on model methods [ASSUMED]

class Requisicao(AuditedModel):
    class Status(models.TextChoices):
        RASCUNHO          = 'RASCUNHO',          'Rascunho'
        PENDENTE_GESTOR   = 'PENDENTE_GESTOR',   'Aguardando Gestor'
        PENDENTE_DIRETOR  = 'PENDENTE_DIRETOR',  'Aguardando Diretor'
        APROVADO          = 'APROVADO',          'Aprovado'
        REPROVADO         = 'REPROVADO',         'Reprovado'
        CANCELADO         = 'CANCELADO',         'Cancelado'

    ESTADOS_TERMINAIS = {Status.APROVADO, Status.REPROVADO, Status.CANCELADO}
    CANCELA_PERMISSOES = {Status.RASCUNHO, Status.PENDENTE_GESTOR}

    descricao      = models.TextField()
    categoria      = models.ForeignKey('CategoriaCompra', on_delete=models.PROTECT)
    valor_estimado = models.DecimalField(max_digits=12, decimal_places=2)
    justificativa  = models.TextField()
    unidade        = models.ForeignKey(
        'accounts.UnidadeOrganizacional', on_delete=models.PROTECT
    )
    status         = models.CharField(
        max_length=20, choices=Status.choices, default=Status.RASCUNHO
    )

    class Meta:
        verbose_name = 'Requisição de Compra'
        verbose_name_plural = 'Requisições de Compra'
        ordering = ['-criado_em']

    def pode_submeter(self):
        return self.status == self.Status.RASCUNHO

    def pode_cancelar(self):
        return self.status in self.CANCELA_PERMISSOES

    def pode_gestor_agir(self):
        return self.status == self.Status.PENDENTE_GESTOR

    def pode_diretor_agir(self):
        return self.status == self.Status.PENDENTE_DIRETOR
```

---

### Padrão 2: Service Layer com select_for_update + atomic

**O que é:** Toda transição de estado ocorre dentro de `transaction.atomic()` com `select_for_update()` para prevenir race conditions.

**Quando usar:** Sempre. Nenhuma transição de estado acontece fora do service.

```python
# apps/aprovacoes/services.py
# Source: STATE.md arquitetural constraint [VERIFIED: STATE.md]
# + Django docs select_for_update [CITED: https://docs.djangoproject.com/en/5.2/ref/models/querysets/#select-for-update]

from django.db import transaction
from django.http import Http404
from apps.requisicoes.models import Requisicao
from .models import AprovacaoLog, ConfiguracaoAlcada


def submeter_requisicao(requisicao_pk: int, solicitante) -> Requisicao:
    """Transição RASCUNHO → PENDENTE_GESTOR."""
    with transaction.atomic():
        req = Requisicao.objects.select_for_update().get(pk=requisicao_pk)
        if not req.pode_submeter():
            raise ValueError(f"Requisição em estado '{req.status}' não pode ser submetida.")
        if req.criado_por != solicitante:
            raise PermissionError("Apenas o Solicitante pode enviar esta requisição.")
        req.status = Requisicao.Status.PENDENTE_GESTOR
        req.save(update_fields=['status', 'atualizado_em'])
        AprovacaoLog.objects.create(
            requisicao=req,
            aprovador=solicitante,
            evento=AprovacaoLog.Evento.ENVIO,
        )
        transaction.on_commit(lambda: _notificar_gestores(req.pk))
    return req


def aprovar_gestor(requisicao_pk: int, gestor) -> Requisicao:
    """Transição PENDENTE_GESTOR → APROVADO ou PENDENTE_DIRETOR."""
    with transaction.atomic():
        req = Requisicao.objects.select_for_update().get(pk=requisicao_pk)
        if not req.pode_gestor_agir():
            raise ValueError(f"Estado '{req.status}' não aceita ação de Gestor.")
        config = ConfiguracaoAlcada.obter()
        if config.requer_diretor(req.valor_estimado):
            req.status = Requisicao.Status.PENDENTE_DIRETOR
            evento = AprovacaoLog.Evento.APROVACAO_GESTOR
        else:
            req.status = Requisicao.Status.APROVADO
            evento = AprovacaoLog.Evento.APROVACAO_FINAL
        req.save(update_fields=['status', 'atualizado_em'])
        AprovacaoLog.objects.create(requisicao=req, aprovador=gestor, evento=evento)
    return req


def reprovar_requisicao(requisicao_pk: int, aprovador, motivo: str) -> Requisicao:
    """Transição para REPROVADO — terminal. Motivo obrigatório."""
    if not motivo or not motivo.strip():
        raise ValueError("Motivo é obrigatório para reprovação.")
    with transaction.atomic():
        req = Requisicao.objects.select_for_update().get(pk=requisicao_pk)
        if req.status not in (
            Requisicao.Status.PENDENTE_GESTOR,
            Requisicao.Status.PENDENTE_DIRETOR,
        ):
            raise ValueError(f"Estado '{req.status}' não permite reprovação.")
        req.status = Requisicao.Status.REPROVADO
        req.save(update_fields=['status', 'atualizado_em'])
        AprovacaoLog.objects.create(
            requisicao=req,
            aprovador=aprovador,
            evento=AprovacaoLog.Evento.REPROVACAO,
            motivo=motivo,
        )
    return req


def cancelar_requisicao(requisicao_pk: int, solicitante) -> Requisicao:
    """Transição para CANCELADO (apenas RASCUNHO ou PENDENTE_GESTOR)."""
    with transaction.atomic():
        req = Requisicao.objects.select_for_update().get(pk=requisicao_pk)
        if not req.pode_cancelar():
            raise ValueError(f"Requisição em estado '{req.status}' não pode ser cancelada.")
        if req.criado_por != solicitante:
            raise PermissionError("Apenas o Solicitante pode cancelar.")
        req.status = Requisicao.Status.CANCELADO
        req.save(update_fields=['status', 'atualizado_em'])
        AprovacaoLog.objects.create(
            requisicao=req,
            aprovador=solicitante,
            evento=AprovacaoLog.Evento.CANCELAMENTO,
        )
    return req
```

---

### Padrão 3: ConfiguracaoAlcada Singleton

**O que é:** Uma única linha na tabela `aprovacoes_configuracaoalcada`. Acessada via método de classe.

**Por que singleton:** A decisão de negócio é "um threshold global para toda a empresa". Se a tabela estiver vazia, aplica fail-safe (sempre 2 níveis, D-10).

```python
# apps/aprovacoes/models.py
# Source: D-08, D-09, D-10 de CONTEXT.md [VERIFIED: 02-CONTEXT.md]

class ConfiguracaoAlcada(models.Model):
    valor_maximo_gestor = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=(
            "Valor máximo para aprovação apenas pelo Gestor (R$). "
            "Acima deste valor, exige aprovação do Diretor também. "
            "Deixe em branco para sempre exigir 2 níveis (comportamento seguro)."
        ),
    )

    class Meta:
        verbose_name = 'Configuração de Alçada'
        verbose_name_plural = 'Configuração de Alçada'

    @classmethod
    def obter(cls) -> 'ConfiguracaoAlcada':
        """Retorna a configuração singleton. Cria uma nova se não existir."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def requer_diretor(self, valor: Decimal) -> bool:
        """True se valor requer aprovação do Diretor (2 níveis)."""
        if self.valor_maximo_gestor is None:
            return True  # fail-safe: sempre 2 níveis
        return valor >= self.valor_maximo_gestor
```

---

### Padrão 4: E-mail via transaction.on_commit

**O que é:** O e-mail é enfileirado para disparo apenas após o `commit` bem-sucedido. Garante consistência — se a transação rolar back, nenhum e-mail é enviado.

```python
# apps/aprovacoes/services.py (continuação)
# Source: CLAUDE.md §Email Notifications [VERIFIED: CLAUDE.md]
# + Django docs on_commit [CITED: https://docs.djangoproject.com/en/5.2/topics/db/transactions/#performing-actions-after-commit]

from django.core.mail import send_mail
from apps.accounts.models import User

def _notificar_gestores(requisicao_pk: int) -> None:
    """
    Chamado via transaction.on_commit após commit bem-sucedido.
    Envia e-mail para todos os Gestores da unidade da requisição.
    """
    from apps.requisicoes.models import Requisicao
    try:
        req = Requisicao.objects.select_related('unidade', 'criado_por').get(pk=requisicao_pk)
    except Requisicao.DoesNotExist:
        return

    gestores = User.objects.filter(
        role=User.Role.GESTOR,
        default_unit=req.unidade,
        is_active=True,
    )
    destinatarios = list(gestores.values_list('email', flat=True))
    if not destinatarios:
        return  # sem Gestores na unidade — falha silenciosa, log pode ser adicionado

    send_mail(
        subject=f'[ComprasNexos] Nova requisição aguardando aprovação — {req.descricao[:50]}',
        message=(
            f'Olá,\n\n'
            f'Uma nova requisição de compra foi enviada para aprovação:\n\n'
            f'Solicitante: {req.criado_por.get_full_name() or req.criado_por.email}\n'
            f'Unidade: {req.unidade.nome}\n'
            f'Descrição: {req.descricao}\n'
            f'Valor Estimado: R$ {req.valor_estimado:,.2f}\n\n'
            f'Acesse o sistema para aprovar ou reprovar.\n'
        ),
        from_email=None,  # usa DEFAULT_FROM_EMAIL do settings
        recipient_list=destinatarios,
        fail_silently=True,  # evita 500 se SES não estiver configurado em dev
    )
```

---

### Padrão 5: Mixins de Permissão por Role

**O que é:** Replicar `AdminRequiredMixin` (já existente) para `GestorRequiredMixin` e `DiretorRequiredMixin`.

```python
# apps/aprovacoes/views.py
# Source: apps/accounts/views.py AdminRequiredMixin [VERIFIED: apps/accounts/views.py]

from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import LoginRequiredMixin


class GestorRequiredMixin(LoginRequiredMixin):
    """Restringe acesso a usuários com role='gestor' ou 'admin'."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role not in ('gestor', 'admin') and not request.user.is_superuser:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class DiretorRequiredMixin(LoginRequiredMixin):
    """Restringe acesso a usuários com role='diretor' ou 'admin'."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role not in ('diretor', 'admin') and not request.user.is_superuser:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
```

---

### Padrão 6: Modal de Aprovação/Reprovação HTMX (Pattern 3 de CLAUDE.md)

**O que é:** Ao clicar "Aprovar" ou "Reprovar", o HTMX carrega o formulário do modal sem page reload. O POST retorna a linha da fila atualizada.

```html
<!-- Botão na fila que carrega o modal -->
<!-- Source: CLAUDE.md §HTMX Patterns Pattern 3 [VERIFIED: CLAUDE.md] -->
<td>
  <button
    hx-get="{% url 'aprovacoes:modal-reprovar' req.pk %}"
    hx-target="#modal-container"
    hx-swap="innerHTML"
    class="btn btn-destructive btn-sm">
    Reprovar
  </button>
  <button
    hx-post="{% url 'aprovacoes:aprovar' req.pk %}"
    hx-target="#fila-row-{{ req.pk }}"
    hx-swap="outerHTML"
    class="btn btn-primary btn-sm">
    Aprovar
  </button>
</td>

<!-- Modal de reprovação (partial) -->
<!-- Modal container no template base da fila -->
<div id="modal-container"></div>

<!-- Dentro do partial modal_reprovar.html -->
<form
  hx-post="{% url 'aprovacoes:reprovar' req.pk %}"
  hx-target="#fila-row-{{ req.pk }}"
  hx-swap="outerHTML"
  hx-on::after-request="document.getElementById('modal-container').innerHTML=''">
  {% csrf_token %}
  <div class="form-group">
    <label class="form-label">Motivo da Reprovação *</label>
    <textarea name="motivo" class="form-input" rows="3" required
              placeholder="Descreva o motivo da reprovação..."></textarea>
    <span class="form-error" id="motivo-error"></span>
  </div>
  <div class="form-actions">
    <button type="button"
            onclick="document.getElementById('modal-container').innerHTML=''"
            class="btn btn-secondary">Cancelar</button>
    <button type="submit" class="btn btn-destructive">Confirmar Reprovação</button>
  </div>
</form>
```

---

### Padrão 7: "Copiar dados" via HTMX (D-14)

**O que é:** No formulário de nova requisição, um select permite escolher uma requisição existente do próprio Solicitante. Ao selecionar, HTMX preenche os campos via partial.

```html
<!-- No formulário de nova requisição -->
<!-- Source: D-14 de CONTEXT.md + CLAUDE.md Pattern 4 [VERIFIED: 02-CONTEXT.md] -->
<div class="form-group">
  <label class="form-label">Copiar dados de requisição anterior (opcional)</label>
  <select
    hx-get="{% url 'requisicoes:copiar-dados' %}"
    hx-trigger="change"
    hx-target="#campos-requisicao"
    hx-include="[name='requisicao_origem']"
    name="requisicao_origem"
    class="form-select">
    <option value="">— Nenhuma —</option>
    {% for r in requisicoes_anteriores %}
    <option value="{{ r.pk }}">{{ r.descricao|truncatechars:60 }} ({{ r.criado_em|date:"d/m/Y" }})</option>
    {% endfor %}
  </select>
</div>

<div id="campos-requisicao">
  <!-- campos preenchidos pelo partial ou formulário normal -->
  {% include "requisicoes/partials/campos_requisicao.html" with form=form %}
</div>
```

---

### Anti-Padrões a Evitar

- **Lógica de transição de estado na view:** A view nunca deve mudar `requisicao.status` diretamente. Sempre delegar ao `services.py`.
- **Criar `AprovacaoLog` fora de `transaction.atomic()`:** O log e a transição de status devem estar na mesma transação. Se um falha, o outro reverte.
- **Disparar e-mail dentro da `transaction.atomic()`:** `send_mail()` dentro do bloco atômico pode ser enviado mesmo se a transação rolar back. Usar `transaction.on_commit()`.
- **`ConfiguracaoAlcada.objects.get(pk=1)` sem `get_or_create`:** Se a linha não existir, levanta `DoesNotExist`. Usar o método `obter()` que garante `get_or_create`.
- **Gestor vendo requisições de outras unidades:** O queryset da `FilaGestorView` DEVE filtrar por `unidade=request.user.default_unit`. Omitir este filtro é uma falha de controle de acesso.
- **Diretor agindo em `PENDENTE_GESTOR`:** As views do Diretor devem filtrar por `status=PENDENTE_DIRETOR` e verificar o status antes de permitir ação.
- **Race condition sem `select_for_update`:** Dois Gestores clicando "Aprovar" simultaneamente sem lock podem criar dois `AprovacaoLog` e transicionar o estado duas vezes. `select_for_update()` previne isso.
- **Reprovação sem motivo aceita pelo form:** O campo `motivo` deve ter `required=True` tanto no form HTML quanto na validação do service (defense in depth).

---

## Nunca Construir Manualmente

| Problema | Não Construir | Usar Em Vez Disso | Por Quê |
|----------|--------------|-------------------|---------|
| Concorrência em transições | Lock manual com flags no banco | `select_for_update()` + `transaction.atomic()` | Django ORM já expõe `SELECT FOR UPDATE` corretamente; implementação manual esquece edge cases (savepoints, nowait) |
| Fila de e-mail | Thread ou subprocess | `transaction.on_commit()` | Garante que e-mail só sai após commit; sem infra extra |
| Singleton de config | Tabela com chave de texto | `get_or_create(pk=1)` | Simples, idiomático em Django; auditável no admin |
| Validação de campos monetários | Parse manual de string | `DecimalField` nativo do Django | Aritmética de ponto flutuante é imprecisa para dinheiro; `DecimalField` usa `Decimal` do Python |
| Controle de acesso por role | Checa `request.user.role` em cada view | `GestorRequiredMixin` (replicar `AdminRequiredMixin`) | Centralizado, testável, não esquece em nenhuma view |

**Insight-chave:** O Django ORM com `select_for_update()` é suficiente para o volume de 20 usuários. Redis/Celery/FSM libs externas adicionam infraestrutura sem benefício real nessa escala.

---

## Armadilhas Comuns

### Armadilha 1: select_for_update requer transação ativa

**O que vai errado:** `Requisicao.objects.select_for_update().get(pk=pk)` fora de `with transaction.atomic():` levanta `TransactionManagementError` em PostgreSQL com `AUTOCOMMIT=True`.

**Por que acontece:** `select_for_update()` requer que exista uma transação em andamento. O Django por padrão opera em auto-commit fora de blocos atômicos.

**Como evitar:** Sempre envolver `select_for_update()` dentro de `with transaction.atomic():`. Nunca chamar `select_for_update()` diretamente na view.

**Sinais de alerta:** `django.db.transaction.TransactionManagementError: An error occurred in the current transaction.`

---

### Armadilha 2: HTMX POST sem CSRF token em partials injetados

**O que vai errado:** Modal de reprovação retorna 403 CSRF Failed quando submetido.

**Por que acontece:** O handler `htmx:configRequest` em `base.html` lê `<meta name="csrf-token">` do DOM. O partial do modal é injetado via HTMX e não carrega sua própria `<meta>` tag. Se o handler foi registrado antes do partial ser injetado, funciona — mas é frágil. Se o partial tiver um botão com `hx-post` sem `csrf_token` no form, a requisição falha.

**Como evitar:** Adicionar `{% csrf_token %}` em todo `<form>` no partial, **e** garantir que a tag `<meta name="csrf-token">` está presente no `base.html` (já está em `templates/base.html:6`). O padrão já verificado em `01-REVIEW.md` (CR-04) — seguir o mesmo padrão: `{% csrf_token %}` em cada form de partial.

**Sinais de alerta:** HTTP 403 em HTMX POST; mensagem `CSRF verification failed` no log.

---

### Armadilha 3: Gestor sem default_unit vê todas as requisições (falha de controle de acesso)

**O que vai errado:** Um Gestor com `default_unit=None` (possível se não foi configurado) recebe um queryset sem filtro de unidade, vendo requisições de toda a empresa.

**Por que acontece:** `Requisicao.objects.filter(unidade=request.user.default_unit)` com `default_unit=None` se torna `filter(unidade=None)`, que retorna zero registros — mas se o código usar `filter(unidade__in=[request.user.default_unit])`, comportamento pode variar.

**Como evitar:** Na `FilaGestorView.get_queryset()`, checar explicitamente: `if not request.user.default_unit: return Requisicao.objects.none()`. Previne vazamento de dados e facilita diagnóstico.

**Sinais de alerta:** Gestor vendo requisições que não são da sua unidade; lista de fila inesperadamente vazia quando não deveria.

---

### Armadilha 4: Transição de estado 409 sem feedback ao usuário

**O que vai errado:** Dois Gestores clicam "Aprovar" simultaneamente. Um vence o lock. O outro recebe `ValueError("Estado 'APROVADO' não aceita ação de Gestor.")` e a view retorna 500.

**Por que acontece:** O service levanta `ValueError` mas a view não trata. Em HTMX, um 500 é difícil de diagnosticar pelo usuário.

**Como evitar:** A view deve capturar `ValueError` do service e retornar HTTP 409 com uma mensagem amigável em pt-BR, ou redirecionar para a fila com mensagem de aviso. Para HTMX, retornar um partial de erro com `HX-Reswap: none` ou atualizar o elemento com mensagem.

**Sinais de alerta:** Usuário clica no botão e a UI congela ou mostra erro genérico.

---

### Armadilha 5: Campo motivo vazio aceito em reprovação

**O que vai errado:** O motivo de reprovação é submetido vazio (ataque direto ao endpoint, bypassando o `required` HTML).

**Por que acontece:** O `required` HTML só é validado pelo browser — curl ou qualquer cliente HTTP pode omitir o campo. A validação no service é a defesa real.

**Como evitar:** O service `reprovar_requisicao()` deve validar `if not motivo or not motivo.strip(): raise ValueError(...)` **antes** do `transaction.atomic()`. O form também valida para UX.

---

### Armadilha 6: ConfiguracaoAlcada inexistente em ambiente novo

**O que vai errado:** Primeiro deploy em ambiente limpo — tabela vazia. `ConfiguracaoAlcada.objects.get(pk=1)` levanta `DoesNotExist`, causando 500 no primeiro fluxo de aprovação.

**Por que acontece:** Nenhuma fixture ou migration cria a linha inicial.

**Como evitar:** Usar o método `obter()` com `get_or_create`. O comportamento default (sem configuração) é correto pelo D-10: sempre 2 níveis. Não é necessário uma fixture — `get_or_create` lida com isso.

---

### Armadilha 7: Modelo AprovacaoLog permite registros duplicados para mesma transição

**O que vai errado:** Uma requisição em `PENDENTE_GESTOR` recebe dois logs de aprovação de Gestores diferentes (ambos clicaram "Aprovar" antes do lock bloquear o segundo).

**Por que acontece:** `select_for_update()` bloqueia o segundo Gestor até o primeiro commit. Após o commit, o status já é `APROVADO` e o service levanta `ValueError`. Isso é o comportamento **correto** — a armadilha é não tratar esse `ValueError` na view adequadamente.

**Como evitar:** Confirmar que o service verifica o estado **depois** de adquirir o lock (o código do Padrão 2 acima faz isso corretamente).

---

## Exemplos de Código

### Modelo AprovacaoLog

```python
# apps/aprovacoes/models.py
# Source: D-19 de CONTEXT.md + apps/core/models.py TimestampedModel [VERIFIED: ambos]

from django.conf import settings
from django.db import models
from apps.core.models import TimestampedModel


class AprovacaoLog(TimestampedModel):
    class Evento(models.TextChoices):
        ENVIO             = 'ENVIO',             'Envio para Aprovação'
        APROVACAO_GESTOR  = 'APROVACAO_GESTOR',  'Aprovação pelo Gestor'
        APROVACAO_FINAL   = 'APROVACAO_FINAL',   'Aprovação Final'
        REPROVACAO        = 'REPROVACAO',        'Reprovação'
        CANCELAMENTO      = 'CANCELAMENTO',      'Cancelamento'

    requisicao = models.ForeignKey(
        'requisicoes.Requisicao',
        on_delete=models.CASCADE,
        related_name='logs',
    )
    aprovador  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name='aprovacoes_realizadas',
    )
    evento     = models.CharField(max_length=20, choices=Evento.choices)
    motivo     = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'Log de Aprovação'
        verbose_name_plural = 'Logs de Aprovação'
        ordering = ['criado_em']
```

---

### FilaGestorView com Filtro de Unidade

```python
# apps/aprovacoes/views.py
# Source: D-04, D-05 de CONTEXT.md [VERIFIED: 02-CONTEXT.md]

from django.views.generic import ListView
from apps.requisicoes.models import Requisicao


class FilaGestorView(GestorRequiredMixin, ListView):
    template_name = 'aprovacoes/fila_gestor.html'
    context_object_name = 'requisicoes'

    def get_queryset(self):
        # D-05: Gestor vê APENAS requisições da própria unidade
        if not self.request.user.default_unit:
            return Requisicao.objects.none()
        return (
            Requisicao.objects
            .filter(
                status=Requisicao.Status.PENDENTE_GESTOR,
                unidade=self.request.user.default_unit,
            )
            .select_related('criado_por', 'categoria', 'unidade')
            .order_by('criado_em')  # FIFO — mais antigas primeiro
        )


class FilaDiretorView(DiretorRequiredMixin, ListView):
    template_name = 'aprovacoes/fila_diretor.html'
    context_object_name = 'requisicoes'

    def get_queryset(self):
        # D-06: Diretor vê todas as unidades
        return (
            Requisicao.objects
            .filter(status=Requisicao.Status.PENDENTE_DIRETOR)
            .select_related('criado_por', 'categoria', 'unidade')
            .order_by('criado_em')
        )
```

---

### Badge de Status com Classes CSS Existentes

```html
<!-- Source: static/css/main.css badges existentes [VERIFIED: static/css/main.css] -->
<!-- Status → CSS class mapping (alinha com badges já no design system) -->

{% if req.status == 'RASCUNHO' %}
  <span class="badge" style="background:#374151;color:#9ca3af;">Rascunho</span>
{% elif req.status == 'PENDENTE_GESTOR' %}
  <span class="badge badge-aguardando">Aguardando Gestor</span>
{% elif req.status == 'PENDENTE_DIRETOR' %}
  <span class="badge badge-em-cotacao">Aguardando Diretor</span>
{% elif req.status == 'APROVADO' %}
  <span class="badge badge-ativo">Aprovado</span>
{% elif req.status == 'REPROVADO' %}
  <span class="badge badge-inativo">Reprovado</span>
{% elif req.status == 'CANCELADO' %}
  <span class="badge" style="background:#374151;color:#9ca3af;">Cancelado</span>
{% endif %}
```

**Observação:** Os badges `.badge-aguardando` (amarelo), `.badge-em-cotacao` (azul), `.badge-ativo` (verde) e `.badge-inativo` (vermelho) já existem em `main.css`. `RASCUNHO` e `CANCELADO` usam estilo inline cinza pois não há badge neutro definido — o planner pode optar por adicionar `.badge-rascunho` e `.badge-cancelado` no Wave 0 da fase.

---

### Registro no Django Admin

```python
# apps/aprovacoes/admin.py
# Source: D-08, D-11 de CONTEXT.md [VERIFIED: 02-CONTEXT.md]

from django.contrib import admin
from .models import AprovacaoLog, ConfiguracaoAlcada


@admin.register(ConfiguracaoAlcada)
class ConfiguracaoAlcadaAdmin(admin.ModelAdmin):
    """
    Singleton — impede criação de mais de uma linha.
    Admin/Diretor configura valor_maximo_gestor via Django admin.
    """
    def has_add_permission(self, request):
        return not ConfiguracaoAlcada.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False  # singleton — nunca deletar


@admin.register(AprovacaoLog)
class AprovacaoLogAdmin(admin.ModelAdmin):
    list_display = ['requisicao', 'aprovador', 'evento', 'criado_em']
    list_filter  = ['evento']
    readonly_fields = ['requisicao', 'aprovador', 'evento', 'motivo', 'criado_em', 'atualizado_em']

    def has_add_permission(self, request):
        return False  # logs são imutáveis — apenas leitura

    def has_delete_permission(self, request, obj=None):
        return False
```

---

## Estado da Arte

| Abordagem Antiga | Abordagem Atual | Quando Mudou | Impacto |
|-----------------|----------------|--------------|---------|
| `FSM libs` (django-fsm, viewflow) | `select_for_update()` + método no modelo | Django 1.x → 5.x | Para FSMs simples, o ORM nativo é mais legível e sem dependências extras [ASSUMED] |
| `Celery + Redis` para e-mail assíncrono | `transaction.on_commit()` + send_mail síncrono | Django 1.9+ | Suficiente para baixo volume; sem infra adicional [VERIFIED: CLAUDE.md + STATE.md] |
| `post_save signal` para lógica de negócio | Service layer explícito (`services.py`) | Padrão Django moderno | Signals têm ordem de execução implícita e são difíceis de testar [ASSUMED] |

**Deprecado/obsoleto:**
- `post_save` signals para lógica de workflow: substituído por service layer explícito (padrão já estabelecido neste projeto em `apps/accounts/services.py`).
- `FloatField` para valores monetários: substituído por `DecimalField(max_digits=12, decimal_places=2)` (constraint arquitetural do projeto).

---

## Inventário de Estado em Tempo de Execução

> Esta fase é **greenfield** (cria novos apps). Não há estado em tempo de execução a migrar.
> Não aplicável.

---

## Disponibilidade de Ambiente

| Dependência | Necessária Para | Disponível | Versão | Fallback |
|-------------|----------------|-----------|--------|---------|
| Python 3.12 | Runtime da aplicação | Ver nota abaixo | — | — |
| Django 5.2.* | Framework | Sim (via requirements.txt) | 5.2.* pinado | — |
| PostgreSQL 15 | Banco de dados | A confirmar | — | — |
| django-anymail | Envio de e-mail | Sim | 15.0 (instalado) | `fail_silently=True` em dev |
| AWS SES | E-mail produção | Pendente (SES domain + DNS) | — | Backend SMTP para testes |
| django-htmx | HTMX integration | Sim | 1.27.0 (instalado) | — |

**Nota sobre Python:** O ambiente de desenvolvimento local tem Python 3.14.5 instalado, mas o projeto usa Docker com Python 3.12 (conforme CLAUDE.md). As novas apps devem ser desenvolvidas e testadas dentro do container.

**Dependências faltantes sem fallback:**
- SES domain/DNS para e-mail de produção (não bloqueia desenvolvimento — `fail_silently=True` + SMTP local/Mailtrap para testes).

**STATE.md registrou como item aberto:** "Clarify SES domain + DNS access before Phase 2 email work begins." Este bloqueio afeta e-mail em produção, mas não o desenvolvimento da lógica de negócio.

---

## Arquitetura de Validação (Nyquist)

### Framework de Testes

| Propriedade | Valor |
|------------|-------|
| Framework | pytest-django (já configurado) |
| Arquivo de config | `pytest.ini` (raiz do projeto) |
| Comando rápido | `pytest apps/requisicoes/ apps/aprovacoes/ -x -q` |
| Suite completa | `pytest -x -q` |

### Requisitos → Mapa de Testes

| ID | Comportamento | Tipo | Comando Automatizado | Arquivo Existe? |
|----|--------------|------|---------------------|----------------|
| REQ-01 | Solicitante cria requisição com todos os campos | unit | `pytest apps/requisicoes/tests/test_models.py -x` | Não — Wave 0 |
| REQ-01 | Formulário valida campos obrigatórios | unit | `pytest apps/requisicoes/tests/test_forms.py -x` | Não — Wave 0 |
| REQ-02 | Badge de status atualiza na tela do Solicitante | unit (view) | `pytest apps/requisicoes/tests/test_views.py::test_detalhe_status -x` | Não — Wave 0 |
| REQ-03 | AprovacaoLog criado em cada transição | unit | `pytest apps/aprovacoes/tests/test_services.py::test_log_criado -x` | Não — Wave 0 |
| REQ-04 | E-mail enviado a Gestores ao submeter | unit (mock) | `pytest apps/aprovacoes/tests/test_services.py::test_email_gestores -x` | Não — Wave 0 |
| APROV-01 | Gestor vê apenas requisições da própria unidade | unit (view) | `pytest apps/aprovacoes/tests/test_views.py::test_fila_gestor_filtro -x` | Não — Wave 0 |
| APROV-02 | Gestor aprova → status correto (< alçada = APROVADO) | unit | `pytest apps/aprovacoes/tests/test_services.py::test_aprovar_gestor_baixo_valor -x` | Não — Wave 0 |
| APROV-02 | Gestor aprova → status correto (>= alçada = PENDENTE_DIRETOR) | unit | `pytest apps/aprovacoes/tests/test_services.py::test_aprovar_gestor_alto_valor -x` | Não — Wave 0 |
| APROV-03 | Diretor vê apenas PENDENTE_DIRETOR, todas as unidades | unit (view) | `pytest apps/aprovacoes/tests/test_views.py::test_fila_diretor -x` | Não — Wave 0 |
| APROV-04 | Diretor aprova → APROVADO; Diretor reprova → REPROVADO | unit | `pytest apps/aprovacoes/tests/test_services.py::test_aprovar_diretor -x` | Não — Wave 0 |
| APROV-05 | Reprovação sem motivo é rejeitada | unit | `pytest apps/aprovacoes/tests/test_services.py::test_reprovar_sem_motivo -x` | Não — Wave 0 |
| APROV-06 | Config alçada nula → sempre 2 níveis | unit | `pytest apps/aprovacoes/tests/test_services.py::test_alcada_nula -x` | Não — Wave 0 |
| D-15 | Cancelamento bloqueado em PENDENTE_DIRETOR | unit | `pytest apps/aprovacoes/tests/test_services.py::test_cancelar_pendente_diretor -x` | Não — Wave 0 |
| D-15 | Cancelamento permitido em RASCUNHO e PENDENTE_GESTOR | unit | `pytest apps/aprovacoes/tests/test_services.py::test_cancelar_estados_validos -x` | Não — Wave 0 |
| Race cond. | select_for_update bloqueia segundo Gestor | integration | Manual — requer conexões paralelas | — |

### Taxa de Amostragem

- **Por commit de tarefa:** `pytest apps/requisicoes/ apps/aprovacoes/ -x -q`
- **Por merge de wave:** `pytest -x -q` (suite completa)
- **Gate de fase:** Suite completa verde antes de `/gsd-verify-work`

### Lacunas do Wave 0

- [ ] `apps/requisicoes/tests/__init__.py` — criar
- [ ] `apps/requisicoes/tests/conftest.py` — fixtures: `categoria`, `requisicao_rascunho`, `requisicao_pendente_gestor`
- [ ] `apps/requisicoes/tests/test_models.py` — cobre REQ-01, REQ-02
- [ ] `apps/requisicoes/tests/test_forms.py` — cobre REQ-01 validação
- [ ] `apps/requisicoes/tests/test_views.py` — cobre REQ-01, REQ-02, APROV-01
- [ ] `apps/aprovacoes/tests/__init__.py` — criar
- [ ] `apps/aprovacoes/tests/conftest.py` — fixtures: `diretor_user`, `config_alcada`
- [ ] `apps/aprovacoes/tests/test_services.py` — cobre REQ-03, REQ-04, APROV-02..06, D-15
- [ ] `apps/aprovacoes/tests/test_views.py` — cobre APROV-01, APROV-03

---

## Domínio de Segurança

### Categorias ASVS Aplicáveis (ASVS Level 1)

| Categoria ASVS | Aplica | Controle Padrão |
|---------------|--------|----------------|
| V2 Autenticação | Não (já implementado na Fase 1) | — |
| V3 Gestão de Sessão | Não (já implementado na Fase 1) | — |
| V4 Controle de Acesso | **Sim** | `GestorRequiredMixin`, `DiretorRequiredMixin`, verificação de propriedade no service |
| V5 Validação de Input | **Sim** | Django ModelForm + validação no service (defense in depth) |
| V6 Criptografia | Não | — |
| V13 API | Não (sem DRF em v1) | — |

### Padrões de Ameaça Conhecidos

| Padrão | STRIDE | Mitigação Padrão |
|--------|--------|-----------------|
| Gestor aprovando requisição de outra unidade | Elevation of Privilege | Queryset filtra por `unidade=request.user.default_unit`; verificar ownership no service |
| Solicitante agindo como Gestor (URL manipulation) | Spoofing | `GestorRequiredMixin` em todas as views de aprovação |
| Reprovação sem motivo (bypass HTML required) | Tampering | Validação no service antes do `transaction.atomic()` |
| Race condition em aprovação dupla | Tampering | `select_for_update()` + verificação de estado pós-lock |
| Acesso a detalhe de requisição de outra unidade | Information Disclosure | View de detalhe verifica `req.criado_por == request.user OR role in (gestor, diretor, admin)` |
| CSRF em HTMX POST de modais | Cross-Site Request Forgery | `{% csrf_token %}` em todos os forms de partials (lição do CR-04 da Fase 1) |

### Verificação Adicional de Ownership

Em views de detalhe e de ação (cancelar, ver histórico), a lógica deve verificar ownership ou role antes de servir o objeto:

```python
# Exemplo: view de detalhe da requisição
def get_object(self):
    req = get_object_or_404(Requisicao, pk=self.kwargs['pk'])
    user = self.request.user
    if user.role in ('admin', 'diretor'):
        return req
    if user.role == 'gestor':
        if req.unidade != user.default_unit:
            raise PermissionDenied
        return req
    # Solicitante só vê suas próprias
    if req.criado_por != user:
        raise PermissionDenied
    return req
```

---

## Restrições do Projeto (de CLAUDE.md)

| Diretiva | Origem | Impacto na Fase 2 |
|---------|--------|-----------------|
| Python 3.12 + Django 5.2 LTS | CLAUDE.md §Constraints | Código usa apenas APIs do Django 5.2; nenhuma feature de 5.3+ |
| HTMX 2.0.x | CLAUDE.md §Technology Stack | Usar `hx-on::after-request` (sintaxe 2.0) para callbacks de modal |
| Sem Celery/Redis | CLAUDE.md §What NOT to Use | E-mail apenas via `transaction.on_commit()` |
| Sem DRF | CLAUDE.md §What NOT to Use | Nenhuma API REST — views Django puras |
| `DecimalField(max_digits=12, decimal_places=2)` | CLAUDE.md §Database | `valor_estimado` e `valor_maximo_gestor` obrigatoriamente este tipo |
| `select_for_update()` + `transaction.atomic()` | CLAUDE.md §Approval Workflow | Todas as transições de estado em `services.py` |
| `transaction.on_commit()` para e-mail | CLAUDE.md §Email Notifications | Sem `send_mail()` dentro do bloco atômico |
| ReportLab para PDF | CLAUDE.md §PDF Generation | Não aplicável nesta fase (relatórios são Fase 5) |
| SQLite proibido | CLAUDE.md §What NOT to Use | PostgreSQL em todos os ambientes, incluindo testes |
| Toda lógica em `services.py` | CLAUDE.md + STATE.md | Views são thin; service orquestra tudo |

---

## Log de Premissas

| # | Premissa | Seção | Risco se Errada |
|---|----------|-------|----------------|
| A1 | FSM libs externas (django-fsm) são desnecessárias para esta FSM de 6 estados | State of the Art | Baixo — a FSM é simples; métodos no modelo + service layer são idiomáticos em Django |
| A2 | `ConfiguracaoAlcada` deve ter `has_add_permission` bloqueado após existência, não limitar a `pk=1` por constraint DB | Anti-Patterns | Baixo — `pk=1` em `get_or_create` garante singleton sem constraint extra |
| A3 | `fail_silently=True` em `send_mail` é aceitável para v1 com volume baixo | Padrão 4 | Médio — e-mails silenciosos podem atrasar adoção; monitorar logs do SES |
| A4 | Polling HTMX para status em tempo real é suficiente (REQ-02) sem WebSockets | Arquitetura | Baixo — 20 usuários, HTMX polling de 15s é padrão documentado no CLAUDE.md |
| A5 | Django admin nativo é suficiente para `CategoriaCompra` e `ConfiguracaoAlcada` (D-03, D-11) | Estrutura de Apps | Baixo — se Admin precisar de mais UX, o planner pode adicionar view HTMX dedicada |

---

## Questões em Aberto

1. **SES domain para e-mail**
   - O que sabemos: django-anymail está instalado; lógica de e-mail será implementada com `fail_silently=True` em dev.
   - O que está incerto: Se DNS/SPF/DKIM do domínio do cliente estão configurados no SES para produção.
   - Recomendação: Implementar e-mail com `fail_silently=True` em dev e SMTP (Mailtrap ou console backend) para testes. O planner deve incluir uma tarefa de smoke test de e-mail separada bloqueada por `checkpoint:human-verify` para produção.

2. **Solicitante com `default_unit=None` — formulário de requisição**
   - O que sabemos: `UNIT-03` diz que a unidade padrão é pré-selecionada mas pode ser alterada. `User.default_unit` é nullable (`null=True, blank=True`).
   - O que está incerto: O que acontece quando Solicitante não tem unidade configurada? O formulário deve exibir um select de todas as unidades ativas, sem pré-seleção?
   - Recomendação: O planner deve tratar esse caso explicitamente. Sugestão: se `default_unit` for None, exibir select de todas as unidades ativas. Se tiver `default_unit`, pré-selecionar mas permitir mudança.

3. **Textarea vs CharField para `justificativa` e `descricao`**
   - O que sabemos: CONTEXT.md não especifica `max_length` para esses campos.
   - O que está incerto: Há um limite operacional para a descrição de uma requisição?
   - Recomendação: `descricao = CharField(max_length=500)` e `justificativa = TextField()`. Planner decide.

---

## Fontes

### Primárias (confiança HIGH)
- `apps/accounts/models.py` — `User.role`, `User.default_unit`, `UnidadeOrganizacional` verificados
- `apps/core/models.py` — `AuditedModel`, `TimestampedModel` verificados
- `apps/accounts/views.py` — `AdminRequiredMixin` verificado (padrão a replicar)
- `config/settings/base.py` — `INSTALLED_APPS`, `MIDDLEWARE`, `HtmxMiddleware` verificados
- `templates/base.html` — CSRF meta tag + htmx:configRequest handler verificados
- `static/css/main.css` — classes de badge e componentes verificados
- `apps/accounts/tests/conftest.py` — fixtures `gestor_user`, `solicitante_user` verificados
- `pytest.ini` — configuração de testes verificada
- `.planning/phases/02-requisitions-approvals/02-CONTEXT.md` — todas as decisões D-01..D-19
- `STATE.md` — constraints arquiteturais confirmados
- `CLAUDE.md` — stack, padrões, restrições
- `01-REVIEW.md` — CR-04 (CSRF em HTMX partials), outros anti-padrões identificados na Fase 1

### Secundárias (confiança MEDIUM)
- Django docs `select_for_update`: https://docs.djangoproject.com/en/5.2/ref/models/querysets/#select-for-update [CITED]
- Django docs `on_commit`: https://docs.djangoproject.com/en/5.2/topics/db/transactions/#performing-actions-after-commit [CITED]

---

## Metadados

**Breakdown de confiança:**
- Stack padrão: HIGH — nenhum pacote novo; tudo verificado no ambiente e em requirements.txt
- Arquitetura: HIGH — baseado em código existente do projeto + constraints documentados em STATE.md + CLAUDE.md
- Armadilhas: HIGH — CR-04 da Fase 1 confirmado; race condition documentado no Django; experience-based

**Data da pesquisa:** 2026-06-10
**Válida até:** 2026-07-10 (stack estável; sem dependências fast-moving)
