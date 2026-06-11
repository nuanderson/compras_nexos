"""
Testes do modelo Fornecedor e template tag cnpj_format.

Cobre: FORN-01, FORN-02 (alfanumérico), FORN-03 (PROTECT), FORN-04 (ativo).
"""
import pytest
from django.db.models.deletion import ProtectedError

from apps.fornecedores.models import Fornecedor
from apps.fornecedores.templatetags.fornecedor_tags import cnpj_format
from apps.requisicoes.models import CategoriaCompra


@pytest.fixture
def categoria(db):
    return CategoriaCompra.objects.create(nome="Informática", ativo=True)


@pytest.fixture
def fornecedor(db, categoria):
    return Fornecedor.objects.create(
        cnpj="11222333000181",
        razao_social="Empresa Teste Ltda",
        email="teste@empresa.com",
        categoria=categoria,
        ativo=True,
    )


@pytest.mark.django_db
class TestFornecedorModel:
    """FORN-01 — Campos e persistência."""

    def test_cnpj_numerico_salva_corretamente(self, fornecedor):
        """CNPJ numérico de 14 chars salva e é único."""
        assert fornecedor.cnpj == "11222333000181"

    def test_cnpj_alfanumerico_salva_corretamente(self, db, categoria):
        """D-02 — CNPJ alfanumérico Jul/2026 com 14 chars deve salvar."""
        f = Fornecedor.objects.create(
            cnpj="12ABC34501DE35",
            razao_social="Empresa Alfa Ltda",
            email="alfa@empresa.com",
            categoria=categoria,
            ativo=True,
        )
        assert f.cnpj == "12ABC34501DE35"

    def test_str_retorna_razao_social(self, fornecedor):
        assert str(fornecedor) == "Empresa Teste Ltda"

    def test_ativo_default_true(self, fornecedor):
        assert fornecedor.ativo is True

    def test_telefone_opcional(self, db, categoria):
        """A2 do research — telefone não é obrigatório."""
        f = Fornecedor.objects.create(
            cnpj="45678901234567",
            razao_social="Sem Telefone Ltda",
            email="semtel@empresa.com",
            categoria=categoria,
        )
        assert f.telefone == ""


@pytest.mark.django_db
class TestFornecedorCategoriaProtect:
    """FORN-03 — FK CategoriaCompra com PROTECT (D-01)."""

    def test_deletar_categoria_com_fornecedor_levanta_protectederror(
        self, fornecedor, categoria
    ):
        """Deletar CategoriaCompra vinculada deve levantar ProtectedError."""
        with pytest.raises(ProtectedError):
            categoria.delete()


class TestCnpjFormatFilter:
    """Template filter cnpj_format."""

    def test_formata_cnpj_numerico(self):
        assert cnpj_format("11222333000181") == "11.222.333/0001-81"

    def test_formata_cnpj_alfanumerico(self):
        """D-02 — CNPJ alfanumérico deve ser formatado corretamente."""
        assert cnpj_format("12ABC34501DE35") == "12.ABC.345/01DE-35"

    def test_valor_vazio_retorna_vazio(self):
        assert cnpj_format("") == ""

    def test_valor_none_retorna_none(self):
        """None deve ser retornado sem exceção."""
        assert cnpj_format(None) is None
