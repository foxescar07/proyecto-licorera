from django.urls import path
from . import views

app_name = 'producto'

urlpatterns = [
    path('',                                        views.lista_productos,       name='lista_productos'),
    path('crear/',                                  views.crear_producto,         name='crear_producto'),
    path('<int:pk>/presentaciones/',                views.presentaciones_guardar, name='presentaciones_guardar'),
    path('buscar/',                                 views.buscar_producto,        name='buscar_producto'),
    path('stock-status/',                           views.stock_status,           name='stock_status'),
    path('rotacion/',                               views.rotacion_json,          name='rotacion_json'),

    # ── de la rama anterior ───────────────────────────────────────────────────
    path('producto/<int:pk>/',                      views.producto_detalle,       name='producto_detalle'),
    path('producto/<int:pk>/editar/',               views.producto_editar,        name='producto_editar'),
    path('producto/<int:pk>/eliminar/',             views.producto_eliminar,      name='producto_eliminar'),
    path('registro/',                               views.producto_registro,      name='producto_registro'),
    path('agenda/',                                 views.agenda_lista,           name='agenda_lista'),
    path('agenda/<int:pk>/eliminar/',               views.agenda_eliminar,        name='agenda_eliminar'),
    path('categorias/',                             views.categorias_lista,       name='categorias_lista'),
    path('categorias/crear/',                       views.categoria_crear,        name='categoria_crear'),
    path('categorias/<int:pk>/editar/',             views.categoria_editar,       name='categoria_editar'),
    path('categorias/<int:pk>/eliminar/',           views.categoria_eliminar,     name='categoria_eliminar'),
    path('salida/',                                 views.producto_salida,        name='producto_salida'),
]