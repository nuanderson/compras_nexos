"""
Service layer para apps/cotacoes.

Toda a logica de negocio do ciclo RFQ vive aqui — as views delegam a estas funcoes
e nunca contem logica de negocio diretamente (padrão estabelecido em aprovacoes/services.py).

Funcoes:
  criar_rfq           — cria RFQ vinculado a requisicao aprovada (COT-01, D-06)
  adicionar_cotacao   — adiciona CotacaoFornecedor ao RFQ (COT-02, D-08)
  remover_cotacao     — remove CotacaoFornecedor do RFQ (COT-02, D-08)
  calcular_comparativo — retorna lista ordenada com delta % e is_menor (COT-03, D-09)
  selecionar_vencedor — define vencedor imutavel com justificativa (COT-04, D-07, T-04-05/06)

Seguranca:
  T-04-04  Guard `if menor > 0` em calcular_comparativo evita ZeroDivisionError
  T-04-05  transaction.atomic() + select_for_update() em selecionar_vencedor
  T-04-06  Guard `if rfq.tem_vencedor` dentro da transacao (defense in depth)
"""
from decimal import Decimal
from typing import Any

from django.db import transaction

from .models import CotacaoFornecedor, RFQ


def criar_rfq(requisicao_pk: int, comprador) -> RFQ:
    """
    Cria um RFQ vinculado a uma Requisicao aprovada.

    O IntegrityError do OneToOneField propaga para a view capturar (T-04-02, D-06).
    Retorna o RFQ criado.
    """
    return RFQ.objects.create(
        requisicao_id=requisicao_pk,
        criado_por=comprador,
    )


def adicionar_cotacao(rfq: RFQ, dados: dict) -> CotacaoFornecedor:
    """
    Adiciona uma CotacaoFornecedor ao RFQ.

    Bloqueia se rfq.tem_vencedor (defense in depth, D-08).

    Levanta:
        ValueError — se RFQ ja tem vencedor definido.
    """
    if rfq.tem_vencedor:
        raise ValueError("RFQ encerrado — nao aceita novas cotacoes.")
    return CotacaoFornecedor.objects.create(rfq=rfq, **dados)


def remover_cotacao(rfq: RFQ, cotacao_pk: int) -> None:
    """
    Remove uma CotacaoFornecedor do RFQ.

    Bloqueia se rfq.tem_vencedor (defense in depth, D-08).

    Levanta:
        ValueError — se RFQ ja tem vencedor definido.
        CotacaoFornecedor.DoesNotExist — se cotacao nao pertence ao RFQ.
    """
    if rfq.tem_vencedor:
        raise ValueError("RFQ encerrado — cotacoes imutaveis.")
    cotacao = CotacaoFornecedor.objects.get(pk=cotacao_pk, rfq=rfq)
    cotacao.delete()


def calcular_comparativo(rfq: RFQ) -> list[dict[str, Any]]:
    """
    Retorna lista de dicts com cotacao, delta percentual e is_menor.
    Ordenada por preco_unitario ASC (menor preco primeiro).

    Guard de divisao por zero (T-04-04): se menor <= 0, retorna delta Decimal("0").
    Retorna lista vazia se nao houver cotacoes.

    Cada dict: {"cotacao": CotacaoFornecedor, "delta": Decimal, "is_menor": bool}
    """
    cotacoes = list(
        rfq.cotacoes.select_related("fornecedor").order_by("preco_unitario")
    )
    if not cotacoes:
        return []

    menor = cotacoes[0].preco_unitario
    result = []
    for c in cotacoes:
        # Guard T-04-04: evita ZeroDivisionError quando menor <= 0
        if menor and menor > 0:
            delta = (
                (c.preco_unitario - menor) / menor * Decimal("100")
            ).quantize(Decimal("0.1"))
        else:
            delta = Decimal("0")
        result.append({
            "cotacao": c,
            "delta": delta,
            "is_menor": c.preco_unitario == menor,
        })
    return result


def selecionar_vencedor(
    rfq_pk: int,
    cotacao_pk: int,
    justificativa: str,
    comprador,
) -> RFQ:
    """
    Define o vencedor do RFQ. Imutavel apos salvo. (COT-04, D-07)

    Validacao de justificativa ocorre ANTES de abrir a transacao (defense in depth,
    padrão de reprovar_requisicao em aprovacoes/services.py).

    select_for_update() serializa dois Compradores simultaneos (T-04-05).
    Guard `rfq.tem_vencedor` dentro da transacao impede dupla selecao (T-04-06).

    Levanta:
        ValueError — se justificativa estiver vazia ou apenas espacos.
        ValueError — se RFQ ja tem vencedor definido.
        CotacaoFornecedor.DoesNotExist — se cotacao nao pertence ao RFQ.
    """
    # Validacao ANTES do transaction.atomic() (defense in depth, T-04-06)
    if not justificativa or not justificativa.strip():
        raise ValueError("Justificativa e obrigatoria para selecionar o vencedor.")

    with transaction.atomic():
        rfq = RFQ.objects.select_for_update().get(pk=rfq_pk)

        if rfq.tem_vencedor:
            raise ValueError("Vencedor já foi definido para este RFQ.")

        cotacao = CotacaoFornecedor.objects.get(pk=cotacao_pk, rfq=rfq)
        rfq.vencedor = cotacao
        rfq.justificativa_selecao = justificativa.strip()
        rfq.save(update_fields=["vencedor", "justificativa_selecao", "atualizado_em"])

    return rfq
