from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    path('',                              views.inventario_home,     name='inventario_home'),
    path('agenda/<int:pk>/estado/',       views.agenda_estado,       name='agenda_estado'),
    path('conteo/',                       views.conteo_inventario,   name='conteo_inventario'),
    path('conteo/guardar/',               views.guardar_conteo,      name='guardar_conteo'),
    path('ajustar/<int:pk>/',             views.ajustar_stock,       name='ajustar_stock'),
    path('codigos/<int:pk>/guardar/',     views.guardar_codigo,      name='guardar_codigo'),
    path('movimiento/<int:pk>/editar/',   views.editar_movimiento,   name='editar_movimiento'),
    path('gestion/',                      views.gestion_productos,   name='gestion_productos'),
]