"""
Accounts models: custom User model and UnidadeOrganizacional.

IMPORTANT: AUTH_USER_MODEL = 'accounts.User' must be set BEFORE any migrate command.
This model must be created first — it is the irreversible foundation all other apps depend on.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class UnidadeOrganizacional(models.Model):
    nome = models.CharField(max_length=150)
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Unidade Organizacional"
        verbose_name_plural = "Unidades Organizacionais"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class User(AbstractUser):
    class Role(models.TextChoices):
        SOLICITANTE = "solicitante", "Solicitante"
        GESTOR = "gestor", "Gestor"
        COMPRADOR = "comprador", "Comprador"
        DIRETOR = "diretor", "Diretor"
        ADMIN = "admin", "Admin"

    # Email as the login field
    email = models.EmailField(unique=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]  # kept for createsuperuser compat

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.SOLICITANTE,
    )
    default_unit = models.ForeignKey(
        UnidadeOrganizacional,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="default_users",
    )
