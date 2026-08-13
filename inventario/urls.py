from django.urls import path

from . import views

app_name = 'inventario'

urlpatterns = [
    # Dashboard
    path('', views.inventario_home, name='inventario_home'),
    path('gestion-stock/', views.gestion_stock, name='gestion_stock'),

    # Lote
    path('lotes/', views.lote_list, name='lote_list'),
    path('lotes/crear/', views.lote_create, name='lote_create'),
    path('lotes/<str:numero_lote>/', views.lote_detail, name='lote_detail'),
    path('lotes/<str:numero_lote>/editar/', views.lote_update, name='lote_update'),
    path('lotes/<str:numero_lote>/ajustar-stock/', views.lote_ajustar_stock, name='lote_ajustar_stock'),

    # Inventario (stock)
    path('stock/', views.inventario_list, name='inventario_list'),
    path('stock/<int:codigo_inventario>/', views.inventario_detail, name='inventario_detail'),

    # Movimiento de inventario
    path('movimientos/', views.movimiento_list, name='movimiento_list'),
    path('movimientos/crear/', views.movimiento_create, name='movimiento_create'),

    # Agenda de inventario
    path('agendas/', views.agenda_list, name='agenda_list'),
    path('agendas/crear/', views.agenda_create, name='agenda_create'),
    path('agendas/<int:codigo>/', views.agenda_detail, name='agenda_detail'),
    path('agendas/<int:codigo>/editar/', views.agenda_update, name='agenda_update'),
    path('agendas/<int:codigo>/completar/', views.agenda_completar, name='agenda_completar'),

    # Hallazgo
    path('hallazgos/', views.hallazgo_list, name='hallazgo_list'),
    path('agendas/<int:codigo_agenda>/hallazgos/crear/', views.hallazgo_create, name='hallazgo_create'),
]