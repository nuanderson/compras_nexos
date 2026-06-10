# Monetary fields in all apps: DecimalField(max_digits=12, decimal_places=2) — never FloatField
from django.conf import settings
from django.db import models


class TimestampedModel(models.Model):
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditedModel(TimestampedModel):
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="%(app_label)s_%(class)s_criado",
    )

    class Meta:
        abstract = True
