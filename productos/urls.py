from django.urls import path  # type: ignore
from . import views

urlpatterns = [
    path('',                                        views.lista_productos,        name='lista_productos'),
    path('crear/',                                  views.crear_producto,         name='crear_producto'),
    path('buscar/',                                 views.buscar_producto,        name='buscar_producto'),
    path('producto/<int:pk>/',                      views.producto_detalle,       name='producto_detalle'),
    path('registro/',                               views.producto_registro,      name='producto_registro'),
    path('stock-status/',                           views.stock_status,           name='stock_status'),
]