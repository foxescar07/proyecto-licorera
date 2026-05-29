from django.contrib import admin
from .models import SesionConteo, ConteoProducto, ResultadoInventario, Lote, Inventario, AgendaInventario


@admin.register(SesionConteo)
class SesionConteoAdmin(admin.ModelAdmin):
    list_display = ['fecha_inicio', 'estado']


@admin.register(ConteoProducto)
class ConteoProductoAdmin(admin.ModelAdmin):
    list_display  = ['sesion', 'presentacion', 'cantidad_contada']
    search_fields = ['presentacion__producto__nombre']


@admin.register(ResultadoInventario)
class ResultadoInventarioAdmin(admin.ModelAdmin):
    list_display = ['sesion', 'presentacion', 'cantidad_sistema', 'cantidad_fisica', 'diferencia']


@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display  = ['numero_lote', 'presentacion', 'fecha_vencimiento']
    search_fields = ['numero_lote', 'presentacion__producto__nombre']


@admin.register(Inventario)
class InventarioAdmin(admin.ModelAdmin):
    list_display = ['tipo', 'presentacion', 'cantidad', 'fecha_actualizada']
    list_filter  = ['tipo']


@admin.register(AgendaInventario)
class AgendaInventarioAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'fecha_programada', 'estado']
    list_filter  = ['estado']
