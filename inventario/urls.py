from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    path('', views.inventario_home, name='inventario_home'),
    path('stock/', views.gestion_stock, name='gestion_stock'),
    path('lotes/', views.lote_list, name='lote_list'),
    path('lotes/nuevo/', views.lote_create, name='lote_create'),
    path('lotes/<str:numero_lote>/', views.lote_detail, name='lote_detail'),
    path('lotes/<str:numero_lote>/editar/', views.lote_update, name='lote_update'),
    path('lotes/<str:numero_lote>/ajustar/', views.lote_ajustar_stock, name='lote_ajustar_stock'),
    path('movimientos/', views.movimiento_list, name='movimiento_list'),
    path('movimientos/nuevo/', views.movimiento_create, name='movimiento_create'),
    path('lista/', views.inventario_list, name='inventario_list'),
    path('detalle/<int:codigo_inventario>/', views.inventario_detail, name='inventario_detail'),
]