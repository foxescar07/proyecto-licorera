from django.urls import path
from . import views

urlpatterns = [
    path('',                                        views.inventario_home,            name='inventario_home'),
    path('gestion/salida/',                         views.registrar_salida_view,      name='registrar_salida_view'),
    path('gestion/lotes/',                          views.gestion_lotes_view,         name='gestion_lotes_view'),
    
    # Agendas
    path('agenda/',                                 views.agenda_lista,               name='agenda_lista'),
    path('agenda/<int:pk>/estado/',                 views.agenda_estado,              name='agenda_estado'),
    path('agenda/<int:pk>/eliminar/',               views.agenda_eliminar,            name='agenda_eliminar'),
    
    # Conteos
    path('conteo/',                                 views.conteo_inventario,          name='conteo_inventario'),
    path('conteo/guardar/',                         views.guardar_conteo,             name='guardar_conteo'),
    
    # Ajustes y Códigos
    path('ajustar/<int:pk>/',                       views.ajustar_stock_presentacion, name='ajustar_stock_presentacion'),
    path('codigos/<int:pk>/guardar/',               views.guardar_codigo,             name='guardar_codigo'),
    path('movimiento/<int:pk>/editar/',             views.editar_movimiento,          name='editar_movimiento'),
    
    # Stock y Lotes
    path('stock/',                                  views.gestion_stock,              name='gestion_stock'),
    path('stock/status/',                           views.stock_status,               name='stock_status'),
    path('rotacion/',                               views.rotacion_json,              name='rotacion_json'),
    path('salida/',                                 views.producto_salida,            name='producto_salida'),
    path('lote/registrar/',                         views.registrar_lote,             name='registrar_lote'),
    path('lote/<int:pk>/editar-stock/',             views.editar_lote_stock,          name='editar_lote_stock'),
]