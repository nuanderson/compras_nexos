"""
Testes das views do app fornecedores.

Cobre: FORN-01..05, T-03-01 (403), T-03-02 (405 em toggle GET).
"""
import pytest
from django.test import Client
from django.urls import reverse

from apps.fornecedores.models import Fornecedor
from apps.requisicoes.models import CategoriaCompra


@pytest.mark.django_db
class TestListaFornecedoresView:
    """FORN-05 — listagem e controle de acesso."""

    def test_lista_exige_comprador_403_para_solicitante(self, client, solicitante_user):
        """T-03-01 — Solicitante deve receber 403."""
        client.force_login(solicitante_user)
        url = reverse("fornecedores:lista")
        response = client.get(url)
        assert response.status_code == 403

    def test_lista_comprador_retorna_200(self, client, comprador_user):
        """Comprador deve receber 200 na listagem."""
        client.force_login(comprador_user)
        url = reverse("fornecedores:lista")
        response = client.get(url)
        assert response.status_code == 200

    def test_lista_sem_login_redireciona(self, client):
        """Sem autenticação deve redirecionar para login."""
        url = reverse("fornecedores:lista")
        response = client.get(url)
        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"]

    def test_busca_htmx_retorna_partial(self, client, comprador_user, fornecedor):
        """GET com HTMX deve retornar partial sem base.html."""
        client.force_login(comprador_user)
        url = reverse("fornecedores:lista")
        response = client.get(
            url,
            {"q": "Empresa"},
            HTTP_HX_REQUEST="true",
            HTTP_HX_TARGET="fornecedores-list",
        )
        assert response.status_code == 200
        # Partial não deve conter doctype ou html completo
        content = response.content.decode()
        assert "<!DOCTYPE" not in content.upper()

    def test_busca_vazia_retorna_lista_completa(self, client, comprador_user, fornecedor):
        """q="" não deve retornar 404 — retorna lista completa."""
        client.force_login(comprador_user)
        url = reverse("fornecedores:lista")
        response = client.get(url, {"q": ""})
        assert response.status_code == 200

    def test_busca_cnpj_exato(self, client, comprador_user, fornecedor):
        """q com CNPJ formatado deve encontrar o fornecedor pelo CNPJ compactado."""
        client.force_login(comprador_user)
        url = reverse("fornecedores:lista")
        response = client.get(
            url,
            {"q": "11.222.333/0001-81"},
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert "Empresa Teste Ltda" in content


@pytest.mark.django_db
class TestCadastrarFornecedorView:
    """FORN-01 — cadastro de fornecedor."""

    def test_cadastrar_fornecedor_valido_cria_e_redireciona(
        self, client, comprador_user, categoria
    ):
        """POST com CNPJ válido deve criar Fornecedor e redirecionar para lista."""
        client.force_login(comprador_user)
        url = reverse("fornecedores:cadastrar")
        data = {
            "cnpj": "07.526.557/0001-00",
            "razao_social": "Nova Empresa SA",
            "email": "nova@empresa.com",
            "telefone": "",
            "categoria": categoria.pk,
        }
        response = client.post(url, data)
        assert response.status_code == 302
        assert Fornecedor.objects.filter(cnpj="07526557000100").exists()

    def test_cadastrar_cnpj_duplicado_retorna_form_com_erro(
        self, client, comprador_user, fornecedor, categoria
    ):
        """POST com CNPJ já cadastrado deve retornar form com erro."""
        client.force_login(comprador_user)
        url = reverse("fornecedores:cadastrar")
        data = {
            "cnpj": "11.222.333/0001-81",  # CNPJ do fixture fornecedor
            "razao_social": "Empresa Duplicada Ltda",
            "email": "dupla@empresa.com",
            "telefone": "",
            "categoria": categoria.pk,
        }
        response = client.post(url, data)
        assert response.status_code == 200
        assert "Já existe" in response.content.decode()

    def test_cadastrar_exige_comprador_403_para_solicitante(
        self, client, solicitante_user
    ):
        """T-03-01 — Solicitante recebe 403 em POST para cadastrar."""
        client.force_login(solicitante_user)
        url = reverse("fornecedores:cadastrar")
        response = client.post(url, {})
        assert response.status_code == 403


@pytest.mark.django_db
class TestToggleAtivoView:
    """FORN-04 — toggle de ativo/inativo sem deleção."""

    def test_toggle_ativo_post_inverte_estado(self, client, comprador_user, fornecedor):
        """POST deve inverter ativo=True → False."""
        client.force_login(comprador_user)
        assert fornecedor.ativo is True
        url = reverse("fornecedores:toggle-ativo", args=[fornecedor.pk])
        response = client.post(url)
        assert response.status_code == 200
        fornecedor.refresh_from_db()
        assert fornecedor.ativo is False

    def test_toggle_ativo_get_retorna_405(self, client, comprador_user, fornecedor):
        """T-03-02 — GET em toggle-ativo deve retornar 405."""
        client.force_login(comprador_user)
        url = reverse("fornecedores:toggle-ativo", args=[fornecedor.pk])
        response = client.get(url)
        assert response.status_code == 405

    def test_toggle_ativo_retorna_partial_html(self, client, comprador_user, fornecedor):
        """POST deve retornar partial HTML com linha atualizada (para HTMX outerHTML swap)."""
        client.force_login(comprador_user)
        url = reverse("fornecedores:toggle-ativo", args=[fornecedor.pk])
        response = client.post(url)
        assert response.status_code == 200
        content = response.content.decode()
        # Deve conter o ID do fornecedor na linha
        assert f"fornecedor-{fornecedor.pk}" in content

    def test_toggle_ativo_solicitante_recebe_403(
        self, client, solicitante_user, fornecedor
    ):
        """T-03-01 — Solicitante recebe 403 ao tentar toggle."""
        client.force_login(solicitante_user)
        url = reverse("fornecedores:toggle-ativo", args=[fornecedor.pk])
        response = client.post(url)
        assert response.status_code == 403
