from django.contrib import admin # type: ignore
from .models import Cliente, Venta, DetalleVenta, AperturaCaja, CierreCaja, Devolucion, DetalleDevolucion


class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 0
    raw_id_fields = ['producto', 'presentacion', 'lote']
    fields = ['producto', 'presentacion', 'lote', 'cantidad', 'precio_unitario', 'subtotal_display']
    readonly_fields = ['subtotal_display']

    def subtotal_display(self, obj):
        return f"${obj.subtotal():,.2f}" if obj.pk else "$0.00"
    subtotal_display.short_description = "Subtotal"


class DetalleDevolucionInline(admin.TabularInline):
    model = DetalleDevolucion
    extra = 0
    raw_id_fields = ['presentacion', 'lote']
    fields = ['presentacion', 'lote', 'cantidad', 'precio_unitario', 'subtotal_display']
    readonly_fields = ['subtotal_display']

    def subtotal_display(self, obj):
        return f"${obj.subtotal():,.2f}" if obj.pk else "$0.00"
    subtotal_display.short_description = "Subtotal"


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['identificacion', 'tipo_id', 'nombre', 'telefono', 'email']
    search_fields = ['identificacion', 'nombre']
    list_filter = ['tipo_id']


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ['id', 'cliente', 'vendedor', 'fecha', 'total_con_descuento_display', 'metodos_pago_resumen']
    search_fields = ['id', 'cliente__nombre']
    list_filter = ['fecha', 'vendedor']
    inlines = [DetalleVentaInline]
    date_hierarchy = 'fecha'

    def total_con_descuento_display(self, obj): return f"${obj.total_con_descuento:,.2f}"
    total_con_descuento_display.short_description = "Total"

    def metodos_pago_resumen(self, obj):
        p = []
        if obj.pago_efectivo: p.append(f"Efec: ${obj.pago_efectivo:,.0f}")
        if obj.pago_tarjeta: p.append(f"Tarj: ${obj.pago_tarjeta:,.0f}")
        if obj.pago_nequi: p.append(f"Nequi: ${obj.pago_nequi:,.0f}")
        return ", ".join(p) if p else "Sin pagos"
    metodos_pago_resumen.short_description = "Pagos"


@admin.register(AperturaCaja)
class AperturaCajaAdmin(admin.ModelAdmin):
    list_display = ['fecha', 'usuario', 'monto_base', 'creado_en']
    list_filter = ['fecha', 'usuario']


@admin.register(CierreCaja)
class CierreCajaAdmin(admin.ModelAdmin):
    list_display = ['fecha', 'usuario', 'total_contado', 'total_retirado']
    list_filter = ['fecha', 'usuario']


@admin.register(Devolucion)
class DevolucionAdmin(admin.ModelAdmin):
    list_display = ['numero', 'venta', 'registrado_por', 'fecha', 'total_devuelto']
    list_filter = ['motivo', 'fecha']
    inlines = [DetalleDevolucionInline]
    raw_id_fields = ['venta']