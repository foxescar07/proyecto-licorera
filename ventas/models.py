from django.db import models
from productos.models import Producto, PresentacionProducto


class Venta(models.Model):
    cliente = models.CharField(max_length=200, default='Cliente general')
    fecha = models.DateTimeField(auto_now_add=True)
    descuento_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    @property
    def total_venta(self):
        subtotal = sum(det.subtotal() for det in self.detalles.all())
        descuento = subtotal * (self.descuento_porcentaje / 100)
        return subtotal - descuento

    def __str__(self):
        return f"Venta #{self.pk} - {self.cliente} - {self.fecha.strftime('%Y-%m-%d')}"

    class Meta:
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'
        ordering = ['-fecha']


class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    presentacion = models.ForeignKey(PresentacionProducto, on_delete=models.PROTECT, null=True, blank=True)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def __str__(self):
        return f"{self.producto.nombre} x{self.cantidad}"

    class Meta:
        verbose_name = 'Detalle de venta'
        verbose_name_plural = 'Detalles de venta'