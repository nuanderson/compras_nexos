"""
Formulários do app estoque.

ItemEstoqueForm — cadastro e edição (unidade_organizacional excluída: atribuída na view)
AtualizarQuantidadeForm — atualização de quantidade com validação >= 0
"""
from django import forms

from .models import ItemEstoque, UnidadeMedida


class ItemEstoqueForm(forms.ModelForm):
    """
    Formulário de cadastro/edição de item de estoque.

    unidade_organizacional NÃO está nos fields — atribuída pela view
    com request.user.default_unit (T-03-09).
    """

    unidade_medida = forms.ModelChoiceField(
        queryset=UnidadeMedida.objects.filter(ativo=True),
        label="Unidade de Medida",
        empty_label="Selecione...",
    )

    class Meta:
        model = ItemEstoque
        fields = ["nome", "unidade_medida", "quantidade_atual", "quantidade_minima"]
        labels = {
            "nome": "Nome do Item",
            "quantidade_atual": "Quantidade Atual",
            "quantidade_minima": "Quantidade Mínima",
        }


class AtualizarQuantidadeForm(forms.ModelForm):
    """
    Formulário de atualização de quantidade.

    Valida que quantidade >= 0 (T-03-08).
    """

    class Meta:
        model = ItemEstoque
        fields = ["quantidade_atual"]
        labels = {"quantidade_atual": "Quantidade Atual"}

    def clean_quantidade_atual(self):
        valor = self.cleaned_data.get("quantidade_atual")
        if valor is not None and valor < 0:
            raise forms.ValidationError("A quantidade não pode ser negativa.")
        return valor
