from django.contrib import admin
from django.utils.html import format_html
from .models import OperacionBase, DetalleOperacionBase, HistorialOperacionBase


class DetalleOperacionBaseInline(admin.TabularInline):
    """Detalles de la operación mostrados inline"""
    model = DetalleOperacionBase
    extra = 1
    fields = ('producto', 'presentacion', 'lote', 'cantidad', 'precio_unitario', 'descuento_linea', 'activo')
    readonly_fields = ()


class HistorialOperacionBaseInline(admin.TabularInline):
    """Historial de cambios mostrado inline (solo lectura)"""
    model = HistorialOperacionBase
    extra = 0
    fields = ('fecha', 'evento', 'usuario', 'descripcion')
    readonly_fields = ('fecha', 'evento', 'usuario', 'descripcion', 'valor_anterior', 'valor_nuevo')
    can_delete = False


@admin.register(OperacionBase)
class OperacionBaseAdmin(admin.ModelAdmin):
    """Administrador principal de operaciones base"""

    list_display = (
        'codigo',
        'tipo_operacion_badge',
        'estado_badge',
        'get_entidad',
        'total_format',
        'estado_pago_badge',
        'usuario_creador',
        'fecha_operacion',
    )

    list_filter = (
        'tipo_operacion',
        'estado',
        'estado_pago',
        'fecha_operacion',
        'usuario_creador',
    )

    search_fields = (
        'codigo',
        'proveedor__nombre_empresa',
        'cliente__nombre',
        'producto__nombre',
        'numero_factura',
        'numero_documento',
    )

    readonly_fields = (
        'codigo',
        'subtotal',
        'total',
        'saldo_pendiente',
        'fecha_creacion',
        'fecha_modificacion',
        'usuario_creador',
    )

    fieldsets = (
        ('IDENTIFICACIÓN', {
            'fields': ('codigo', 'tipo_operacion', 'estado', 'fecha_operacion')
        }),
        ('PROVEEDOR (si aplica)', {
            'fields': ('proveedor', 'orden_compra', 'compra_legacy', 'detalle_compra'),
            'classes': ('collapse',)
        }),
        ('CLIENTE (si aplica)', {
            'fields': ('cliente', 'venta', 'devolucion', 'detalle_venta'),
            'classes': ('collapse',)
        }),
        ('PRODUCTO & INVENTARIO', {
            'fields': ('producto', 'presentacion', 'lote', 'movimiento_inventario')
        }),
        ('DATOS OPERACIONALES', {
            'fields': (
                'cantidad',
                'precio_unitario',
                'descuento',
                'subtotal',
                'total',
            )
        }),
        ('PAGO', {
            'fields': (
                'metodo_pago',
                'estado_pago',
                'monto_pagado',
                'saldo_pendiente',
                'fecha_pago',
            ),
            'classes': ('collapse',)
        }),
        ('RECEPCIÓN/ENVÍO', {
            'fields': (
                'cantidad_recibida',
                'fecha_recepcion',
                'numero_factura',
                'numero_documento',
            ),
            'classes': ('collapse',)
        }),
        ('AUDITORÍA', {
            'fields': (
                'usuario_creador',
                'usuario_modificador',
                'usuario_autorizado',
                'fecha_creacion',
                'fecha_modificacion',
            ),
            'classes': ('collapse',)
        }),
        ('NOTAS', {
            'fields': ('notas', 'observaciones', 'motivo_cancelacion'),
            'classes': ('collapse',)
        }),
    )

    inlines = [DetalleOperacionBaseInline, HistorialOperacionBaseInline]

    def tipo_operacion_badge(self, obj):
        """Muestra el tipo de operación en color"""
        colors = {
            'compra_proveedor': '#3498db',
            'recepcion_compra': '#2ecc71',
            'venta_cliente': '#e74c3c',
            'devolucion_cliente': '#f39c12',
            'ajuste_inventario': '#9b59b6',
            'pago_proveedor': '#1abc9c',
        }
        color = colors.get(obj.tipo_operacion, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_tipo_operacion_display()
        )
    tipo_operacion_badge.short_description = 'Tipo'

    def estado_badge(self, obj):
        """Muestra el estado en color"""
        colors = {
            'pendiente': '#95a5a6',
            'en_proceso': '#f39c12',
            'completada': '#2ecc71',
            'cancelada': '#e74c3c',
            'rechazada': '#c0392b',
        }
        color = colors.get(obj.estado, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'

    def estado_pago_badge(self, obj):
        """Muestra el estado de pago en color"""
        colors = {
            'pendiente': '#e74c3c',
            'parcial': '#f39c12',
            'pagada': '#2ecc71',
        }
        color = colors.get(obj.estado_pago, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_estado_pago_display()
        )
    estado_pago_badge.short_description = 'Pago'

    def get_entidad(self, obj):
        """Muestra la entidad relacionada (proveedor o cliente)"""
        if obj.proveedor:
            return f"Proveedor: {obj.proveedor.nombre_empresa}"
        elif obj.cliente:
            return f"Cliente: {obj.cliente.nombre}"
        return "—"
    get_entidad.short_description = 'Entidad'

    def total_format(self, obj):
        """Muestra el total formateado"""
        return f"${obj.total:,.2f}"
    total_format.short_description = 'Total'

    actions = ['marcar_completada', 'marcar_cancelada']

    def marcar_completada(self, request, queryset):
        """Acción para marcar operaciones como completadas"""
        updated = queryset.update(estado='completada')
        self.message_user(request, f'{updated} operación(es) marcada(s) como completada(s).')
    marcar_completada.short_description = "Marcar como Completada"

    def marcar_cancelada(self, request, queryset):
        """Acción para marcar operaciones como canceladas"""
        updated = queryset.update(estado='cancelada')
        self.message_user(request, f'{updated} operación(es) cancelada(s).')
    marcar_cancelada.short_description = "Marcar como Cancelada"


@admin.register(DetalleOperacionBase)
class DetalleOperacionBaseAdmin(admin.ModelAdmin):
    """Administrador de detalles de operación"""

    list_display = ('operacion', 'producto', 'cantidad', 'precio_unitario', 'subtotal', 'descuento_linea', 'total', 'activo')
    list_filter = ('activo', 'operacion__tipo_operacion', 'fecha_creacion')
    search_fields = ('operacion__codigo', 'producto__nombre')
    readonly_fields = ('subtotal', 'total', 'fecha_creacion')

    fieldsets = (
        ('OPERACIÓN', {
            'fields': ('operacion',)
        }),
        ('PRODUCTO', {
            'fields': ('producto', 'presentacion', 'lote')
        }),
        ('CANTIDAD Y PRECIOS', {
            'fields': ('cantidad', 'precio_unitario', 'descuento_linea', 'subtotal', 'total')
        }),
        ('INFORMACIÓN DE LOTE', {
            'fields': ('numero_lote', 'fecha_vencimiento'),
            'classes': ('collapse',)
        }),
        ('CONTROL', {
            'fields': ('orden_linea', 'activo', 'fecha_creacion'),
            'classes': ('collapse',)
        }),
    )


@admin.register(HistorialOperacionBase)
class HistorialOperacionBaseAdmin(admin.ModelAdmin):
    """Administrador del historial de operaciones (solo lectura)"""

    list_display = ('operacion', 'evento', 'usuario', 'fecha', 'descripcion')
    list_filter = ('evento', 'fecha', 'usuario')
    search_fields = ('operacion__codigo', 'usuario__username', 'descripcion')
    readonly_fields = ('operacion', 'evento', 'usuario', 'fecha', 'descripcion', 'valor_anterior', 'valor_nuevo')

    fieldsets = (
        ('INFORMACIÓN', {
            'fields': ('operacion', 'evento', 'usuario', 'fecha')
        }),
        ('DETALLES', {
            'fields': ('descripcion', 'valor_anterior', 'valor_nuevo'),
        }),
    )

    def has_add_permission(self, request):
        """No permitir agregar historial manual"""
        return False

    def has_delete_permission(self, request, obj=None):
        """No permitir eliminar historial"""
        return False
