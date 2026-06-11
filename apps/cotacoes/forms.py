"""
Formulários do app cotacoes.

RFQForm: exibe apenas requisições APROVADAS sem RFQ vinculado (D-06, Pitfall 4).
Label customizado para identificação visual no select (specifics do CONTEXT).

CotacaoFornecedorForm: formulário para adicionar cotação de fornecedor ao RFQ (COT-02).
Restringe queryset de fornecedores a ativo=True (D-05).

Referências:
  COT-01  criar RFQ vinculado a requisição aprovada
  COT-02  adicionar cotações de fornecedores
  D-06    OneToOneField — um RFQ por Requisicao (rfq__isnull=True exclui já cotadas)
  D-05    apenas fornecedores ativos no select
"""
from django import forms

from apps.fornecedores.models import Fornecedor
from apps.requisicoes.models import Requisicao

from .models import CotacaoFornecedor, RFQ


class RFQForm(forms.ModelForm):
    """
    Formulário para criação de RFQ.

    Queryset filtrado: apenas Requisicao APROVADO sem RFQ vinculado (D-06, Pitfall 4).
    label_from_instance customizado para display informativo no select.
    """

    class Meta:
        model = RFQ
        fields = ["requisicao"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["requisicao"].queryset = (
            Requisicao.objects.filter(
                status=Requisicao.Status.APROVADO,
                rfq__isnull=True,
            ).select_related("categoria")
        )
        self.fields["requisicao"].label_from_instance = (
            lambda obj: f"#{obj.pk} — {obj.descricao[:40]} (R$ {obj.valor_estimado:,.2f})"
        )
        self.fields["requisicao"].widget.attrs.update({"class": "form-select"})
        self.fields["requisicao"].label = "Requisição"


class CotacaoFornecedorForm(forms.ModelForm):
    """
    Formulário para adicionar cotação de fornecedor a um RFQ (COT-02, D-01/D-02/D-03).

    Queryset de fornecedores restrito a ativo=True (D-05).
    Campos: fornecedor, preco_unitario, prazo_entrega, condicoes_pagamento, observacoes.
    """

    class Meta:
        model = CotacaoFornecedor
        fields = ["fornecedor", "preco_unitario", "prazo_entrega", "condicoes_pagamento", "observacoes"]
        labels = {
            "fornecedor": "Fornecedor",
            "preco_unitario": "Preço Unitário (R$)",
            "prazo_entrega": "Prazo de Entrega",
            "condicoes_pagamento": "Condições de Pagamento",
            "observacoes": "Observações",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Restringir fornecedores a apenas ativos, ordenados por razão social (D-05)
        self.fields["fornecedor"].queryset = (
            Fornecedor.objects.filter(ativo=True).order_by("razao_social")
        )
        # Aplicar classes CSS
        self.fields["fornecedor"].widget.attrs.update({"class": "form-select"})
        for field_name in ["preco_unitario", "prazo_entrega", "condicoes_pagamento", "observacoes"]:
            self.fields[field_name].widget.attrs.update({"class": "form-input"})
        self.fields["observacoes"].required = False
        self.fields["prazo_entrega"].required = False
        self.fields["condicoes_pagamento"].required = False
