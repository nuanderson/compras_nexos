"""
Testes das views do Diretor (slice vertical do 2o nivel de aprovacao).

Cobre:
  APROV-03  fila do Diretor sem filtro de unidade (D-06)
  APROV-04  aprovacao/reprovacao de 2o nivel
  APROV-05  motivo obrigatorio em reprovacao
  D-13      reprovacao permanente — sem reabertura

Fixtures reutilizadas de apps/aprovacoes/tests/conftest.py.
"""
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.accounts.models import UnidadeOrganizacional, User
from apps.aprovacoes.models import AprovacaoLog
from apps.requisicoes.models import Requisicao


# ─────────────────────────────────────────────
# Fixtures adicionais para este arquivo
# ─────────────────────────────────────────────


@pytest.fixture
def segunda_unidade(db):
    """Segunda unidade organizacional para testar D-06 (sem filtro de unidade)."""
    return UnidadeOrganizacional.objects.create(
        nome="Unidade B",
        descricao="Segunda unidade para teste",
        ativo=True,
    )


# ─────────────────────────────────────────────
# Helpers de URL
# ─────────────────────────────────────────────

FILA_DIRETOR_URL = "aprovacoes:fila-diretor"
APROVAR_DIRETOR_URL = "aprovacoes:aprovar-diretor"
MODAL_REPROVAR_DIRETOR_URL = "aprovacoes:modal-reprovar-diretor"
REPROVAR_DIRETOR_URL = "aprovacoes:reprovar-diretor"


# ─────────────────────────────────────────────
# Testes de fila (D-06, APROV-03)
# ─────────────────────────────────────────────


@pytest.mark.django_db
def test_fila_diretor_todas_unidades(
    client, diretor_user, solicitante_user, categoria, test_unit, segunda_unidade
):
    """
    Diretor ve PENDENTE_DIRETOR de TODAS as unidades (D-06, APROV-03).
    Requisicoes de unidade A e unidade B devem aparecer juntas.
    """
    req_a = Requisicao.objects.create(
        descricao="Requisicao da Unidade A",
        categoria=categoria,
        valor_estimado=Decimal("5000.00"),
        justificativa="Justificativa A",
        unidade=test_unit,
        status=Requisicao.Status.PENDENTE_DIRETOR,
        criado_por=solicitante_user,
    )
    req_b = Requisicao.objects.create(
        descricao="Requisicao da Unidade B",
        categoria=categoria,
        valor_estimado=Decimal("3000.00"),
        justificativa="Justificativa B",
        unidade=segunda_unidade,
        status=Requisicao.Status.PENDENTE_DIRETOR,
        criado_por=solicitante_user,
    )

    client.force_login(diretor_user)
    response = client.get(reverse(FILA_DIRETOR_URL))

    assert response.status_code == 200
    requisicoes = list(response.context["requisicoes"])
    pks = [r.pk for r in requisicoes]
    assert req_a.pk in pks, "Requisicao da Unidade A deve estar na fila do Diretor"
    assert req_b.pk in pks, "Requisicao da Unidade B deve estar na fila do Diretor"


@pytest.mark.django_db
def test_fila_diretor_so_pendente_diretor(
    client, diretor_user, solicitante_user, categoria, test_unit
):
    """
    Fila do Diretor mostra APENAS PENDENTE_DIRETOR.
    PENDENTE_GESTOR e APROVADO nao aparecem.
    """
    req_pendente_dir = Requisicao.objects.create(
        descricao="Pendente Diretor",
        categoria=categoria,
        valor_estimado=Decimal("5000.00"),
        justificativa="ok",
        unidade=test_unit,
        status=Requisicao.Status.PENDENTE_DIRETOR,
        criado_por=solicitante_user,
    )
    req_pendente_gest = Requisicao.objects.create(
        descricao="Pendente Gestor",
        categoria=categoria,
        valor_estimado=Decimal("500.00"),
        justificativa="ok",
        unidade=test_unit,
        status=Requisicao.Status.PENDENTE_GESTOR,
        criado_por=solicitante_user,
    )
    req_aprovado = Requisicao.objects.create(
        descricao="Aprovado",
        categoria=categoria,
        valor_estimado=Decimal("500.00"),
        justificativa="ok",
        unidade=test_unit,
        status=Requisicao.Status.APROVADO,
        criado_por=solicitante_user,
    )

    client.force_login(diretor_user)
    response = client.get(reverse(FILA_DIRETOR_URL))

    assert response.status_code == 200
    pks = [r.pk for r in response.context["requisicoes"]]
    assert req_pendente_dir.pk in pks
    assert req_pendente_gest.pk not in pks, "PENDENTE_GESTOR nao deve aparecer na fila do Diretor"
    assert req_aprovado.pk not in pks, "APROVADO nao deve aparecer na fila do Diretor"


# ─────────────────────────────────────────────
# Testes de controle de acesso (T-04-01)
# ─────────────────────────────────────────────


@pytest.mark.django_db
def test_gestor_nao_acessa_fila_diretor(client, gestor_user):
    """Gestor nao pode acessar a fila do Diretor — deve receber 403 (T-04-01)."""
    client.force_login(gestor_user)
    response = client.get(reverse(FILA_DIRETOR_URL))
    assert response.status_code == 403


@pytest.mark.django_db
def test_solicitante_nao_acessa_fila_diretor(client, solicitante_user):
    """Solicitante nao pode acessar a fila do Diretor — deve receber 403 (T-04-01)."""
    client.force_login(solicitante_user)
    response = client.get(reverse(FILA_DIRETOR_URL))
    assert response.status_code == 403


# ─────────────────────────────────────────────
# Testes de aprovacao (APROV-04)
# ─────────────────────────────────────────────


@pytest.mark.django_db
def test_aprovar_diretor(client, diretor_user, requisicao_pendente_diretor):
    """
    POST aprovar-diretor em PENDENTE_DIRETOR transiciona para APROVADO (APROV-04).
    Cria AprovacaoLog com evento APROVACAO_FINAL.
    """
    client.force_login(diretor_user)
    response = client.post(
        reverse(APROVAR_DIRETOR_URL, args=[requisicao_pendente_diretor.pk])
    )

    assert response.status_code == 200
    requisicao_pendente_diretor.refresh_from_db()
    assert requisicao_pendente_diretor.status == Requisicao.Status.APROVADO

    log = AprovacaoLog.objects.filter(
        requisicao=requisicao_pendente_diretor,
        evento=AprovacaoLog.Evento.APROVACAO_FINAL,
    )
    assert log.exists(), "AprovacaoLog com APROVACAO_FINAL deve ser criado"


@pytest.mark.django_db
def test_aprovar_diretor_estado_invalido_409(
    client, diretor_user, solicitante_user, categoria, test_unit
):
    """
    POST aprovar-diretor em PENDENTE_GESTOR deve retornar 409 (Armadilha 4).
    Estado nao aceita acao de Diretor.
    """
    req = Requisicao.objects.create(
        descricao="Estado invalido para Diretor",
        categoria=categoria,
        valor_estimado=Decimal("500.00"),
        justificativa="ok",
        unidade=test_unit,
        status=Requisicao.Status.PENDENTE_GESTOR,
        criado_por=solicitante_user,
    )

    client.force_login(diretor_user)
    response = client.post(reverse(APROVAR_DIRETOR_URL, args=[req.pk]))
    assert response.status_code == 409


# ─────────────────────────────────────────────
# Testes de modal de reprovacao
# ─────────────────────────────────────────────


@pytest.mark.django_db
def test_modal_reprovar_diretor_get(client, diretor_user, requisicao_pendente_diretor):
    """
    GET modal-reprovar-diretor retorna 200 com textarea name="motivo".
    """
    client.force_login(diretor_user)
    response = client.get(
        reverse(MODAL_REPROVAR_DIRETOR_URL, args=[requisicao_pendente_diretor.pk])
    )

    assert response.status_code == 200
    assert b'name="motivo"' in response.content


# ─────────────────────────────────────────────
# Testes de reprovacao (APROV-04, APROV-05, D-13)
# ─────────────────────────────────────────────


@pytest.mark.django_db
def test_reprovar_diretor_sem_motivo_rejeitado(
    client, diretor_user, requisicao_pendente_diretor
):
    """
    POST reprovar-diretor sem motivo nao transiciona (APROV-05).
    Estado permanece PENDENTE_DIRETOR.
    """
    client.force_login(diretor_user)
    response = client.post(
        reverse(REPROVAR_DIRETOR_URL, args=[requisicao_pendente_diretor.pk]),
        data={"motivo": ""},
    )

    # Deve retornar o modal com erros (nao transicionar) — 422 com HX-Retarget (WR-02)
    assert response.status_code == 422
    requisicao_pendente_diretor.refresh_from_db()
    assert requisicao_pendente_diretor.status == Requisicao.Status.PENDENTE_DIRETOR, (
        "Status nao deve mudar sem motivo valido"
    )


@pytest.mark.django_db
def test_reprovar_diretor_com_motivo(
    client, diretor_user, requisicao_pendente_diretor
):
    """
    POST reprovar-diretor com motivo transiciona para REPROVADO (APROV-04, APROV-05).
    Cria AprovacaoLog com motivo.
    """
    client.force_login(diretor_user)
    motivo = "Valor acima do orcamento aprovado para o periodo."
    response = client.post(
        reverse(REPROVAR_DIRETOR_URL, args=[requisicao_pendente_diretor.pk]),
        data={"motivo": motivo},
    )

    assert response.status_code == 200
    requisicao_pendente_diretor.refresh_from_db()
    assert requisicao_pendente_diretor.status == Requisicao.Status.REPROVADO

    log = AprovacaoLog.objects.filter(
        requisicao=requisicao_pendente_diretor,
        evento=AprovacaoLog.Evento.REPROVACAO,
        motivo=motivo,
    )
    assert log.exists(), "AprovacaoLog com motivo deve ser criado"


@pytest.mark.django_db
def test_reprovado_permanente(
    client, diretor_user, solicitante_user, categoria, test_unit
):
    """
    POST aprovar-diretor em REPROVADO retorna 409 — reprovacao e permanente (D-13).
    Nao existe rota de reabertura.
    """
    req = Requisicao.objects.create(
        descricao="Requisicao reprovada",
        categoria=categoria,
        valor_estimado=Decimal("5000.00"),
        justificativa="ok",
        unidade=test_unit,
        status=Requisicao.Status.REPROVADO,
        criado_por=solicitante_user,
    )

    client.force_login(diretor_user)
    response = client.post(reverse(APROVAR_DIRETOR_URL, args=[req.pk]))
    assert response.status_code == 409, "Requisicao REPROVADA nao pode ser aprovada (D-13)"
