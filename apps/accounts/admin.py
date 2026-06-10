"""
Django admin configuration for accounts app.
Provides developer access to User and UnidadeOrganizacional via /admin/.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import UnidadeOrganizacional, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Perfil ComprasNexos",
            {"fields": ("role", "default_unit")},
        ),
    )
    list_display = ["email", "username", "first_name", "last_name", "role", "is_active"]
    list_filter = ["role", "is_active"]


@admin.register(UnidadeOrganizacional)
class UnidadeOrganizacionalAdmin(admin.ModelAdmin):
    list_display = ["nome", "ativo", "criado_em"]
    list_filter = ["ativo"]
    search_fields = ["nome"]
