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
    path('compras/<int:id>/estado/', views.cambiar_estado_compra, name='cambiar_estado_compra'),
    path('compras/<int:id>/pago/', views.registrar_pago_compra, name='registrar_pago_compra'),

    # Rutas para AJAX/Modales
    path('modal/detalle/<int:id>/', views.detalle_proveedor_modal, name='detalle_proveedor_modal'),
    path('modal/desactivar/<int:id>/', views.desactivar_proveedor, name='desactivar_proveedor_modal'),
    path('modal/reactivar/<int:id>/', views.reactivar_proveedor, name='reactivar_proveedor_modal'),
    path('modal/sancionar/<int:id>/', views.sancionar_proveedor, name='sancionar_proveedor_modal'),
    path('modal/levantar-sancion/<int:id>/', views.levantar_sancion_proveedor, name='levantar_sancion_proveedor'),
]
