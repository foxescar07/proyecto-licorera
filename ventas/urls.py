from django.urls import path
from . import views

app_name = 'ventas'

urlpatterns = [



    # ── Devoluciones ─────────────────────────────────────────────
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
    path(
        'devoluciones/pdf/<int:pk>/',
        views.descargar_comprobante_pdf,
        name='descargar_comprobante_pdf',
    ),
    path(
        'devoluciones/historial/',
        views.historial_devoluciones,
        name='historial_devoluciones',
    ),
    path(
        'devoluciones/<int:pk>/detalle/',
        views.detalle_devolucion,
        name='detalle_devolucion',
    ),
]