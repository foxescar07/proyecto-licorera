from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display  = ('username', 'nombre_completo', 'rol', 'activo', 'date_joined')
    list_filter   = ('rol', 'activo', 'is_staff', 'is_superuser')
    search_fields = ('first_name', 'last_name', 'identificacion', 'username')
    fieldsets = UserAdmin.fieldsets + (
        ('Información Extra', {
            'fields': ('tipo_id', 'identificacion', 'telefono', 'rol', 'activo', 'foto')
        }),
    )