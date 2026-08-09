from django.contrib import admin
from .models import (
    AgendaInventario,
    Hallazgo,
    Inventario,
    Lote,
    MovimientoInventario,
)


@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display  = ['numero_lote', 'presentacion', 'stock_actual', 'fecha_vencimiento']
    search_fields = ['numero_lote', 'presentacion__producto__nombre']
    list_filter   = ['fecha_vencimiento']


@admin.register(Inventario)
class InventarioAdmin(admin.ModelAdmin):
    list_display  = ['producto', 'presentacion', 'stock_actual', 'stock_min', 'stock_max']
    search_fields = ['producto__nombre']


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = ['tipo', 'inventario', 'lote', 'cantidad', 'fecha']
    list_filter  = ['tipo']


@admin.register(AgendaInventario)
class AgendaInventarioAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'fecha', 'estado', 'responsable']
    list_filter  = ['estado']


@admin.register(Hallazgo)
class HallazgoAdmin(admin.ModelAdmin):
    list_display = ['agenda', 'producto', 'cantidad_sistema', 'cantidad_fisica', 'diferencia', 'tipo_hallazgo']
    list_filter  = ['tipo_hallazgo']