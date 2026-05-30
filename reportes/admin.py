from django.contrib import admin
from .models import ReporteGenerado

@admin.register(ReporteGenerado)
class ReporteGeneradoAdmin(admin.ModelAdmin):
    # Columnas que se verán en la lista principal
    list_display = ('titulo', 'tipo', 'fecha_creacion', 'usuario')
    
    # Filtros laterales para encontrar reportes rápido
    list_filter = ('tipo', 'fecha_creacion', 'usuario')
    
    # Buscador por título
    search_fields = ('titulo',)
    
    # Campos de solo lectura (la fecha se pone sola)
    readonly_fields = ('fecha_creacion',)

    # Organización de los campos al editar/ver un reporte
    fieldsets = (
        ('Información General', {
            'fields': ('titulo', 'tipo', 'usuario')
        }),
        ('Contenido', {
            'fields': ('archivo', 'fecha_creacion')
        }),
    )