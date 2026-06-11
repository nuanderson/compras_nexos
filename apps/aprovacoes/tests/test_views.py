"""
Testes de view para o slice vertical do Gestor.

Cobre: APROV-01, APROV-02, APROV-05, D-04, D-05, D-09, T-03-01, T-03-02.
Armadilhas testadas: default_unit=None (Armadilha 3), 409 em estado invalido (Armadilha 4).
"""
from decimal import Decimal

import pytest

from apps.accounts.models import UnidadeOrganizacional, User
from apps.aprovacoes.models import AprovacaoLog, ConfiguracaoAlcada
from apps.requisicoes.models import CategoriaCompra, Requisicao


# ─────────────────────────────────────────────
# Fixtures locais
# ─────────────────────────────────────────────


@pytest.fixture
def unidade_a(db):
    return UnidadeOrganizacional.objects.create(nome="Unidade A Views", ativo=True)


@pytest.fixture
def unidade_b(db):
    return UnidadeOrganizacional.objects.create(nome="Unidade B Views", ativo=True)


@pytest.fixture
def categoria(db):
    return CategoriaCompra.objects.create(nome="Categoria Views", ativo=True)


@pytest.fixture
def gestor(db, unidade_a):
    return User.objects.create_user(
        username="gestor_views",
        email="gestor_views@test.com",
        password="testpass123",
        role=User.Role.GESTOR,
        default_unit=unidade_a,
    )


@pytest.fixture
def gestor_sem_unidade(db):
    return User.objects.create_user(
        username="gestor_sem_unit",
        email="gestor_sem_unit@test.com",
        password="testpass123",
        role=User.Role.GESTOR,
        default_unit=None,
    )


@pytest.fixture
def solicitante(db, unidade_a):
    return User.objects.create_user(
        username="solicitante_views",
        email="solicitante_views@test.com",
        password="testpass123",
        role=User.Role.SOLICITANTE,
        default_unit=unidade_a,
    )


@pytest.fixture
def config_alcada(db):
    """ConfiguracaoAlcada com valor_maximo_gestor = R$ 1.000,00."""
    config, _ = ConfiguracaoAlcada.objects.get_or_create(pk=1)
    config.valor_maximo_gestor = Decimal("1000.00")
    config.save()
    return config


@pytest.fixture
def req_pendente_gestor(db, solicitante, categoria, unidade_a):
    """Requisicao PENDENTE_GESTOR, valor R$ 500 (abaixo da alcada)."""
    return Requisicao.objects.create(
        descricao="Papel A4 para escritorio",
        categoria=categoria,
        valor_estimado=Decimal("500.00"),
        justificativa="Estoque zerado",
        unidade=unidade_a,
        status=Requisicao.Status.PENDENTE_GESTOR,
        criado_por=solicitante,
    )


@pytest.fixture
def req_pendente_gestor_alto_valor(db, solicitante, categoria, unidade_a):
    """Requisicao PENDENTE_GESTOR, valor R$ 5.000 (acima da alcada)."""
    return Requisicao.objects.create(
        descricao="Servidor de alta performance",
        categoria=categoria,
        valor_estimado=Decimal("5000.00"),
        justificativa="Upgrade de infraestrutura",
        unidade=unidade_a,
        status=Requisicao.Status.PENDENTE_GESTOR,
        criado_por=solicitante,
    )


@pytest.fixture
def req_unidade_b(db, solicitante, categoria, unidade_b):
    """Requisicao PENDENTE_GESTOR da unidade B."""
    # Solicitante pertence a unidade_a; criamos a req manualmente na unidade_b
    return Requisicao.objects.create(
        descricao="Requisicao da unidade B",
        categoria=categoria,
        valor_estimado=Decimal("300.00"),
        justificativa="Teste de isolamento",
        unidade=unidade_b,
        status=Requisicao.Status.PENDENTE_GESTOR,
        criado_por=solicitante,
    )


@pytest.fixture
def req_aprovada(db, solicitante, categoria, unidade_a):
    """Requisicao ja APROVADA (estado invalido para acao de Gestor)."""
    return Requisicao.objects.create(
        descricao="Requisicao ja aprovada",
        categoria=categoria,
        valor_estimado=Decimal("200.00"),
        justificativa="Teste de estado invalido",
        unidade=unidade_a,
        status=Requisicao.Status.APROVADO,
        criado_por=solicitante,
    )


# ─────────────────────────────────────────────
# Testes de FilaGestorView
# ─────────────────────────────────────────────


@pytest.mark.django_db
def test_fila_gestor_filtra_unidade(client, gestor, req_pendente_gestor, req_unidade_b):
    """
    Gestor da unidade A ve APENAS requisicoes PENDENTE_GESTOR da unidade A.
    Requisicao da unidade B NAO aparece. (APROV-01, D-05)
    """
    client.force_login(gestor)
    response = client.get("/aprovacoes/fila/")

    assert response.status_code == 200
    requisicoes = list(response.context["requisicoes"])
    assert req_pendente_gestor in requisicoes
    assert req_unidade_b not in requisicoes


@pytest.mark.django_db
def test_fila_gestor_sem_default_unit(client, gestor_sem_unidade, req_pendente_gestor):
    """
    Gestor com default_unit=None recebe queryset vazio — sem vazamento de outras unidades.
    (Armadilha 3, D-05)
    """
    client.force_login(gestor_sem_unidade)
    response = client.get("/aprovacoes/fila/")

    assert response.status_code == 200
    assert list(response.context["requisicoes"]) == []


@pytest.mark.django_db
def test_fila_gestor_so_pendente_gestor(client, gestor, req_pendente_gestor, req_aprovada):
    """
    Requisicoes com status diferente de PENDENTE_GESTOR NAO aparecem na fila.
    """
    client.force_login(gestor)
    response = client.get("/aprovacoes/fila/")

    assert response.status_code == 200
    requisicoes = list(response.context["requisicoes"])
    assert req_pendente_gestor in requisicoes
    assert req_aprovada not in requisicoes


@pytest.mark.django_db
def test_solicitante_nao_acessa_fila(client, solicitante):
    """
    Solicitante recebe 403 ao tentar acessar a fila do Gestor. (T-03-02, Spoofing/EoP)
    """
    client.force_login(solicitante)
    response = client.get("/aprovacoes/fila/")

    assert response.status_code == 403


# ─────────────────────────────────────────────
# Testes de AprovarGestorView
# ─────────────────────────────────────────────


@pytest.mark.django_db
def test_aprovar_gestor_baixo_valor(client, gestor, req_pendente_gestor, config_alcada):
    """
    POST aprovar com valor < alcada -> status APROVADO (D-09).
    """
    client.force_login(gestor)
    response = client.post(f"/aprovacoes/{req_pendente_gestor.pk}/aprovar/")

    assert response.status_code == 200
    req_pendente_gestor.refresh_from_db()
    assert req_pendente_gestor.status == Requisicao.Status.APROVADO


@pytest.mark.django_db
def test_aprovar_gestor_alto_valor(
    client, gestor, req_pendente_gestor_alto_valor, config_alcada
):
    """
    POST aprovar com valor >= alcada -> status PENDENTE_DIRETOR (D-09).
    """
    client.force_login(gestor)
    response = client.post(f"/aprovacoes/{req_pendente_gestor_alto_valor.pk}/aprovar/")

    assert response.status_code == 200
    req_pendente_gestor_alto_valor.refresh_from_db()
    assert req_pendente_gestor_alto_valor.status == Requisicao.Status.PENDENTE_DIRETOR


@pytest.mark.django_db
def test_aprovar_estado_invalido_409(client, gestor, req_aprovada):
    """
    POST aprovar em requisicao ja APROVADO -> 409 (Armadilha 4, T-03-04).
    """
    client.force_login(gestor)
    response = client.post(f"/aprovacoes/{req_aprovada.pk}/aprovar/")

    assert response.status_code == 409


# ─────────────────────────────────────────────
# Testes de ModalReprovarView e ReprovarGestorView
# ─────────────────────────────────────────────


@pytest.mark.django_db
def test_modal_reprovar_get(client, gestor, req_pendente_gestor):
    """
    GET modal-reprovar retorna 200 com textarea motivo. (APROV-05)
    """
    client.force_login(gestor)
    response = client.get(f"/aprovacoes/{req_pendente_gestor.pk}/modal-reprovar/")

    assert response.status_code == 200
    content = response.content.decode()
    assert "motivo" in content
    assert "textarea" in content.lower()


@pytest.mark.django_db
def test_reprovar_sem_motivo_rejeitado(client, gestor, req_pendente_gestor):
    """
    POST reprovar sem motivo (string vazia) -> NAO transiciona, retorna erros. (APROV-05, T-03-03)
    """
    client.force_login(gestor)
    response = client.post(
        f"/aprovacoes/{req_pendente_gestor.pk}/reprovar/",
        {"motivo": ""},
    )

    # Status 422 retorna o modal com erros — sem transicionar (WR-02: HX-Retarget)
    assert response.status_code == 422
    req_pendente_gestor.refresh_from_db()
    assert req_pendente_gestor.status == Requisicao.Status.PENDENTE_GESTOR


@pytest.mark.django_db
def test_reprovar_com_motivo(client, gestor, req_pendente_gestor):
    """
    POST reprovar com motivo valido -> status REPROVADO + AprovacaoLog com motivo. (APROV-02, APROV-05)
    """
    client.force_login(gestor)
    response = client.post(
        f"/aprovacoes/{req_pendente_gestor.pk}/reprovar/",
        {"motivo": "Orcamento insuficiente para este periodo."},
    )

    assert response.status_code == 200
    req_pendente_gestor.refresh_from_db()
    assert req_pendente_gestor.status == Requisicao.Status.REPROVADO

    log = AprovacaoLog.objects.filter(
        requisicao=req_pendente_gestor,
        evento=AprovacaoLog.Evento.REPROVACAO,
    ).first()
    assert log is not None
    assert "Orcamento insuficiente" in log.motivo
