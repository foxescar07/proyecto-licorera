from django.urls import path
from . import views

urlpatterns = [
    path("", views.lista_marcas, name="lista_marcas"),
    path("nueva/", views.crear_marca, name="crear_marca"),
    path("<int:pk>/editar/", views.editar_marca, name="editar_marca"),
    path("<int:pk>/eliminar/", views.eliminar_marca, name="eliminar_marca"),
]