from django.urls import path
from . import views

app_name = "aprovacoes"

urlpatterns = [
    path("fila/", views.FilaGestorView.as_view(), name="fila-gestor"),
    path("<int:pk>/aprovar/", views.AprovarGestorView.as_view(), name="aprovar-gestor"),
    path("<int:pk>/modal-reprovar/", views.ModalReprovarView.as_view(), name="modal-reprovar-gestor"),
    path("<int:pk>/reprovar/", views.ReprovarGestorView.as_view(), name="reprovar-gestor"),
]
