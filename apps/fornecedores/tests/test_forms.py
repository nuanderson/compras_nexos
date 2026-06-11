"""
Testes do FornecedorForm — validação de CNPJ via python-stdnum.

Cobre: FORN-02, D-02.
"""
import pytest

from apps.fornecedores.forms import FornecedorForm
from apps.fornecedores.models import Fornecedor
from apps.requisicoes.models import CategoriaCompra


@pytest.fixture
def categoria(db):
    return CategoriaCompra.objects.create(nome="Informática", ativo=True)


@pytest.fixture
def dados_validos(categoria):
    return {
        "cnpj": "11.222.333/0001-81",
        "razao_social": "Empresa Teste Ltda",
        "email": "teste@empresa.com",
        "telefone": "",
        "categoria": categoria.pk,
    }


class TestFornecedorFormCnpj:
    """FORN-02 — Validação de CNPJ."""

    def test_cnpj_formatado_aceito_e_compactado(self, db, dados_validos):
        """CNPJ com formatação XX.XXX.XXX/XXXX-XX deve ser aceito e retornar compactado."""
        form = FornecedorForm(data=dados_validos)
        assert form.is_valid(), form.errors
        assert form.cleaned_data["cnpj"] == "11222333000181"

    def test_cnpj_invalido_rejeitado(self, db, dados_validos):
        """CNPJ com dígitos verificadores incorretos deve ser rejeitado."""
        dados_validos["cnpj"] = "00000000000000"
        form = FornecedorForm(data=dados_validos)
        assert not form.is_valid()
        assert "cnpj" in form.errors

    def test_cnpj_alfanumerico_aceito(self, db, dados_validos):
        """D-02 — CNPJ alfanumérico Jul/2026 deve ser aceito."""
        dados_validos["cnpj"] = "12.ABC.345/01DE-35"
        form = FornecedorForm(data=dados_validos)
        assert form.is_valid(), form.errors
        assert form.cleaned_data["cnpj"] == "12ABC34501DE35"

    def test_cnpj_duplicado_rejeitado(self, db, dados_validos, categoria):
        """Dois fornecedores com o mesmo CNPJ devem ser rejeitados."""
        Fornecedor.objects.create(
            cnpj="11222333000181",
            razao_social="Empresa Existente",
            email="existente@empresa.com",
            categoria=categoria,
        )
        form = FornecedorForm(data=dados_validos)
        assert not form.is_valid()
        assert "cnpj" in form.errors
        assert "Já existe" in form.errors["cnpj"][0]

    def test_cnpj_duplicado_aceito_em_edicao_proprio(self, db, dados_validos, categoria):
        """Editar um fornecedor mantendo o mesmo CNPJ deve ser permitido."""
        fornecedor = Fornecedor.objects.create(
            cnpj="11222333000181",
            razao_social="Empresa Existente",
            email="existente@empresa.com",
            categoria=categoria,
        )
        form = FornecedorForm(data=dados_validos, instance=fornecedor)
        assert form.is_valid(), form.errors

    def test_cnpj_mensagem_erro_clara(self, db, dados_validos):
        """Mensagem de erro deve ser clara para o usuário."""
        dados_validos["cnpj"] = "12345678901234"
        form = FornecedorForm(data=dados_validos)
        assert not form.is_valid()
        assert "CNPJ inválido" in form.errors["cnpj"][0]
