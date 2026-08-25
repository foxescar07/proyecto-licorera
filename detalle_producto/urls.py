from django.urls import path
from . import views

app_name = 'detalle_producto'

urlpatterns = [
    path('', views.detalle_producto_lista, name='lista'),
    path('desactivar/<int:pk>/', views.detalle_producto_desactivar, name='desactivar'),
    path('activar/<int:pk>/', views.detalle_producto_activar, name='activar'),
    path('editar/<int:pk>/', views.detalle_producto_editar, name='editar'),
    path('guardar-codigo/<int:pk>/', views.guardar_codigo, name='guardar_codigo'),
]