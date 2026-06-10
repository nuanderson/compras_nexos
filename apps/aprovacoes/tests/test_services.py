"""
Testes para a camada de serviço de aprovações (apps/aprovacoes/services.py).

Cobre todas as transições de estado da máquina de estados:
  - submeter_requisicao (RASCUNHO → PENDENTE_GESTOR)
  - aprovar_gestor (PENDENTE_GESTOR → APROVADO ou PENDENTE_DIRETOR)
  - aprovar_diretor (PENDENTE_DIRETOR → APROVADO)
  - reprovar_requisicao (PENDENTE_GESTOR/PENDENTE_DIRETOR → REPROVADO)
  - cancelar_requisicao (RASCUNHO/PENDENTE_GESTOR → CANCELADO)
  - _notificar_gestores (implementacao real com send_mail, cobertura completa em test_email.py)
"""
import logging
from decimal import Decimal

import pytest

from apps.aprovacoes.models import AprovacaoLog, ConfiguracaoAlcada
from apps.aprovacoes import services
from apps.requisicoes.models import Requisicao


@pytest.mark.django_db
class TestSubmeterRequisicao:
    def test_submeter_rascunho(self, requisicao_rascunho, solicitante_user):
        """RASCUNHO → PENDENTE_GESTOR; cria AprovacaoLog(evento=ENVIO)."""
        req = services.submeter_requisicao(requisicao_rascunho.pk, solicitante_user)

        req.refresh_from_db()
        assert req.status == Requisicao.Status.PENDENTE_GESTOR

        log = AprovacaoLog.objects.get(requisicao=req, evento=AprovacaoLog.Evento.ENVIO)
        assert log.aprovador == solicitante_user

    def test_submeter_estado_invalido(self, requisicao_pendente_gestor, solicitante_user):
        """Submeter requisição já em PENDENTE_GESTOR levanta ValueError."""
        with pytest.raises(ValueError, match="não pode ser submetida"):
            services.submeter_requisicao(requisicao_pendente_gestor.pk, solicitante_user)

    def test_submeter_nao_dono(self, requisicao_rascunho, outro_solicitante):
        """Outro usuário (não criado_por) levanta PermissionError."""
        with pytest.raises(PermissionError):
            services.submeter_requisicao(requisicao_rascunho.pk, outro_solicitante)


@pytest.mark.django_db
class TestAprovarGestor:
    def test_aprovar_gestor_baixo_valor(
        self, requisicao_pendente_gestor, gestor_user, config_alcada
    ):
        """
        ConfiguracaoAlcada com valor_maximo_gestor=1000, valor_estimado=500
        → status APROVADO, AprovacaoLog(evento=APROVACAO_FINAL). (D-09)
        """
        req = services.aprovar_gestor(requisicao_pendente_gestor.pk, gestor_user)

        req.refresh_from_db()
        assert req.status == Requisicao.Status.APROVADO

        log = AprovacaoLog.objects.get(
            requisicao=req, evento=AprovacaoLog.Evento.APROVACAO_FINAL
        )
        assert log.aprovador == gestor_user

    def test_aprovar_gestor_alto_valor(
        self, requisicao_pendente_gestor_alto_valor, gestor_user, config_alcada
    ):
        """
        valor_maximo_gestor=1000, valor_estimado=5000
        → status PENDENTE_DIRETOR, AprovacaoLog(evento=APROVACAO_GESTOR). (D-09)
        """
        req = services.aprovar_gestor(
            requisicao_pendente_gestor_alto_valor.pk, gestor_user
        )

        req.refresh_from_db()
        assert req.status == Requisicao.Status.PENDENTE_DIRETOR

        log = AprovacaoLog.objects.get(
            requisicao=req, evento=AprovacaoLog.Evento.APROVACAO_GESTOR
        )
        assert log.aprovador == gestor_user

    def test_alcada_nula_exige_diretor(
        self, requisicao_pendente_gestor, gestor_user
    ):
        """
        valor_maximo_gestor=None, qualquer valor → PENDENTE_DIRETOR (fail-safe D-10).
        Não cria config_alcada — obter() cria com valor_maximo_gestor=None.
        """
        # Garantir que a config existe com valor_maximo_gestor=None
        config, _ = ConfiguracaoAlcada.objects.get_or_create(pk=1)
        config.valor_maximo_gestor = None
        config.save()

        req = services.aprovar_gestor(requisicao_pendente_gestor.pk, gestor_user)

        req.refresh_from_db()
        assert req.status == Requisicao.Status.PENDENTE_DIRETOR


@pytest.mark.django_db
class TestAprovarDiretor:
    def test_aprovar_diretor(self, requisicao_pendente_diretor, diretor_user):
        """PENDENTE_DIRETOR → APROVADO, AprovacaoLog(evento=APROVACAO_FINAL). (APROV-04)"""
        req = services.aprovar_diretor(requisicao_pendente_diretor.pk, diretor_user)

        req.refresh_from_db()
        assert req.status == Requisicao.Status.APROVADO

        log = AprovacaoLog.objects.get(
            requisicao=req, evento=AprovacaoLog.Evento.APROVACAO_FINAL
        )
        assert log.aprovador == diretor_user


@pytest.mark.django_db
class TestReprovarRequisicao:
    def test_reprovar_sem_motivo(self, requisicao_pendente_gestor, gestor_user):
        """Motivo vazio ou só espaços → ValueError, estado inalterado. (APROV-05)"""
        status_antes = requisicao_pendente_gestor.status

        with pytest.raises(ValueError, match="Motivo é obrigatório"):
            services.reprovar_requisicao(
                requisicao_pendente_gestor.pk, gestor_user, motivo=""
            )

        requisicao_pendente_gestor.refresh_from_db()
        assert requisicao_pendente_gestor.status == status_antes

    def test_reprovar_motivo_apenas_espacos(self, requisicao_pendente_gestor, gestor_user):
        """Motivo com apenas espaços → ValueError. (APROV-05)"""
        with pytest.raises(ValueError, match="Motivo é obrigatório"):
            services.reprovar_requisicao(
                requisicao_pendente_gestor.pk, gestor_user, motivo="   "
            )

    def test_reprovar_com_motivo(self, requisicao_pendente_gestor, gestor_user):
        """
        PENDENTE_GESTOR + motivo → REPROVADO, AprovacaoLog(evento=REPROVACAO, motivo=...).
        (APROV-02, APROV-05)
        """
        motivo = "Valor acima do orçamento aprovado"
        req = services.reprovar_requisicao(
            requisicao_pendente_gestor.pk, gestor_user, motivo=motivo
        )

        req.refresh_from_db()
        assert req.status == Requisicao.Status.REPROVADO

        log = AprovacaoLog.objects.get(
            requisicao=req, evento=AprovacaoLog.Evento.REPROVACAO
        )
        assert log.motivo == motivo
        assert log.aprovador == gestor_user

    def test_reprovar_diretor(self, requisicao_pendente_diretor, diretor_user):
        """PENDENTE_DIRETOR + motivo → REPROVADO. (APROV-04, APROV-05)"""
        req = services.reprovar_requisicao(
            requisicao_pendente_diretor.pk,
            diretor_user,
            motivo="Não está alinhado ao planejamento orçamentário",
        )

        req.refresh_from_db()
        assert req.status == Requisicao.Status.REPROVADO


@pytest.mark.django_db
class TestCancelarRequisicao:
    def test_cancelar_rascunho(self, requisicao_rascunho, solicitante_user):
        """RASCUNHO → CANCELADO, AprovacaoLog(evento=CANCELAMENTO). (D-15)"""
        req = services.cancelar_requisicao(requisicao_rascunho.pk, solicitante_user)

        req.refresh_from_db()
        assert req.status == Requisicao.Status.CANCELADO

        log = AprovacaoLog.objects.get(
            requisicao=req, evento=AprovacaoLog.Evento.CANCELAMENTO
        )
        assert log.aprovador == solicitante_user

    def test_cancelar_pendente_gestor(
        self, requisicao_pendente_gestor, solicitante_user
    ):
        """PENDENTE_GESTOR → CANCELADO. (D-15)"""
        req = services.cancelar_requisicao(
            requisicao_pendente_gestor.pk, solicitante_user
        )

        req.refresh_from_db()
        assert req.status == Requisicao.Status.CANCELADO

    def test_cancelar_pendente_diretor_bloqueado(
        self, requisicao_pendente_diretor, solicitante_user
    ):
        """PENDENTE_DIRETOR → ValueError, estado inalterado. (D-15)"""
        status_antes = requisicao_pendente_diretor.status

        with pytest.raises(ValueError):
            services.cancelar_requisicao(
                requisicao_pendente_diretor.pk, solicitante_user
            )

        requisicao_pendente_diretor.refresh_from_db()
        assert requisicao_pendente_diretor.status == status_antes


@pytest.mark.django_db
class TestLogCriadoEmCadaTransicao:
    def test_log_criado_em_cada_transicao(
        self,
        requisicao_rascunho,
        solicitante_user,
        gestor_user,
        diretor_user,
        config_alcada,
    ):
        """
        Cada transição bem-sucedida incrementa AprovacaoLog.objects.count() em 1. (REQ-03)
        """
        count_inicial = AprovacaoLog.objects.count()

        # 1. Submeter
        req = services.submeter_requisicao(requisicao_rascunho.pk, solicitante_user)
        assert AprovacaoLog.objects.count() == count_inicial + 1

        # 2. Aprovar gestor (valor baixo → APROVADO direto)
        services.aprovar_gestor(req.pk, gestor_user)
        assert AprovacaoLog.objects.count() == count_inicial + 2


@pytest.mark.django_db
class TestNotificarGestoresStub:
    def test_notificar_gestores_pk_inexistente_nao_levanta_excecao(self):
        """
        Chamar _notificar_gestores com pk inexistente NAO levanta excecao (falha silenciosa D-07).
        A implementacao real retorna silenciosamente quando Requisicao.DoesNotExist.
        """
        # Nao deve levantar nenhuma excecao — comportamento de falha silenciosa
        services._notificar_gestores(99999)  # pk inexistente
