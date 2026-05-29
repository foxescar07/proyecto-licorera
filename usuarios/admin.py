from django.contrib import admin
from .models import Perfil


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display  = ('nombre_completo', 'usuario', 'rol', 'activo', 'fecha_registro')
    list_filter   = ('rol', 'activo')
    search_fields = ('user__first_name', 'user__last_name', 'identificacion')