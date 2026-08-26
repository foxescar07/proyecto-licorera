from django.contrib import admin
from .models import (
    Usuario, Bodega, Categoria, Producto, PresentacionProducto,
    Lote, Marca, DetalleProducto, Proveedor, Compra, DetalleCompra,
    DevolucionProveedores, Venta, DetalleVenta, Devolucion, DetalleDevolucion,
    MetodoPago, Caja
)

admin.site.register(Usuario)
admin.site.register(Bodega)
admin.site.register(Categoria)
admin.site.register(Producto)
admin.site.register(PresentacionProducto)
admin.site.register(Lote)
admin.site.register(Marca)
admin.site.register(DetalleProducto)
admin.site.register(Proveedor)
admin.site.register(Compra)
admin.site.register(DetalleCompra)
admin.site.register(DevolucionProveedores)
admin.site.register(Venta)
admin.site.register(DetalleVenta)
admin.site.register(Devolucion)
admin.site.register(DetalleDevolucion)
admin.site.register(MetodoPago)
admin.site.register(Caja)
