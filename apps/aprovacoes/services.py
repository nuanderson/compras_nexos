"""
Aprovacoes service layer.
Máquina de estados completa para Requisicao: submeter, aprovar (gestor/diretor),
reprovar e cancelar.
Views chamam estas funções — nunca contêm lógica de negócio diretamente.

Todas as transições são atômicas com select_for_update() para evitar race conditions
(Armadilha 3 do RESEARCH.md — dois Gestores aprovando simultaneamente).

Referências de decisão:
  D-09  alçada por valor
  D-10  fail-safe quando valor_maximo_gestor=None → sempre 2 níveis
  D-15  regras de cancelamento
  APROV-04  Diretor aprova/reprova
  APROV-05  motivo obrigatório em reprovação
  REQ-03    log imutável de cada transição
  REQ-04    notificação ao Gestor (stub neste plano — implementado no Plano 03)
"""
import logging

from django.db import transaction

from apps.requisicoes.models import Requisicao

from .models import AprovacaoLog, ConfiguracaoAlcada

logger = logging.getLogger(__name__)


def submeter_requisicao(requisicao_pk: int, solicitante) -> Requisicao:
    """
    Transição RASCUNHO → PENDENTE_GESTOR.

    Levanta:
        ValueError       — se a requisição não está em RASCUNHO.
        PermissionError  — se `solicitante` não é o criador da requisição.

    Após commit, agenda _notificar_gestores via transaction.on_commit.
    """
    with transaction.atomic():
        req = Requisicao.objects.select_for_update().get(pk=requisicao_pk)

        if not req.pode_submeter():
            raise ValueError(
                f"Requisição em estado '{req.status}' não pode ser submetida."
            )

        if req.criado_por != solicitante:
            raise PermissionError(
                "Apenas o Solicitante pode enviar esta requisição."
            )

        req.status = Requisicao.Status.PENDENTE_GESTOR
        req.save(update_fields=["status", "atualizado_em"])

        AprovacaoLog.objects.create(
            requisicao=req,
            aprovador=solicitante,
            evento=AprovacaoLog.Evento.ENVIO,
        )

        transaction.on_commit(lambda: _notificar_gestores(req.pk))

    return req


def aprovar_gestor(requisicao_pk: int, gestor) -> Requisicao:
    """
    Transição PENDENTE_GESTOR → APROVADO ou PENDENTE_DIRETOR.

    O destino depende de ConfiguracaoAlcada.requer_diretor(valor_estimado):
      - True  → PENDENTE_DIRETOR (evento APROVACAO_GESTOR)
      - False → APROVADO         (evento APROVACAO_FINAL)

    Fail-safe D-10: se valor_maximo_gestor=None, sempre → PENDENTE_DIRETOR.

    Levanta:
        ValueError — se a requisição não está em PENDENTE_GESTOR.
    """
    with transaction.atomic():
        req = Requisicao.objects.select_for_update().get(pk=requisicao_pk)

        if not req.pode_gestor_agir():
            raise ValueError(
                f"Estado '{req.status}' não aceita ação de Gestor."
            )

        config = ConfiguracaoAlcada.obter()

        if config.requer_diretor(req.valor_estimado):
            req.status = Requisicao.Status.PENDENTE_DIRETOR
            evento = AprovacaoLog.Evento.APROVACAO_GESTOR
        else:
            req.status = Requisicao.Status.APROVADO
            evento = AprovacaoLog.Evento.APROVACAO_FINAL

        req.save(update_fields=["status", "atualizado_em"])

        AprovacaoLog.objects.create(
            requisicao=req,
            aprovador=gestor,
            evento=evento,
        )

    return req


def aprovar_diretor(requisicao_pk: int, diretor) -> Requisicao:
    """
    Transição PENDENTE_DIRETOR → APROVADO. (APROV-04)

    Levanta:
        ValueError — se a requisição não está em PENDENTE_DIRETOR.
    """
    with transaction.atomic():
        req = Requisicao.objects.select_for_update().get(pk=requisicao_pk)

        if not req.pode_diretor_agir():
            raise ValueError(
                f"Estado '{req.status}' não aceita ação de Diretor."
            )

        req.status = Requisicao.Status.APROVADO
        req.save(update_fields=["status", "atualizado_em"])

        AprovacaoLog.objects.create(
            requisicao=req,
            aprovador=diretor,
            evento=AprovacaoLog.Evento.APROVACAO_FINAL,
        )

    return req


def reprovar_requisicao(requisicao_pk: int, aprovador, motivo: str) -> Requisicao:
    """
    Transição para REPROVADO (estado terminal). Motivo obrigatório. (APROV-05)

    A validação do motivo ocorre ANTES de abrir a transação (defense in depth, T-02-02):
    mesmo que alguém chame o service diretamente sem passar pelo form, o motivo é validado.

    Levanta:
        ValueError — se motivo estiver vazio ou composto apenas de espaços.
        ValueError — se a requisição não está em PENDENTE_GESTOR ou PENDENTE_DIRETOR.
    """
    # Validação ANTES do transaction.atomic() (defense in depth, T-02-02)
    if not motivo or not motivo.strip():
        raise ValueError("Motivo é obrigatório para reprovação.")

    with transaction.atomic():
        req = Requisicao.objects.select_for_update().get(pk=requisicao_pk)

        if req.status not in (
            Requisicao.Status.PENDENTE_GESTOR,
            Requisicao.Status.PENDENTE_DIRETOR,
        ):
            raise ValueError(
                f"Estado '{req.status}' não permite reprovação."
            )

        req.status = Requisicao.Status.REPROVADO
        req.save(update_fields=["status", "atualizado_em"])

        AprovacaoLog.objects.create(
            requisicao=req,
            aprovador=aprovador,
            evento=AprovacaoLog.Evento.REPROVACAO,
            motivo=motivo,
        )

    return req


def cancelar_requisicao(requisicao_pk: int, solicitante) -> Requisicao:
    """
    Transição para CANCELADO. Permitida apenas em RASCUNHO ou PENDENTE_GESTOR. (D-15)

    Levanta:
        ValueError       — se a requisição não pode ser cancelada (D-15).
        PermissionError  — se `solicitante` não é o criador da requisição.
    """
    with transaction.atomic():
        req = Requisicao.objects.select_for_update().get(pk=requisicao_pk)

        if not req.pode_cancelar():
            raise ValueError(
                f"Requisição em estado '{req.status}' não pode ser cancelada."
            )

        if req.criado_por != solicitante:
            raise PermissionError(
                "Apenas o Solicitante pode cancelar esta requisição."
            )

        req.status = Requisicao.Status.CANCELADO
        req.save(update_fields=["status", "atualizado_em"])

        AprovacaoLog.objects.create(
            requisicao=req,
            aprovador=solicitante,
            evento=AprovacaoLog.Evento.CANCELAMENTO,
        )

    return req


def _notificar_gestores(requisicao_pk: int) -> None:
    """
    STUB — Notificação de e-mail aos Gestores da unidade. (REQ-04, D-07, D-16)

    Esta função é chamada via transaction.on_commit após submeter_requisicao().
    O envio real do e-mail (REQ-04, D-07, D-16) pertence ao slice do Gestor no Plano 03.

    *** IMPLEMENTAÇÃO REAL PENDENTE — PLANO 03 ***

    A função NÃO levanta exceção (seria engolida pelo on_commit),
    mas emite um WARNING visível nos logs para que a ausência de implementação
    não passe despercebida. O Plano 03 substituirá este corpo pelo envio real
    via django-anymail + AWS SES.
    """
    logger.warning(
        "STUB: _notificar_gestores não implementado — "
        "REQ-04 requer implementação no Plano 03 (requisicao_pk=%s)",
        requisicao_pk,
    )
