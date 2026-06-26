from django.contrib import admin
from .models import ConfiguracionEmpresa, BackupRegistro

@admin.register(ConfiguracionEmpresa)
class ConfiguracionEmpresaAdmin(admin.ModelAdmin):
    list_display = ('nombre_empresa', 'nit', 'moneda', 'iva_porcentaje')

@admin.register(BackupRegistro)
class BackupRegistroAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'fecha', 'tamaño_mb')
    readonly_fields = ('fecha',)