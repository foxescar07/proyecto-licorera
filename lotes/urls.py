from django.urls import path

from . import views

app_name = 'lotes'

urlpatterns = [
    path('', views.lote_list, name='lote_list'),
    path('crear/', views.lote_create, name='lote_create'),
    path('<str:numero_lote>/', views.lote_detail, name='lote_detail'),
    path('<str:numero_lote>/editar/', views.lote_update, name='lote_update'),
    path('<str:numero_lote>/ajustar-stock/', views.lote_ajustar_stock, name='lote_ajustar_stock'),
]