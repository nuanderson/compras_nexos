"""
Testes para _notificar_gestores: envio de e-mail transacional aos Gestores da unidade.

Cobre: REQ-04, D-07 (falha silenciosa), D-16 (filtro de unidade e is_active).
"""
from decimal import Decimal

import pytest
from django.core import mail
from django.test import override_settings

from apps.accounts.models import UnidadeOrganizacional, User
from apps.aprovacoes.services import _notificar_gestores
from apps.requisicoes.models import CategoriaCompra, Requisicao


@pytest.fixture
def unidade_a(db):
    return UnidadeOrganizacional.objects.create(
        nome="Unidade A Email", ativo=True
    )


@pytest.fixture
def unidade_b(db):
    return UnidadeOrganizacional.objects.create(
        nome="Unidade B Email", ativo=True
    )


@pytest.fixture
def categoria_email(db):
    return CategoriaCompra.objects.create(nome="Suprimentos Email Test", ativo=True)


@pytest.fixture
def solicitante_email(db, unidade_a):
    return User.objects.create_user(
        username="solicitante_email_test",
        email="solicitante_email@test.com",
        password="testpass123",
        role=User.Role.SOLICITANTE,
        default_unit=unidade_a,
        first_name="Carlos",
        last_name="Lima",
    )


@pytest.fixture
def gestor_a1(db, unidade_a):
    return User.objects.create_user(
        username="gestor_a1",
        email="gestor_a1@test.com",
        password="testpass123",
        role=User.Role.GESTOR,
        default_unit=unidade_a,
        is_active=True,
    )


@pytest.fixture
def gestor_a2(db, unidade_a):
    return User.objects.create_user(
        username="gestor_a2",
        email="gestor_a2@test.com",
        password="testpass123",
        role=User.Role.GESTOR,
        default_unit=unidade_a,
        is_active=True,
    )


@pytest.fixture
def gestor_b(db, unidade_b):
    return User.objects.create_user(
        username="gestor_b",
        email="gestor_b@test.com",
        password="testpass123",
        role=User.Role.GESTOR,
        default_unit=unidade_b,
        is_active=True,
    )


@pytest.fixture
def gestor_a_inativo(db, unidade_a):
    return User.objects.create_user(
        username="gestor_a_inativo",
        email="gestor_a_inativo@test.com",
        password="testpass123",
        role=User.Role.GESTOR,
        default_unit=unidade_a,
        is_active=False,
    )


@pytest.fixture
def requisicao_pendente_email(db, solicitante_email, categoria_email, unidade_a):
    return Requisicao.objects.create(
        descricao="Papel sulfite para impressora",
        categoria=categoria_email,
        valor_estimado=Decimal("350.00"),
        justificativa="Estoque zerado",
        unidade=unidade_a,
        status=Requisicao.Status.PENDENTE_GESTOR,
        criado_por=solicitante_email,
    )


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
@pytest.mark.django_db
def test_email_enviado_aos_gestores_da_unidade(
    requisicao_pendente_email, gestor_a1, gestor_a2
):
    """
    Dois Gestores ativos na unidade A devem receber o e-mail.
    Apenas 1 mensagem e enviada (via send_mail com recipient_list contendo ambos).
    REQ-04, D-07.
    """
    _notificar_gestores(requisicao_pendente_email.pk)

    assert len(mail.outbox) == 1
    mensagem = mail.outbox[0]
    assert "gestor_a1@test.com" in mensagem.recipients()
    assert "gestor_a2@test.com" in mensagem.recipients()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
@pytest.mark.django_db
def test_email_apenas_gestores_da_unidade(
    requisicao_pendente_email, gestor_a1, gestor_b
):
    """
    Gestor da unidade B NAO deve receber e-mail de requisicao da unidade A (D-05, T-03-05).
    """
    _notificar_gestores(requisicao_pendente_email.pk)

    assert len(mail.outbox) == 1
    mensagem = mail.outbox[0]
    assert "gestor_b@test.com" not in mensagem.recipients()
    assert "gestor_a1@test.com" in mensagem.recipients()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
@pytest.mark.django_db
def test_email_ignora_gestor_inativo(
    requisicao_pendente_email, gestor_a1, gestor_a_inativo
):
    """
    Gestor com is_active=False NAO deve estar na lista de destinatarios (D-16).
    """
    _notificar_gestores(requisicao_pendente_email.pk)

    assert len(mail.outbox) == 1
    mensagem = mail.outbox[0]
    assert "gestor_a_inativo@test.com" not in mensagem.recipients()
    assert "gestor_a1@test.com" in mensagem.recipients()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
@pytest.mark.django_db
def test_sem_gestores_nao_envia(requisicao_pendente_email):
    """
    Sem gestores ativos na unidade: mail.outbox vazio, sem excecao (D-07 - falha silenciosa).
    """
    _notificar_gestores(requisicao_pendente_email.pk)

    assert len(mail.outbox) == 0


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
@pytest.mark.django_db
def test_email_contem_dados_requisicao(requisicao_pendente_email, gestor_a1):
    """
    O assunto e o corpo devem conter a descricao e o valor estimado da requisicao.
    """
    _notificar_gestores(requisicao_pendente_email.pk)

    assert len(mail.outbox) == 1
    mensagem = mail.outbox[0]
    assert "Papel sulfite para impressora" in mensagem.subject
    assert "Papel sulfite para impressora" in mensagem.body
    assert "350" in mensagem.body
