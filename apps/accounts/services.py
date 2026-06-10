"""
Accounts service layer.
Business logic for user and organizational unit management.
Views call these functions — never contain business logic themselves.
"""
from django.contrib.auth.models import Group

from .models import UnidadeOrganizacional, User


def create_user(data: dict) -> User:
    """
    Create a new user with the given data.
    Sets password via set_password() and assigns to the appropriate Django Group.
    """
    password = data.pop("password1", None) or data.pop("password", None)
    # Remove password2 if present
    data.pop("password2", None)

    user = User(**data)
    if password:
        user.set_password(password)
    user.save()

    # Assign to Django Group matching role (capitalize first letter)
    role_display = user.get_role_display()
    group, _ = Group.objects.get_or_create(name=role_display)
    user.groups.add(group)

    return user


def deactivate_user(user: User, actor: User) -> User:
    """
    Deactivate a user account (set is_active=False).
    The user's history is preserved.
    """
    user.is_active = False
    user.save(update_fields=["is_active"])
    return user


def assign_unit(user: User, unit: UnidadeOrganizacional) -> User:
    """
    Assign a default organizational unit to a user.
    """
    user.default_unit = unit
    user.save(update_fields=["default_unit"])
    return user
