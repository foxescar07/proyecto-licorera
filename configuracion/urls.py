from django.urls import path
from . import views

app_name = 'configuracion'

urlpatterns = [
    path('',               views.index,           name='index'),
    path('empresa/',       views.guardar_empresa,  name='guardar_empresa'),
    path('impuestos/',     views.guardar_impuestos, name='guardar_impuestos'),
    path('backup/',        views.crear_backup,     name='crear_backup'),
]