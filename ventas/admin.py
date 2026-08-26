from django.contrib import admin # type: ignore
from .models import Cliente, Venta, DetalleVenta, AperturaCaja, CierreCaja, Devolucion, DetalleDevolucion, MetodoPago


class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 0
    raw_id_fields = ['codigo_producto', 'codigo_presentacion', 'codigo_lote']
    fields = ['codigo_producto', 'codigo_presentacion', 'codigo_lote', 'cantidad', 'precio_unitario', 'subtotal_display']
    readonly_fields = ['subtotal_display']

    def subtotal_display(self, obj):
        return f"${obj.subtotal:,.2f}" if obj.pk else "$0.00"
    subtotal_display.short_description = "Subtotal"


class DetalleDevolucionInline(admin.TabularInline):
    model = DetalleDevolucion
    extra = 0
    raw_id_fields = ['presentacion', 'codigo_lote']
    fields = ['presentacion', 'codigo_lote', 'cantidad', 'precio_unitario', 'subtotal']
    readonly_fields = ['subtotal']

    def subtotal_display(self, obj):
        return f"${obj.subtotal:,.2f}" if obj.pk else "$0.00"
    subtotal_display.short_description = "Subtotal"


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['identificacion', 'tipo_id', 'nombre', 'telefono', 'correo_personal']
    search_fields = ['identificacion', 'nombre']
    list_filter = ['tipo_id']


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ['id', 'codigo_cliente', 'documento_usuario', 'fecha', 'total_venta', 'metodo_pago']
    search_fields = ['id', 'codigo_cliente__nombre']
    list_filter = ['fecha', 'documento_usuario', 'metodo_pago']
    inlines = [DetalleVentaInline]
    date_hierarchy = 'fecha'


@admin.register(MetodoPago)
class MetodoPagoAdmin(admin.ModelAdmin):
    list_display = ['codigo_metodo', 'codigo_venta', 'fecha', 'valor', 'referencia', 'efectivo', 'transaccion']
    search_fields = ['codigo_metodo', 'referencia', 'transaccion']
    list_filter = ['fecha']


@admin.register(AperturaCaja)
class AperturaCajaAdmin(admin.ModelAdmin):
    list_display = ['fecha', 'documento_usuario', 'monto_base', 'creado_en']
    list_filter = ['fecha', 'documento_usuario']


@admin.register(CierreCaja)
class CierreCajaAdmin(admin.ModelAdmin):
    list_display = ['fecha', 'documento_usuario', 'total_contado', 'total_retirado']
    list_filter = ['fecha', 'documento_usuario']


@admin.register(Devolucion)
class DevolucionAdmin(admin.ModelAdmin):
    list_display = ['id', 'codigo_venta', 'documento_usuario', 'fecha', 'total_devuelto']
    list_filter = ['motivo', 'fecha']
    inlines = [DetalleDevolucionInline]
    raw_id_fields = ['codigo_venta']