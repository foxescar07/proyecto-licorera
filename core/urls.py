from django.contrib import admin
from django.urls import path, include
from principal import views as principal_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Página principal
    path('', principal_views.principal, name='principal'),

    # App usuarios
    path('usuarios/', include('usuarios.urls')),
    
    # App productos e inventario
    path('productos/', include('productos.urls', namespace='producto')),
    path('inventario/', include('inventario.urls', namespace='inventario')),
    
    # App reportes
    path('reportes/', include('reportes.urls', namespace='reportes')),
]