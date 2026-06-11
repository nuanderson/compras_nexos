"""
Migration inicial do app fornecedores.

Cria a tabela fornecedores_fornecedor com todos os campos do modelo Fornecedor.
NÃO adiciona TrigramExtension — já habilitada em accounts/0001_initial.py.

Referências:
  FORN-01  modelo Fornecedor
  D-01     FK CategoriaCompra com PROTECT
  D-02     cnpj CharField(max_length=14, unique=True)
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("requisicoes", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Fornecedor",
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
                ("cnpj", models.CharField(max_length=14, unique=True)),
                ("razao_social", models.CharField(max_length=200)),
                ("email", models.EmailField(max_length=254)),
                ("telefone", models.CharField(blank=True, default="", max_length=20)),
                (
                    "categoria",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="fornecedores",
                        to="requisicoes.categoriacompra",
                    ),
                ),
                ("ativo", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Fornecedor",
                "verbose_name_plural": "Fornecedores",
                "ordering": ["razao_social"],
                "abstract": False,
            },
        ),
        migrations.AddIndex(
            model_name="fornecedor",
            index=models.Index(fields=["ativo"], name="fornecedor_ativo_idx"),
        ),
        migrations.AddIndex(
            model_name="fornecedor",
            index=models.Index(
                fields=["categoria"], name="fornecedor_categoria_idx"
            ),
        ),
    ]
