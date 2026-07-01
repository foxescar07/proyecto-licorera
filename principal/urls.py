from django.urls import path
from . import views

urlpatterns = [
    path('', views.principal, name='principal'),
    path('cerrar-sesion/', views.cerrar_sesion, name='cerrar_sesion'),
    path('semana-json/', views.semana_json, name='semana_json'),
    path('meses-json/', views.meses_json, name='meses_json'),
]