from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_proveedores, name='lista_proveedores'),
    path('nuevo/', views.crear_proveedor, name='crear_proveedor'),
    path('detalle/<int:id>/', views.detalle_proveedor, name='detalle_proveedor'),
    path('editar/<int:id>/', views.editar_proveedor, name='editar_proveedor'),
    path('activar/<int:id>/', views.activar_proveedor, name='activar_proveedor'),
    path('desactivar/<int:id>/', views.desactivar_proveedor, name='desactivar_proveedor'),
    path('sancionar/<int:id>/', views.sancionar_proveedor, name='sancionar_proveedor'),
    path('eliminar/<int:id>/', views.eliminar_proveedor, name='eliminar_proveedor'),
    path('compras/', views.lista_compras, name='lista_compras'),
    path('registrar-compra/', views.registrar_compra, name='registrar_compra'),
    path('compras/<int:compra_id>/pago/', views.guardar_pago_compra, name='guardar_pago_compra'),
    path('compras/<int:compra_id>/cambiar-estado/', views.cambiar_estado_compra, name='cambiar_estado_compra'),

    # Órdenes de Compra
    path('ordenes/', views.listar_ordenes, name='listar_ordenes'),
    path('ordenes/crear/', views.crear_orden, name='crear_orden'),
    path('ordenes/<int:pk>/', views.detalle_orden, name='detalle_orden'),
    path('ordenes/<int:pk>/detalle/', views.agregar_detalle_orden, name='agregar_detalle_orden'),
    path('ordenes/<int:pk>/cambiar-estado/', views.cambiar_estado_orden, name='cambiar_estado_orden'),
    path('ordenes/<int:pk>/cambiar-estado-rapido/', views.cambiar_estado_orden_rapido, name='cambiar_estado_orden_rapido'),
    path('api/orden/<int:orden_id>/detalles/', views.api_orden_detalles, name='api_orden_detalles'),
    path('ordenes/<int:pk>/notas/', views.guardar_nota_orden, name='guardar_nota_orden'),
    path('ordenes/<int:pk>/historial/', views.obtener_historial_orden, name='obtener_historial_orden'),
    path('detalles/<int:detalle_id>/editar/', views.editar_detalle_orden, name='editar_detalle_orden'),
]