from django.contrib import admin
from .models import Categoria, Producto, PresentacionProducto
# ─────────────────────────────────────────────
#  Inline: Presentaciones dentro de Producto
# ─────────────────────────────────────────────
class PresentacionProductoInline(admin.TabularInline):
    model          = PresentacionProducto
    extra          = 1
    fields         = ["nombre", "unidades", "cantidad", "precio"]
    show_change_link = True


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
    list_display    = ["codigo", "nombre", "categoria", "unidad", "precio_unitario", "stock_critico"]
    list_filter     = ["categoria", "unidad"]
    search_fields   = ["codigo", "nombre"]
    ordering        = ["nombre"]
    readonly_fields = ["stock_critico"]
    inlines         = [PresentacionProductoInline]

    def get_list_display_links(self, request, list_display):
        return ["nombre"]

    @admin.display(boolean=True, description="Stock crítico")
    def stock_critico(self, obj):
        return obj.stock_critico


# ─────────────────────────────────────────────
#  Presentación de Producto
# ─────────────────────────────────────────────
@admin.register(PresentacionProducto)
class PresentacionProductoAdmin(admin.ModelAdmin):
    list_display  = ["producto", "nombre", "unidades", "cantidad", "precio"]
    list_filter   = ["producto__categoria"]
    search_fields = ["nombre", "producto__nombre", "producto__codigo"]
    ordering      = ["producto__nombre", "unidades"]