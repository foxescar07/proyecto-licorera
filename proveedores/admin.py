from django.contrib import admin
from .models import Proveedor, Compra


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre_empresa', 'email', 'tipo_proveedor', 'estado', 'fecha_registro')
    list_filter = ('estado', 'tipo_proveedor', 'fecha_registro')
    search_fields = ('nombre_empresa', 'email', 'nombre_contacto')
    readonly_fields = ('fecha_registro', 'ultima_modificacion', 'registrado_por', 'modificado_por')
    fieldsets = (
        ('Información General', {
            'fields': ('nombre_empresa', 'nombre_contacto', 'email', 'telefono')
        }),
        ('Clasificación', {
            'fields': ('tipo_proveedor', 'categorias_surtidas')
        }),
        ('Estado', {
            'fields': ('estado', 'motivo_sancion')
        }),
        ('Auditoría', {
            'fields': ('fecha_registro', 'ultima_modificacion', 'registrado_por', 'modificado_por'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.registrado_por = request.user
        obj.modificado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ('proveedor', 'producto', 'cantidad', 'precio_unitario', 'total', 'fecha_registro', 'recibida')
    list_filter = ('proveedor', 'fecha_registro', 'recibida')
    search_fields = ('proveedor__nombre_empresa', 'producto__nombre')
    readonly_fields = ('fecha_registro', 'total')
    fieldsets = (
        ('Información de Compra', {
            'fields': ('proveedor', 'producto', 'cantidad', 'precio_unitario')
        }),
        ('Detalles', {
            'fields': ('lote', 'recibida', 'fecha_registro')
        }),
        ('Total', {
            'fields': ('total',),
            'classes': ('wide',)
        }),
    )
