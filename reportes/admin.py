from django.contrib import admin
from .models import Reporte


@admin.register(Reporte)
class ReporteAdmin(admin.ModelAdmin):
    list_display = (
        'codigo',
        'tipo_reporte',
        'formato',
        'documento_usuario',
        'fecha',
    )
    list_filter = ('tipo_reporte', 'formato', 'fecha')
    search_fields = ('observaciones', 'documento_usuario__username')
    readonly_fields = ('fecha',)
    date_hierarchy = 'fecha'
    ordering = ('-fecha',)

    fieldsets = (
        ('Información del Reporte', {
            'fields': ('tipo_reporte', 'formato', 'documento_usuario')
        }),
        ('Detalles', {
            'fields': ('observaciones',)
        }),
        ('Generación', {
            'fields': ('fecha',)
        }),
    )