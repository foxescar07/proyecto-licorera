from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_proveedores),
    path('compras/', views.lista_compras),
]