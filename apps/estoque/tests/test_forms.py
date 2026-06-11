"""
Testes dos formulários de estoque.

Cobre:
  EST-01 — campos obrigatórios de ItemEstoqueForm
  EST-03 — validação de quantidade em AtualizarQuantidadeForm
"""
import pytest

from apps.estoque.forms import AtualizarQuantidadeForm, ItemEstoqueForm


@pytest.mark.django_db
class TestAtualizarQuantidadeForm:
    def test_quantidade_negativa_invalida(self, item_estoque):
        form = AtualizarQuantidadeForm(
            data={"quantidade_atual": -1},
            instance=item_estoque,
        )
        assert not form.is_valid()
        assert "quantidade_atual" in form.errors

    def test_quantidade_zero_valida(self, item_estoque):
        form = AtualizarQuantidadeForm(
            data={"quantidade_atual": 0},
            instance=item_estoque,
        )
        assert form.is_valid()

    def test_quantidade_positiva_valida(self, item_estoque):
        form = AtualizarQuantidadeForm(
            data={"quantidade_atual": 100},
            instance=item_estoque,
        )
        assert form.is_valid()


@pytest.mark.django_db
class TestItemEstoqueForm:
    def test_campos_obrigatorios_nome_ausente(self, unidade_medida):
        form = ItemEstoqueForm(
            data={
                "nome": "",
                "unidade_medida": unidade_medida.pk,
                "quantidade_atual": 10,
                "quantidade_minima": 5,
            }
        )
        assert not form.is_valid()
        assert "nome" in form.errors

    def test_campos_obrigatorios_unidade_medida_ausente(self):
        form = ItemEstoqueForm(
            data={
                "nome": "Papel A4",
                "unidade_medida": "",
                "quantidade_atual": 10,
                "quantidade_minima": 5,
            }
        )
        assert not form.is_valid()
        assert "unidade_medida" in form.errors

    def test_form_valido_com_todos_campos(self, unidade_medida):
        form = ItemEstoqueForm(
            data={
                "nome": "Papel A4",
                "unidade_medida": unidade_medida.pk,
                "quantidade_atual": 10,
                "quantidade_minima": 5,
            }
        )
        assert form.is_valid()
