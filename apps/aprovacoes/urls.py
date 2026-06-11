from django.urls import path
from . import views

app_name = "aprovacoes"

urlpatterns = [
    # Gestor — 1o nivel de aprovacao (Plano 03)
    path("fila/", views.FilaGestorView.as_view(), name="fila-gestor"),
    path("<int:pk>/aprovar/", views.AprovarGestorView.as_view(), name="aprovar-gestor"),
    path("<int:pk>/modal-reprovar/", views.ModalReprovarView.as_view(), name="modal-reprovar-gestor"),
    path("<int:pk>/reprovar/", views.ReprovarGestorView.as_view(), name="reprovar-gestor"),
    # Diretor — 2o nivel de aprovacao (Plano 04, APROV-03, APROV-04)
    path("fila-diretor/", views.FilaDiretorView.as_view(), name="fila-diretor"),
    path("<int:pk>/aprovar-diretor/", views.AprovarDiretorView.as_view(), name="aprovar-diretor"),
    path("<int:pk>/modal-reprovar-diretor/", views.ModalReprovarDiretorView.as_view(), name="modal-reprovar-diretor"),
    path("<int:pk>/reprovar-diretor/", views.ReprovarDiretorView.as_view(), name="reprovar-diretor"),
]
