"""
Testes para as views do Solicitante (apps/requisicoes/views.py).

Cobre: lista, criar/editar rascunho, detalhe, enviar, cancelar, status partial, copiar dados.
"""
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.test import Client
from django.urls import reverse

from apps.aprovacoes.models import AprovacaoLog
from apps.requisicoes.models import Requisicao


@pytest.mark.django_db
class TestRequisicaoListView:
    def test_lista_apenas_proprias(
        self, client, solicitante_user, outro_solicitante, requisicao_rascunho, categoria, test_unit
    ):
        """RequisicaoListView mostra apenas requisições onde criado_por==request.user (REQ-01)."""
        from apps.requisicoes.models import Requisicao as Req

        # Criar requisição de outro solicitante
        Req.objects.create(
            descricao="De outro solicitante",
            categoria=categoria,
            valor_estimado=Decimal("100.00"),
            justificativa="Outro",
            unidade=test_unit,
            status=Req.Status.RASCUNHO,
            criado_por=outro_solicitante,
        )

        client.force_login(solicitante_user)
        resp = client.get(reverse("requisicoes:lista"))
        assert resp.status_code == 200
        qs = resp.context["requisicoes"]
        # Somente requisições do solicitante logado
        for req in qs:
            assert req.criado_por == solicitante_user

    def test_lista_requer_autenticacao(self, client):
        """Lista redireciona usuário não autenticado."""
        resp = client.get(reverse("requisicoes:lista"))
        assert resp.status_code == 302


@pytest.mark.django_db
class TestRequisicaoCreateView:
    def test_criar_rascunho(self, client, solicitante_user, categoria, test_unit):
        """
        POST /requisicoes/nova/ cria Requisicao status=RASCUNHO com criado_por=usuário logado.
        NÃO submete automaticamente. (D-12)
        """
        client.force_login(solicitante_user)
        count_antes = Requisicao.objects.count()
        resp = client.post(
            reverse("requisicoes:nova"),
            data={
                "descricao": "Nova requisição de teste",
                "categoria": categoria.pk,
                "valor_estimado": "300.00",
                "justificativa": "Necessidade urgente",
                "unidade": test_unit.pk,
            },
        )
        # Deve redirecionar após sucesso
        assert resp.status_code in (302, 200)
        assert Requisicao.objects.count() == count_antes + 1

        nova_req = Requisicao.objects.latest("criado_em")
        assert nova_req.status == Requisicao.Status.RASCUNHO
        assert nova_req.criado_por == solicitante_user

    def test_criar_nao_submete_automaticamente(
        self, client, solicitante_user, categoria, test_unit
    ):
        """
        POST para /nova/ NÃO chama submeter_requisicao — fica em RASCUNHO. (D-12)
        """
        client.force_login(solicitante_user)
        count_logs_antes = AprovacaoLog.objects.count()
        client.post(
            reverse("requisicoes:nova"),
            data={
                "descricao": "Teste não-envio",
                "categoria": categoria.pk,
                "valor_estimado": "100.00",
                "justificativa": "Teste",
                "unidade": test_unit.pk,
            },
        )
        # Nenhum AprovacaoLog criado (ENVIO seria criado ao submeter)
        assert AprovacaoLog.objects.count() == count_logs_antes

    def test_get_nova_retorna_200(self, client, solicitante_user):
        """GET /requisicoes/nova/ retorna 200 para Solicitante."""
        client.force_login(solicitante_user)
        resp = client.get(reverse("requisicoes:nova"))
        assert resp.status_code == 200


@pytest.mark.django_db
class TestRequisicaoDetailView:
    def test_detalhe_mostra_status_e_historico(
        self, client, solicitante_user, requisicao_rascunho
    ):
        """GET /requisicoes/<pk>/ retorna 200 com requisicao e logs no contexto."""
        client.force_login(solicitante_user)
        resp = client.get(
            reverse("requisicoes:detalhe", kwargs={"pk": requisicao_rascunho.pk})
        )
        assert resp.status_code == 200
        assert "requisicao" in resp.context
        assert "logs" in resp.context

    def test_detalhe_nao_dono_negado(
        self, client, outro_solicitante, requisicao_rascunho
    ):
        """GET detalhe de requisição de outro Solicitante retorna 403. (T-02-04)"""
        client.force_login(outro_solicitante)
        resp = client.get(
            reverse("requisicoes:detalhe", kwargs={"pk": requisicao_rascunho.pk})
        )
        assert resp.status_code == 403

    def test_detalhe_admin_ve_qualquer(self, client, admin_user, requisicao_rascunho):
        """Admin pode ver detalhe de qualquer requisição."""
        client.force_login(admin_user)
        resp = client.get(
            reverse("requisicoes:detalhe", kwargs={"pk": requisicao_rascunho.pk})
        )
        assert resp.status_code == 200


@pytest.mark.django_db
class TestRequisicaoEnviarView:
    def test_enviar_transiciona(self, client, solicitante_user, requisicao_rascunho):
        """
        POST /requisicoes/<pk>/enviar/ chama services.submeter_requisicao
        → status PENDENTE_GESTOR. (REQ-03)
        """
        client.force_login(solicitante_user)
        resp = client.post(
            reverse("requisicoes:enviar", kwargs={"pk": requisicao_rascunho.pk})
        )
        assert resp.status_code in (302, 200)

        requisicao_rascunho.refresh_from_db()
        assert requisicao_rascunho.status == Requisicao.Status.PENDENTE_GESTOR

    def test_enviar_estado_invalido_retorna_409(
        self, client, solicitante_user, requisicao_pendente_gestor
    ):
        """POST enviar em PENDENTE_GESTOR retorna 409 (já submetido)."""
        client.force_login(solicitante_user)
        resp = client.post(
            reverse("requisicoes:enviar", kwargs={"pk": requisicao_pendente_gestor.pk})
        )
        assert resp.status_code == 409


@pytest.mark.django_db
class TestRequisicaoCancelarView:
    def test_cancelar_rascunho(self, client, solicitante_user, requisicao_rascunho):
        """POST /requisicoes/<pk>/cancelar/ em RASCUNHO → CANCELADO. (D-15)"""
        client.force_login(solicitante_user)
        resp = client.post(
            reverse("requisicoes:cancelar", kwargs={"pk": requisicao_rascunho.pk})
        )
        assert resp.status_code in (200, 302)

        requisicao_rascunho.refresh_from_db()
        assert requisicao_rascunho.status == Requisicao.Status.CANCELADO

    def test_cancelar_pendente_diretor_retorna_409(
        self, client, solicitante_user, requisicao_pendente_diretor
    ):
        """POST cancelar em PENDENTE_DIRETOR retorna 409. (D-15)"""
        client.force_login(solicitante_user)
        resp = client.post(
            reverse(
                "requisicoes:cancelar",
                kwargs={"pk": requisicao_pendente_diretor.pk},
            )
        )
        assert resp.status_code == 409


@pytest.mark.django_db
class TestStatusBadgeView:
    def test_status_partial(self, client, solicitante_user, requisicao_rascunho):
        """GET /requisicoes/<pk>/status/ retorna partial do badge com 200."""
        client.force_login(solicitante_user)
        resp = client.get(
            reverse("requisicoes:status", kwargs={"pk": requisicao_rascunho.pk})
        )
        assert resp.status_code == 200


@pytest.mark.django_db
class TestCopiarDadosView:
    def test_copiar_dados(self, client, solicitante_user, requisicao_rascunho):
        """
        GET /requisicoes/copiar-dados/?requisicao_origem=<pk> retorna campos pré-preenchidos
        da requisição do próprio Solicitante. (D-14)
        """
        client.force_login(solicitante_user)
        resp = client.get(
            reverse("requisicoes:copiar-dados"),
            data={"requisicao_origem": requisicao_rascunho.pk},
        )
        assert resp.status_code == 200

    def test_copiar_dados_nao_proprio_retorna_404(
        self, client, outro_solicitante, requisicao_rascunho
    ):
        """
        GET copiar-dados com requisição de outro Solicitante retorna 404. (T-02-04)
        """
        client.force_login(outro_solicitante)
        resp = client.get(
            reverse("requisicoes:copiar-dados"),
            data={"requisicao_origem": requisicao_rascunho.pk},
        )
        assert resp.status_code == 404

    def test_copiar_dados_sem_origem_retorna_200(self, client, solicitante_user):
        """GET copiar-dados sem requisicao_origem retorna 200 com form vazio."""
        client.force_login(solicitante_user)
        resp = client.get(reverse("requisicoes:copiar-dados"))
        assert resp.status_code == 200
