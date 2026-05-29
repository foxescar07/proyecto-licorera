from django.contrib import admin
from .models import Categoria, Producto
from inventario.models import Inventario, AgendaInventario


# ─────────────────────────────────────────────
#  (Inline removido porque Inventario ya no enlaza directo a Producto)
# ─────────────────────────────────────────────


# ─────────────────────────────────────────────
#  Categoría
# ─────────────────────────────────────────────
@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display  = ["codigo", "nombre", "descripcion"]
    search_fields = ["codigo", "nombre"]
    ordering      = ["nombre"]


# ─────────────────────────────────────────────
#  Producto
# ─────────────────────────────────────────────
@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display   = ["codigo", "nombre", "categoria", "unidad", "precio_unitario", "stock_critico"]
    list_filter    = ["categoria", "unidad"]
    search_fields  = ["codigo", "nombre"]
    ordering       = ["nombre"]
    readonly_fields = ["stock_critico"]

    # Resalta en rojo los productos con stock crítico
    def get_list_display_links(self, request, list_display):
        return ["nombre"]

    @admin.display(boolean=True, description="Stock crítico")
    def stock_critico(self, obj):
        return obj.stock_critico
