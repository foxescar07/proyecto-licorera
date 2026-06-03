from django.urls import path
from . import views


urlpatterns = [

    # ── Desbloqueo de caja ────────────────────────────────────────
    path(
        '',
        views.desbloquear_caja,
        name='desbloquear_caja',
    ),
    path(
        'bloquear/',
        views.bloquear_caja,
        name='bloquear_caja',
    ),

    # ── Ventas ────────────────────────────────────────────────────
    path(
        'lista/',
        views.ventas_lista,
        name='ventas_lista',
    ),
    path(
        'nueva/',
        views.nueva_venta,
        name='nueva_venta',
    ),
    path(
        'eliminar/<int:pk>/',
        views.eliminar_venta,
        name='eliminar_venta',
    ),
    path(
        'producto/<int:pk>/stock/',
        views.producto_stock_json,
        name='producto_stock_json',
    ),
    path(
        'dia/',
        views.ventas_dia,
        name='ventas_dia',
    ),

    # ── Caja ──────────────────────────────────────────────────────
    path(
        'caja/apertura/',
        views.apertura_caja,
        name='apertura_caja',
    ),
    path(
        'caja/cierre/',
        views.cierre_caja,
        name='cierre_caja',
    ),
    path(
        'caja/conteo/',
        views.registrar_conteo,
        name='registrar_conteo',
    ),

    # ── Devoluciones ──────────────────────────────────────────────
    path(
        'devoluciones/',
        views.lista_devoluciones,
        name='lista_devoluciones',
    ),
    path(
        'devoluciones/buscar/',
        views.buscar_venta_devolucion,
        name='buscar_venta_devolucion',
    ),
    path(
        'devoluciones/venta/<int:venta_id>/detalle/',
        views.detalle_venta_devolucion,
        name='detalle_venta_devolucion',
    ),
    path(
        'devoluciones/registrar/',
        views.registrar_devolucion,
        name='registrar_devolucion',
    ),
    path(
        'devoluciones/comprobante/<int:pk>/',
        views.comprobante_devolucion,
        name='comprobante_devolucion',
    ),

    # ── Pendientes (descomentar cuando se implementen) ────────────
    # path('devoluciones/pdf/<int:pk>/',        views.descargar_comprobante_pdf, name='descargar_comprobante_pdf'),
    # path('devoluciones/historial/',           views.historial_devoluciones,    name='historial_devoluciones'),
    # path('devoluciones/<int:pk>/detalle/',    views.detalle_devolucion,        name='detalle_devolucion'),
]