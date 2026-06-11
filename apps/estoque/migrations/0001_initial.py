"""
Migration inicial do app estoque.

Cria as tabelas UnidadeMedida e ItemEstoque com UniqueConstraint
unique_item_por_unidade (nome + unidade_organizacional).
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="UnidadeMedida",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("nome", models.CharField(max_length=50, unique=True)),
                ("sigla", models.CharField(max_length=10, unique=True)),
                ("ativo", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Unidade de Medida",
                "verbose_name_plural": "Unidades de Medida",
                "ordering": ["nome"],
            },
        ),
        migrations.CreateModel(
            name="ItemEstoque",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("nome", models.CharField(max_length=200)),
                ("quantidade_atual", models.IntegerField(default=0)),
                ("quantidade_minima", models.IntegerField(default=0)),
                (
                    "unidade_medida",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="itens_estoque",
                        to="estoque.unidademedida",
                    ),
                ),
                (
                    "unidade_organizacional",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="itens_estoque",
                        to="accounts.unidadeorganizacional",
                    ),
                ),
            ],
            options={
                "verbose_name": "Item de Estoque",
                "verbose_name_plural": "Itens de Estoque",
                "ordering": ["nome"],
            },
        ),
        migrations.AddConstraint(
            model_name="itemestoque",
            constraint=models.UniqueConstraint(
                fields=["nome", "unidade_organizacional"],
                name="unique_item_por_unidade",
            ),
        ),
    ]
