"""
Seed migration: cria as 8 unidades de medida iniciais. D-04.

Unidades: UN, KG, CX, L, M, PAR, PCT, RES.
Usa get_or_create por sigla para ser idempotente.
NÃO importa o model diretamente — usa apps.get_model() para evitar
problemas com migration reversal.
"""
from django.db import migrations


UNIDADES_INICIAIS = [
    ("Unidade", "UN"),
    ("Quilograma", "KG"),
    ("Caixa", "CX"),
    ("Litro", "L"),
    ("Metro", "M"),
    ("Par", "PAR"),
    ("Pacote", "PCT"),
    ("Resma", "RES"),
]


def seed_unidades(apps, schema_editor):
    UnidadeMedida = apps.get_model("estoque", "UnidadeMedida")
    for nome, sigla in UNIDADES_INICIAIS:
        UnidadeMedida.objects.get_or_create(sigla=sigla, defaults={"nome": nome})


def unseed_unidades(apps, schema_editor):
    UnidadeMedida = apps.get_model("estoque", "UnidadeMedida")
    siglas = [sigla for _, sigla in UNIDADES_INICIAIS]
    UnidadeMedida.objects.filter(sigla__in=siglas).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("estoque", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_unidades, unseed_unidades),
    ]
