from django.contrib import admin
from django.utils.html import format_html
from .models import Proveedor, Compra, HistorialCompra


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre_empresa', 'email', 'tipo_proveedor', 'estado', 'fecha_registro')
    list_filter = ('estado', 'tipo_proveedor', 'fecha_registro')
    search_fields = ('nombre_empresa', 'email')
    readonly_fields = ('fecha_registro', 'registrado_por')
    fieldsets = (
        ('Información General', {
            'fields': ('nombre_empresa', 'nit', 'email', 'telefono')
        }),
        ('Clasificación', {
            'fields': ('tipo_proveedor',)
        }),
        ('Estado y Observaciones', {
            'fields': ('estado', 'observacion')
        }),
        ('Auditoría', {
            'fields': ('fecha_registro', 'registrado_por'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.registrado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ('proveedor', 'valor', 'saldo', 'estado', 'fecha')
    list_filter = ('proveedor', 'estado', 'fecha')
    search_fields = ('proveedor__nombre_empresa',)
    readonly_fields = ('fecha', 'documento_usuario')
    fieldsets = (
        ('Información de Compra', {
            'fields': ('proveedor', 'documento_usuario', 'fecha', 'estado')
        }),
        ('Valores', {
            'fields': ('valor', 'saldo')
        }),
        ('Detalles', {
            'fields': ('motivo_pago', 'observacion')
        }),
    )


@admin.register(HistorialCompra)
class HistorialCompraAdmin(admin.ModelAdmin):
    list_display = ('compra', 'evento', 'usuario', 'fecha')
    list_filter = ('evento', 'fecha')
    search_fields = ('compra__id', 'descripcion')
    readonly_fields = ('fecha', 'compra', 'evento', 'usuario')
    fieldsets = (
        ('Evento', {
            'fields': ('compra', 'evento', 'usuario', 'fecha')
        }),
        ('Descripción', {
            'fields': ('descripcion',)
        }),
    )
