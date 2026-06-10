"""
Accounts forms: user create/edit and unidade forms.
"""
from django import forms
from django.contrib.auth.hashers import make_password

from .models import UnidadeOrganizacional, User


class UserCreateForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput,
    )
    password2 = forms.CharField(
        label="Confirmar senha",
        widget=forms.PasswordInput,
    )

    class Meta:
        model = User
        fields = ["email", "username", "first_name", "last_name", "role", "default_unit"]

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password1")
        p2 = cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("As senhas não coincidem. Tente novamente.")
        return cleaned_data


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["email", "username", "first_name", "last_name", "role", "default_unit", "is_active"]


class UnidadeForm(forms.ModelForm):
    class Meta:
        model = UnidadeOrganizacional
        fields = ["nome", "descricao", "ativo"]
