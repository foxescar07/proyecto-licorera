from django.urls import path
from . import views

app_name = 'producto'

urlpatterns = [
    path('',                              views.lista_productos,        name='lista_productos'),
    path('crear/',                        views.crear_producto,          name='crear_producto'),
    path('<int:pk>/presentaciones/',      views.presentaciones_guardar,  name='presentaciones_guardar'),
    path('buscar/',                       views.buscar_producto,         name='buscar_producto'),
    path('stock-status/',                 views.stock_status,            name='stock_status'),
    path('rotacion/',                     views.rotacion_json,           name='rotacion_json'),
]