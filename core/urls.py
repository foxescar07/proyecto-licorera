from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from principal import views as principal_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Página principal
    path('', principal_views.principal, name='principal'),

    # App usuarios
    path('usuarios/', include('usuarios.urls')),

    # App productos e inventario
    path('productos/', include('productos.urls')),
    path('inventario/', include('inventario.urls')),

    # App reportes
    path('reportes/', include('reportes.urls')),

    # App ventas
    path('ventas/', include('ventas.urls')),

    # App proveedores
    path('proveedores/', include('proveedores.urls')),

    # App configuracion
    path('configuracion/', include('configuracion.urls')),
    
    path('ayuda/', include('ayuda.urls')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)