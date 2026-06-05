from django.urls import path
from . import views


urlpatterns = [
    path('',                                        views.inventario_home,            name='inventario_home'),
     path('gestion-inventario/',                     views.gestion_inventario,         name='gestion_inventario'), 
    path('agenda/<int:pk>/estado/',                 views.agenda_estado,              name='agenda_estado'),
    path('conteo/',                                 views.conteo_inventario,          name='conteo_inventario'),
    path('conteo/guardar/',                         views.guardar_conteo,             name='guardar_conteo'),
    path('ajustar/<int:pk>/',                       views.ajustar_stock,              name='ajustar_stock'),
    path('codigos/<int:pk>/guardar/',               views.guardar_codigo,             name='guardar_codigo'),
    path('movimiento/<int:pk>/editar/',             views.editar_movimiento,          name='editar_movimiento'),
   
    # ── Rutas de la rama antigua ──
    path('gestion/salida/',                         views.gestion_salida,             name='gestion_salida'),
    path('gestion/producto/eliminar/<int:pk>/',     views.gestion_producto_eliminar,  name='gestion_producto_eliminar'),
    path('gestion/producto/editar/<int:pk>/',       views.gestion_producto_editar,    name='gestion_producto_editar'),
    path('gestion/categoria/crear/',                views.gestion_categoria_crear,    name='gestion_categoria_crear'),
    path('gestion/categoria/eliminar/<int:pk>/',    views.gestion_categoria_eliminar, name='gestion_categoria_eliminar'),
    path('gestion/categoria/editar/<int:pk>/',      views.gestion_categoria_editar,   name='gestion_categoria_editar'),
    path('lote/registrar/',                         views.registrar_lote,             name='registrar_lote'),
]