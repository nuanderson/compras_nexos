"""
Formulário de criação de RFQ.

RFQForm: exibe apenas requisições APROVADAS sem RFQ vinculado (D-06, Pitfall 4).
Label customizado para identificação visual no select (specifics do CONTEXT).

Referências:
  COT-01  criar RFQ vinculado a requisição aprovada
  D-06    OneToOneField — um RFQ por Requisicao (rfq__isnull=True exclui já cotadas)
"""
from django import forms

from apps.requisicoes.models import Requisicao

from .models import RFQ


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
