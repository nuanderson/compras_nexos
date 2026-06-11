"""
Template tags e filtros para o app fornecedores.

cnpj_format: formata CNPJ compactado para exibição (XX.XXX.XXX/XXXX-XX).
Suporta CNPJ numérico e alfanumérico (Jul/2026).

Referência: RESEARCH.md — CNPJ Display Formatting.
"""
from django import template
from stdnum.br import cnpj as cnpj_lib

register = template.Library()


@register.filter(name="cnpj_format")
def cnpj_format(value):
    """
    Formata CNPJ compactado para exibição.

    Retorna valor formatado XX.XXX.XXX/XXXX-XX ou XX.XXX.XXX/XXXX-XX (alfanumérico).
    Retorna o valor original se None, vazio ou se a formatação falhar.
    """
    if not value:
        return value
    try:
        return cnpj_lib.format(value)
    except Exception:
        return value  # fallback seguro para exibição
