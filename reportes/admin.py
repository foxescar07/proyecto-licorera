from django.contrib import admin
from .models import (
    ReporteVenta,
    ReporteInventario,
    ReporteCaja,
    ReporteCompra,
    ReporteDevolucion,
    ReporteLote
)


@admin.register(ReporteVenta)
class ReporteVentaAdmin(admin.ModelAdmin):
    list_display = ('id', 'venta_id', 'cliente_id', 'total', 'fecha', 'generado_en')
    list_filter = ('fecha', 'generado_en', 'vendedor_id')
    search_fields = ('cliente_id', 'venta_id')
    readonly_fields = ('generado_en',)
    
    fieldsets = (
        ('Información de Venta', {
            'fields': ('venta_id', 'cliente_id', 'vendedor_id')
        }),
        ('Detalles', {
            'fields': ('presentacion_id', 'total', 'fecha')
        }),
        ('Generación', {
            'fields': ('generado_en',)
        }),
    )


@admin.register(ReporteInventario)
class ReporteInventarioAdmin(admin.ModelAdmin):
    list_display = ('id', 'presentacion_id', 'lote_id', 'stock_sistema', 'stock_fisico', 'diferencia', 'estado_lote')
    list_filter = ('estado_lote', 'generado_en', 'fecha_vencimiento')
    search_fields = ('presentacion_id', 'lote_id')
    readonly_fields = ('generado_en', 'diferencia')
    
    fieldsets = (
        ('Información de Producto', {
            'fields': ('presentacion_id', 'lote_id')
        }),
        ('Stock', {
            'fields': ('stock_sistema', 'stock_fisico', 'diferencia')
        }),
        ('Lote', {
            'fields': ('estado_lote', 'fecha_vencimiento', 'sesion_conteo_id')
        }),
        ('Generación', {
            'fields': ('generado_en',)
        }),
    )


@admin.register(ReporteCaja)
class ReporteCajaAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario_id', 'total_ventas', 'total_devoluciones', 'total_contado', 'diferencia', 'generado_en')
    list_filter = ('generado_en', 'usuario_id')
    search_fields = ('usuario_id',)
    readonly_fields = ('generado_en',)
    
    fieldsets = (
        ('Apertura y Cierre', {
            'fields': ('apertura_id', 'cierre_id', 'usuario_id')
        }),
        ('Movimientos', {
            'fields': ('total_ventas', 'total_devoluciones', 'total_contado', 'diferencia')
        }),
        ('Generación', {
            'fields': ('generado_en',)
        }),
    )


@admin.register(ReporteCompra)
class ReporteCompraAdmin(admin.ModelAdmin):
    list_display = ('id', 'orden_compra_id', 'proveedor_id', 'total', 'estado_orden', 'fecha', 'generado_en')
    list_filter = ('estado_orden', 'fecha', 'generado_en')
    search_fields = ('orden_compra_id', 'proveedor_id')
    readonly_fields = ('generado_en',)
    
    fieldsets = (
        ('Información de Orden', {
            'fields': ('orden_compra_id', 'proveedor_id')
        }),
        ('Detalles', {
            'fields': ('presentacion_id', 'total', 'estado_orden', 'fecha')
        }),
        ('Generación', {
            'fields': ('generado_en',)
        }),
    )


@admin.register(ReporteDevolucion)
class ReporteDevolucioAdmin(admin.ModelAdmin):
    list_display = ('id', 'devolucion_id', 'cliente_id', 'total_devuelto', 'motivo', 'fecha', 'generado_en')
    list_filter = ('fecha', 'generado_en')
    search_fields = ('cliente_id', 'motivo')
    readonly_fields = ('generado_en',)
    
    fieldsets = (
        ('Información de Devolución', {
            'fields': ('devolucion_id', 'venta_id', 'cliente_id')
        }),
        ('Detalles', {
            'fields': ('total_devuelto', 'motivo', 'fecha')
        }),
        ('Generación', {
            'fields': ('generado_en',)
        }),
    )


@admin.register(ReporteLote)
class ReporteLoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'lote_id', 'presentacion_id', 'stock_actual', 'dias_para_vencer', 'estado', 'fecha_vencimiento')
    list_filter = ('estado', 'fecha_vencimiento', 'generado_en')
    search_fields = ('lote_id', 'presentacion_id')
    readonly_fields = ('generado_en',)
    
    fieldsets = (
        ('Información de Lote', {
            'fields': ('lote_id', 'presentacion_id')
        }),
        ('Inventario', {
            'fields': ('stock_actual', 'costo_unitario')
        }),
        ('Vencimiento', {
            'fields': ('fecha_vencimiento', 'dias_para_vencer', 'estado')
        }),
        ('Generación', {
            'fields': ('generado_en',)
        }),
    )