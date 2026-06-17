from django.urls import path
from . import views

urlpatterns = [
    path('',                                views.lista_usuarios,          name='usuario'),
    path('login/',                          views.login_view,              name='login'),
    path('logout/',                         views.logout_view,             name='cerrar_sesion'),
    path('crear/',                          views.crear_usuario,           name='crear_usuario'),
    path('recuperar/',                      views.solicitar_recuperacion,  name='recuperar_clave'),
    path('recuperar/telefono/',             views.recuperar_por_telefono,  name='recuperar_por_telefono'),
    path('recuperar/telefono/verificar/',   views.verificar_codigo_telefono, name='verificar_codigo_telefono'),
    path('restablecer/<str:token>/',        views.restablecer_clave,       name='restablecer_clave'),
    path('perfil/',                         views.perfil_datos,            name='perfil_datos'),
    path('perfil/editar/',                  views.perfil_editar,           name='perfil_editar'),
    path('perfil/pagina/',                  views.perfil_pagina,           name='perfil_pagina'),
    path('perfil/foto/',                    views.actualizar_foto,         name='actualizar_foto'),
    path('editar/<int:pk>/',                views.editar_usuario,          name='editar_usuario'),
    path('toggle/<int:pk>/',                views.toggle_activo,           name='toggle_activo'),
    path('eliminar/<int:pk>/',              views.eliminar_usuario,        name='eliminar_usuario'),
]