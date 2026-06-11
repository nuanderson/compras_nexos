"""
FornecedorForm — validação de CNPJ via python-stdnum.

Padrão confirmado em RESEARCH.md: usar validate() diretamente,
capturar apenas StdnumValidationError (nunca except Exception bare).

Referências:
  FORN-02  validação de CNPJ (D-02)
  Pitfall 1 do RESEARCH.md  — compact() não valida
"""
from django import forms
from stdnum.br import cnpj as cnpj_lib
from stdnum.exceptions import ValidationError as StdnumValidationError

from apps.requisicoes.models import CategoriaCompra

from .models import Fornecedor


class FornecedorForm(forms.ModelForm):
    # Sobrescreve o campo cnpj para aceitar entrada formatada (ex: "11.222.333/0001-81")
    # sem disparar o max_length=14 do modelo antes do clean_cnpj processar.
    # O clean_cnpj compacta para 14 chars antes de salvar.
    cnpj = forms.CharField(
        max_length=20,
        label="CNPJ",
        help_text="Digite o CNPJ com ou sem formatação.",
    )
    categoria = forms.ModelChoiceField(
        queryset=CategoriaCompra.objects.filter(ativo=True),
        label="Categoria",
    )

    class Meta:
        model = Fornecedor
        fields = ["cnpj", "razao_social", "email", "telefone", "categoria"]
        labels = {
            "cnpj": "CNPJ",
            "razao_social": "Razão Social",
            "email": "E-mail",
            "telefone": "Telefone",
            "categoria": "Categoria",
        }

    def clean_cnpj(self):
        """
        Valida e compacta o CNPJ usando python-stdnum.

        validate() = compact() + check_length + check_format + check_checksum.
        Retorna o CNPJ compactado (14 chars) pronto para salvar.
        Levanta ValidationError para qualquer CNPJ inválido.
        """
        valor = self.cleaned_data.get("cnpj", "").strip()
        try:
            compactado = cnpj_lib.validate(valor)
        except StdnumValidationError:
            raise forms.ValidationError("CNPJ inválido. Verifique os dígitos.")

        # Unicidade: exclui o próprio pk em edição
        qs = Fornecedor.objects.filter(cnpj=compactado)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(
                "Já existe um fornecedor cadastrado com este CNPJ."
            )

        return compactado
