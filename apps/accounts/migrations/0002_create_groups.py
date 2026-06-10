"""
Data migration: create the 5 Django Groups (Solicitante, Gestor, Comprador, Diretor, Admin).
This runs automatically with `manage.py migrate` — no manual step required.
Uses apps.get_model() for compatibility with historical state.
"""
from django.db import migrations

GRUPOS = ["Solicitante", "Gestor", "Comprador", "Diretor", "Admin"]


def create_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for nome in GRUPOS:
        Group.objects.get_or_create(name=nome)


def delete_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=GRUPOS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_groups, delete_groups),
    ]
