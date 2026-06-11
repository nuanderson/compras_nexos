"""
Modelo Fornecedor.

CNPJ armazenado no formato compactado (14 chars, sem formatação).
Validação e compactação ocorrem exclusivamente no FornecedorForm (D-02).

Referências:
  FORN-01  campos básicos do fornecedor
  FORN-03  FK CategoriaCompra com PROTECT (D-01)
  FORN-04  campo ativo para toggle sem perda de histórico
"""
from django.db import models

from apps.core.models import TimestampedModel


class Fornecedor(TimestampedModel):
    """
    Fornecedor cadastrado pelo Comprador.

    cnpj é armazenado compactado (14 chars: dígitos ou alfanumérico Jul/2026).
    unique=True garante ausência de duplicatas no banco.
    """

    cnpj = models.CharField(max_length=14, unique=True)
    razao_social = models.CharField(max_length=200)
    email = models.EmailField()
    telefone = models.CharField(max_length=20, blank=True, default="")
    categoria = models.ForeignKey(
        "requisicoes.CategoriaCompra",
        on_delete=models.PROTECT,
        related_name="fornecedores",
    )
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Fornecedor"
        verbose_name_plural = "Fornecedores"
        ordering = ["razao_social"]

    def __str__(self):
        return self.razao_social
