from django.urls import path  # type: ignore
from . import views

urlpatterns = [
    path('',                                        views.lista_productos,        name='lista_productos'),
    path('crear/',                                  views.crear_producto,         name='crear_producto'),
    path('<int:pk>/presentaciones/',                views.presentaciones_guardar, name='presentaciones_guardar'),
    path('buscar/',                                 views.buscar_producto,        name='buscar_producto'),
    path('producto/<int:pk>/',                      views.producto_detalle,       name='producto_detalle'),
    path('registro/',                               views.producto_registro,      name='producto_registro'),
    path('categorias/',                             views.categorias_lista,       name='categorias_lista'),
    path('stock-status/',                           views.stock_status,           name='stock_status'),
    
    # Rutas movidas desde inventario para gestión centralizada de productos
    path('gestion/categoria/crear/',                views.categoria_crear,                name='categoria_crear'),
    path('gestion/categoria/eliminar/<int:pk>/',    views.categoria_eliminar,             name='categoria_eliminar'),
    path('gestion/categoria/editar/<int:pk>/',      views.categoria_editar,               name='categoria_editar'),
]