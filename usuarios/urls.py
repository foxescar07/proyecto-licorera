from django.urls import path
from . import views

urlpatterns = [
    path('',                                views.lista_usuarios,           name='usuario'),
    path('login/',                          views.login_view,               name='login'),
    path('logout/',                         views.logout_view,              name='cerrar_sesion'),
    path('crear/',                          views.crear_usuario,            name='crear_usuario'),
    path('crear-ajax/',                     views.crear_usuario_ajax,       name='crear_usuario_ajax'),
    path('crear-modal/',                    views.crear_usuario_modal,      name='crear_usuario_modal'),
    path('crear-admin/',                    views.crear_usuario_admin,      name='crear_usuario_admin'),
    path('recuperar/',                      views.solicitar_recuperacion,   name='recuperar_clave'),
    path('recuperar/otp/',                  views.solicitar_otp_correo,     name='recuperar_otp_correo'),
    path('recuperar/otp/verificar/',        views.verificar_otp_correo,     name='verificar_otp_correo'),
    path('restablecer/<str:token>/',        views.restablecer_clave,        name='restablecer_clave'),
    path('perfil/',                         views.perfil_datos,             name='perfil_datos'),
    path('perfil/editar/',                  views.perfil_editar,            name='perfil_editar'),
    path('perfil/pagina/',                  views.perfil_pagina,            name='perfil_pagina'),
    path('perfil/foto/',                    views.actualizar_foto,          name='actualizar_foto'),
    path('editar/<int:pk>/',                views.editar_usuario,           name='editar_usuario'),
    path('toggle/<int:pk>/',                views.toggle_activo,            name='toggle_activo'),
    path('eliminar/<int:pk>/',              views.eliminar_usuario,         name='eliminar_usuario'),
    path('actividad/', views.actividad_usuarios, name='actividad_usuarios'),
]