from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("password-reset/", views.password_reset_view, name="password-reset"),
    path("password-reset/done/", views.password_reset_done_view, name="password-reset-done"),
    path(
        "password-reset-confirm/<uidb64>/<token>/",
        views.password_reset_confirm_view,
        name="password-reset-confirm",
    ),
]
