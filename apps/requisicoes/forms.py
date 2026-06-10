"""
Forms para o app de Requisições.

RequisicaoForm: formulário de criação/edição de rascunho pelo Solicitante.
"""
from django import forms

from apps.accounts.models import UnidadeOrganizacional

from .models import CategoriaCompra, Requisicao


class RequisicaoForm(forms.ModelForm):
    """
    Formulário de criação e edição de requisições em RASCUNHO. (REQ-01, D-12)

    Recebe kwarg opcional `user` para pré-selecionar a unidade padrão
    do Solicitante (UNIT-03 / Questão aberta 2 do RESEARCH.md).
    """

    class Meta:
        model = Requisicao
        fields = ["descricao", "categoria", "valor_estimado", "justificativa", "unidade"]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Restringir categorias e unidades ativas apenas
        self.fields["categoria"].queryset = CategoriaCompra.objects.filter(ativo=True)
        self.fields["unidade"].queryset = UnidadeOrganizacional.objects.filter(ativo=True)

        # Pré-selecionar unidade padrão do Solicitante (UNIT-03)
        if user and user.default_unit:
            self.fields["unidade"].initial = user.default_unit
