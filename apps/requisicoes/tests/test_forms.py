"""
Testes para RequisicaoForm (apps/requisicoes/forms.py).
"""
from decimal import Decimal

import pytest

from apps.requisicoes.forms import RequisicaoForm


@pytest.mark.django_db
class TestRequisicaoForm:
    def test_form_campos_obrigatorios(self, categoria, test_unit):
        """
        RequisicaoForm inválido sem descricao/categoria/valor_estimado/justificativa/unidade. (REQ-01)
        """
        form = RequisicaoForm(data={})
        assert not form.is_valid()
        assert "descricao" in form.errors
        assert "categoria" in form.errors
        assert "valor_estimado" in form.errors
        assert "justificativa" in form.errors
        assert "unidade" in form.errors

    def test_form_valido(self, categoria, test_unit):
        """RequisicaoForm com todos os campos é válido."""
        form = RequisicaoForm(
            data={
                "descricao": "Papel A4 para impressão",
                "categoria": categoria.pk,
                "valor_estimado": "500.00",
                "justificativa": "Estoque zerado, necessidade imediata",
                "unidade": test_unit.pk,
            }
        )
        assert form.is_valid(), form.errors

    def test_form_categoria_inativa_invalida(self, test_unit, db):
        """Categoria inativa não deve aparecer no queryset do form."""
        from apps.requisicoes.models import CategoriaCompra

        cat_inativa = CategoriaCompra.objects.create(
            nome="Categoria Inativa", ativo=False
        )
        form = RequisicaoForm(
            data={
                "descricao": "Teste",
                "categoria": cat_inativa.pk,
                "valor_estimado": "100.00",
                "justificativa": "Teste",
                "unidade": test_unit.pk,
            }
        )
        assert not form.is_valid()
        assert "categoria" in form.errors

    def test_form_preenche_default_unit(self, solicitante_user, categoria, test_unit):
        """
        Se user.default_unit existir, o campo unidade tem initial = default_unit. (UNIT-03)
        """
        form = RequisicaoForm(user=solicitante_user)
        assert form.fields["unidade"].initial == solicitante_user.default_unit

    def test_form_sem_default_unit_sem_initial(self, db):
        """Se user não tem default_unit, sem initial no campo unidade."""
        from apps.accounts.models import User

        user_sem_unidade = User.objects.create_user(
            username="s_unid",
            email="s@s.com",
            password="testpass123",
            role=User.Role.SOLICITANTE,
        )
        form = RequisicaoForm(user=user_sem_unidade)
        # No initial (None or falsy)
        assert not form.fields["unidade"].initial
