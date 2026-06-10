from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    # Auth
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("password-reset/", views.password_reset_view, name="password-reset"),
    path("password-reset/done/", views.password_reset_done_view, name="password-reset-done"),
    path(
        "password-reset-confirm/<uidb64>/<token>/",
        views.password_reset_confirm_view,
        name="password-reset-confirm",
    ),
    # Admin panel — user management
    path("admin-panel/usuarios/", views.UserListView.as_view(), name="user-list"),
    path("admin-panel/usuarios/novo/", views.UserCreateView.as_view(), name="user-create"),
    path("admin-panel/usuarios/<int:pk>/editar/", views.UserUpdateView.as_view(), name="user-edit"),
    path(
        "admin-panel/usuarios/<int:pk>/desativar/confirmar/",
        views.UserDeactivateConfirmView.as_view(),
        name="user-deactivate-confirm",
    ),
    path(
        "admin-panel/usuarios/<int:pk>/desativar/",
        views.UserDeactivateView.as_view(),
        name="user-deactivate",
    ),
    # Admin panel — unit management
    path("admin-panel/unidades/", views.UnitListView.as_view(), name="unit-list"),
    path("admin-panel/unidades/nova/", views.UnitCreateView.as_view(), name="unit-create"),
    path("admin-panel/unidades/<int:pk>/editar/", views.UnitUpdateView.as_view(), name="unit-edit"),
    path(
        "admin-panel/unidades/<int:pk>/desativar/confirmar/",
        views.UnitDeactivateConfirmView.as_view(),
        name="unit-deactivate-confirm",
    ),
    path(
        "admin-panel/unidades/<int:pk>/desativar/",
        views.UnitDeactivateView.as_view(),
        name="unit-deactivate",
    ),
]
