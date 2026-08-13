from django.urls import path
from . import views

app_name = 'configuracion'

urlpatterns = [
    path('',                    views.index,                   name='index'),
    path('empresa/',            views.guardar_empresa,         name='guardar_empresa'),
    path('empresa/verificar/',  views.verificar_clave_empresa, name='verificar_clave_empresa'),
    path('empresa/bloquear/',   views.bloquear_empresa,        name='bloquear_empresa'),
    path('impuestos/',          views.guardar_impuestos,       name='guardar_impuestos'),
    path('backup/',             views.crear_backup,            name='crear_backup'),
]