from django.urls import path
from . import views

urlpatterns = [
    path('', views.principal, name='principal'),
    path('cerrar-sesion/', views.cerrar_sesion, name='cerrar_sesion'),
]