from django import forms


class ReprovaForm(forms.Form):
    motivo = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        required=True,
        label="Motivo da Reprovacao",
        error_messages={"required": "O motivo da reprovacao e obrigatorio."},
    )

    def clean_motivo(self):
        motivo = self.cleaned_data.get("motivo", "")
        if not motivo.strip():
            raise forms.ValidationError("O motivo da reprovacao e obrigatorio.")
        return motivo
