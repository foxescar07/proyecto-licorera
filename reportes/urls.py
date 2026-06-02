from django.urls import path
from . import views


urlpatterns = [
    # Mapea http://127.0.0.1:8000/reportes/
    path('', views.index_reportes, name='reportes'),
    
    # Mapea http://127.0.0.1:8000/reportes/movimientos/
    path('movimientos/', views.reporte_movimientos, name='reporte_movimientos'),
]