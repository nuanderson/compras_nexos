"""
Testes das views do app estoque.

Cobre:
  EST-01 — cadastro de item vinculado à unidade do usuário
  EST-03 — atualização de quantidade
  EST-05 — isolamento de unidade (IDOR guard)
  EST-06 — visão consolidada comprador/admin
  T-03-05 — get_object_or_404 com filtro unidade_organizacional
  T-03-06 — PermissionDenied em visão consolidada para Solicitante
  T-03-07 — select_for_update + transaction.atomic
  T-03-08 — validação quantidade negativa
  T-03-09 — unidade_organizacional atribuída pelo usuário, não pelo form
"""
import pytest
from django.urls import reverse

from apps.estoque.models import ItemEstoque


@pytest.mark.django_db
class TestListaEstoqueView:
    def test_lista_solicitante_ve_apenas_propria_unidade(
        self, client, solicitante_user, test_unit, outra_unit, item_estoque, unidade_medida
    ):
        """Solicitante vê item da própria unidade e não vê item de outra unidade."""
        # Criar item na outra unidade
        item_outra = ItemEstoque.objects.create(
            nome="Item Outra Unidade",
            quantidade_atual=10,
            quantidade_minima=5,
            unidade_organizacional=outra_unit,
            unidade_medida=unidade_medida,
        )
        client.force_login(solicitante_user)
        response = client.get(reverse("estoque:lista"))
        assert response.status_code == 200
        itens = list(response.context["itens"])
        nomes = [i.nome for i in itens]
        assert "Papel A4" in nomes
        assert "Item Outra Unidade" not in nomes

    def test_lista_comprador_ve_todas_unidades(
        self, client, comprador_user, test_unit, outra_unit, item_estoque, unidade_medida
    ):
        """Comprador vê itens de todas as unidades."""
        item_outra = ItemEstoque.objects.create(
            nome="Item Outra Unidade",
            quantidade_atual=10,
            quantidade_minima=5,
            unidade_organizacional=outra_unit,
            unidade_medida=unidade_medida,
        )
        client.force_login(comprador_user)
        response = client.get(reverse("estoque:lista"))
        assert response.status_code == 200
        itens = list(response.context["itens"])
        nomes = [i.nome for i in itens]
        assert "Papel A4" in nomes
        assert "Item Outra Unidade" in nomes

    def test_lista_requer_autenticacao(self, client):
        """Redireciona para login se não autenticado."""
        response = client.get(reverse("estoque:lista"))
        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"]


@pytest.mark.django_db
class TestIsolamentoIDOR:
    def test_isolamento_idor_solicitante_get_editar(
        self, client, solicitante_user, outra_unit, unidade_medida
    ):
        """Solicitante recebe 404 ao tentar editar item de outra unidade via pk URL. EST-05."""
        item_outra = ItemEstoque.objects.create(
            nome="Item Sigiloso",
            quantidade_atual=5,
            quantidade_minima=1,
            unidade_organizacional=outra_unit,
            unidade_medida=unidade_medida,
        )
        client.force_login(solicitante_user)
        url = reverse("estoque:editar", args=[item_outra.pk])
        response = client.get(url)
        assert response.status_code == 404

    def test_isolamento_idor_solicitante_atualizar_quantidade(
        self, client, solicitante_user, outra_unit, unidade_medida
    ):
        """Solicitante recebe 404 ao tentar atualizar quantidade de item de outra unidade. T-03-05."""
        item_outra = ItemEstoque.objects.create(
            nome="Item Sigiloso Qtd",
            quantidade_atual=5,
            quantidade_minima=1,
            unidade_organizacional=outra_unit,
            unidade_medida=unidade_medida,
        )
        client.force_login(solicitante_user)
        url = reverse("estoque:atualizar-quantidade", args=[item_outra.pk])
        response = client.post(url, {"quantidade_atual": 99})
        assert response.status_code == 404


@pytest.mark.django_db
class TestCadastrarItemEstoqueView:
    def test_cadastrar_get_retorna_form(self, client, solicitante_user):
        """GET em cadastrar retorna 200 com formulário."""
        client.force_login(solicitante_user)
        response = client.get(reverse("estoque:cadastrar"))
        assert response.status_code == 200

    def test_cadastrar_item_vincula_unidade_usuario(
        self, client, solicitante_user, test_unit, unidade_medida
    ):
        """POST cria item com unidade=request.user.default_unit (T-03-09)."""
        client.force_login(solicitante_user)
        response = client.post(
            reverse("estoque:cadastrar"),
            {
                "nome": "Novo Item Teste",
                "unidade_medida": unidade_medida.pk,
                "quantidade_atual": 10,
                "quantidade_minima": 5,
            },
        )
        assert response.status_code == 302  # redirect após sucesso
        item = ItemEstoque.objects.get(nome="Novo Item Teste")
        assert item.unidade_organizacional == test_unit


@pytest.mark.django_db
class TestAtualizarQuantidadeView:
    def test_atualizar_quantidade_sucesso(
        self, client, solicitante_user, item_estoque
    ):
        """POST atualiza quantidade_atual corretamente."""
        client.force_login(solicitante_user)
        url = reverse("estoque:atualizar-quantidade", args=[item_estoque.pk])
        response = client.post(url, {"quantidade_atual": 100})
        assert response.status_code == 200
        item_estoque.refresh_from_db()
        assert item_estoque.quantidade_atual == 100

    def test_atualizar_quantidade_negativa_invalida(
        self, client, solicitante_user, item_estoque
    ):
        """POST com quantidade negativa retorna status 422 com erro no form. T-03-08."""
        client.force_login(solicitante_user)
        url = reverse("estoque:atualizar-quantidade", args=[item_estoque.pk])
        response = client.post(url, {"quantidade_atual": -1})
        assert response.status_code == 422
        # Quantidade não deve ter sido alterada
        item_estoque.refresh_from_db()
        assert item_estoque.quantidade_atual == 50  # valor original da fixture


@pytest.mark.django_db
class TestVisaoConsolidadaView:
    def test_visao_consolidada_comprador_retorna_200(
        self, client, comprador_user, item_estoque
    ):
        """Comprador acessa visão consolidada com sucesso. EST-06."""
        client.force_login(comprador_user)
        response = client.get(reverse("estoque:consolidado"))
        assert response.status_code == 200

    def test_visao_consolidada_solicitante_403(
        self, client, solicitante_user
    ):
        """Solicitante recebe 403 ao tentar acessar visão consolidada. T-03-06."""
        client.force_login(solicitante_user)
        response = client.get(reverse("estoque:consolidado"))
        assert response.status_code == 403

    def test_visao_consolidada_ve_todas_unidades(
        self, client, comprador_user, test_unit, outra_unit, item_estoque, unidade_medida
    ):
        """Visão consolidada inclui itens de todas as unidades."""
        item_outra = ItemEstoque.objects.create(
            nome="Item Outra Consolidado",
            quantidade_atual=3,
            quantidade_minima=10,
            unidade_organizacional=outra_unit,
            unidade_medida=unidade_medida,
        )
        client.force_login(comprador_user)
        response = client.get(reverse("estoque:consolidado"))
        assert response.status_code == 200
        itens = list(response.context["itens"])
        nomes = [i.nome for i in itens]
        assert "Papel A4" in nomes
        assert "Item Outra Consolidado" in nomes
