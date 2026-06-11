"""
Testes dos modelos de estoque: UnidadeMedida e ItemEstoque.

Cobre:
  EST-01 — cadastro de item
  EST-02 — quantidade mínima
  EST-04 — abaixo_do_minimo property
  EST-05 — UniqueConstraint por unidade
"""
import pytest
from django.db import IntegrityError

from apps.estoque.models import ItemEstoque, UnidadeMedida


@pytest.mark.django_db
class TestUnidadeMedida:
    def test_str_retorna_nome_e_sigla(self, db):
        um = UnidadeMedida.objects.create(nome="Unidade", sigla="UN")
        assert str(um) == "Unidade (UN)"


@pytest.mark.django_db
class TestItemEstoqueAbaixoDoMinimo:
    def test_abaixo_do_minimo_true(self, item_estoque, test_unit, unidade_medida):
        item = ItemEstoque.objects.create(
            nome="ItemBaixo",
            quantidade_atual=5,
            quantidade_minima=10,
            unidade_organizacional=test_unit,
            unidade_medida=unidade_medida,
        )
        assert item.abaixo_do_minimo is True

    def test_abaixo_do_minimo_false_igual(self, test_unit, unidade_medida):
        item = ItemEstoque.objects.create(
            nome="ItemExato",
            quantidade_atual=10,
            quantidade_minima=10,
            unidade_organizacional=test_unit,
            unidade_medida=unidade_medida,
        )
        assert item.abaixo_do_minimo is False

    def test_abaixo_do_minimo_false_acima(self, test_unit, unidade_medida):
        item = ItemEstoque.objects.create(
            nome="ItemAcima",
            quantidade_atual=11,
            quantidade_minima=10,
            unidade_organizacional=test_unit,
            unidade_medida=unidade_medida,
        )
        assert item.abaixo_do_minimo is False


@pytest.mark.django_db
class TestItemEstoqueUniqueConstraint:
    def test_unique_constraint_mesma_unidade(self, test_unit, unidade_medida):
        """Dois itens com mesmo nome na mesma unidade levantam IntegrityError."""
        ItemEstoque.objects.create(
            nome="Item Duplicado",
            quantidade_atual=5,
            quantidade_minima=1,
            unidade_organizacional=test_unit,
            unidade_medida=unidade_medida,
        )
        with pytest.raises(IntegrityError):
            ItemEstoque.objects.create(
                nome="Item Duplicado",
                quantidade_atual=3,
                quantidade_minima=1,
                unidade_organizacional=test_unit,
                unidade_medida=unidade_medida,
            )

    def test_unique_constraint_unidade_diferente(self, test_unit, outra_unit, unidade_medida):
        """Mesmo nome em unidades diferentes é permitido."""
        ItemEstoque.objects.create(
            nome="Item Compartilhado",
            quantidade_atual=5,
            quantidade_minima=1,
            unidade_organizacional=test_unit,
            unidade_medida=unidade_medida,
        )
        # Não deve levantar exceção
        item2 = ItemEstoque.objects.create(
            nome="Item Compartilhado",
            quantidade_atual=3,
            quantidade_minima=1,
            unidade_organizacional=outra_unit,
            unidade_medida=unidade_medida,
        )
        assert item2.pk is not None

    def test_str_inclui_nome_e_unidade(self, item_estoque, test_unit):
        assert "Papel A4" in str(item_estoque)
        assert test_unit.nome in str(item_estoque)
