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

# ════════════════════════════════════════
# DEVOLUCIONES
# ════════════════════════════════════════
class Venta(models.Model):
    cliente = models.CharField(max_length=200, default='Cliente general')
    fecha = models.DateTimeField(auto_now_add=True)
    total_venta = models.DecimalField(max_digits=12, decimal_places=2, default=0)


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

    def __str__(self):
        return f'VTA-{self.pk:04d} | {self.cliente} — {self.fecha:%d/%m/%Y}'


class DetalleVenta(models.Model):
    venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        related_name='detalles',
    )
    presentacion = models.ForeignKey(
        'productos.PresentacionProducto',
        on_delete=models.PROTECT,
        null=True, blank=True,
    )
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)


    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def __str__(self):
        return f"{self.producto.nombre} x{self.cantidad}"

    class Meta:
        verbose_name = 'Detalle de venta'
        verbose_name_plural = 'Detalles de venta'

    class Meta:
        verbose_name = 'Detalle de Venta'
        verbose_name_plural = 'Detalles de Venta'

class Devolucion(models.Model):

    MOTIVO_CHOICES = [
        ('defectuoso',   'Producto defectuoso'),
        ('equivocado',   'Producto equivocado'),
        ('insatisfecho', 'Cliente insatisfecho'),
        ('otro',         'Otro'),
    ]

    REEMBOLSO_CHOICES = [
        ('cambio',       'Cambio de producto'),
        ('nota_credito', 'Nota crédito'),
        ('reembolso',    'Reembolso'),
    ]

    venta = models.ForeignKey(
        'ventas.Venta',                  # ✅ String en lugar de importar la clase
        on_delete=models.PROTECT,
        related_name='devoluciones',
        verbose_name='Venta original',
    )

    fecha = models.DateTimeField(
        auto_now_add=True
    )

    motivo = models.CharField(
        max_length=20,
        choices=MOTIVO_CHOICES,
        default='otro',
    )

    tipo_reembolso = models.CharField(
        max_length=20,
        choices=REEMBOLSO_CHOICES,
        default='cambio',
    )

    observaciones = models.TextField(
        blank=True
    )

    total_devuelto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    class Meta:
        verbose_name        = 'Devolución'
        verbose_name_plural = 'Devoluciones'
        ordering            = ['-fecha']

    def __str__(self):
        return f'DEV-{self.pk:04d} | {self.venta.cliente} — {self.fecha:%d/%m/%Y %H:%M}'

    @property
    def numero(self):
        return f'DEV-{self.pk:04d}'


class DetalleDevolucion(models.Model):

    devolucion = models.ForeignKey(
        Devolucion,
        on_delete=models.CASCADE,
        related_name='detalles',
    )

    detalle_venta = models.ForeignKey(
        'ventas.DetalleVenta',           # ✅ String en lugar de importar la clase
        on_delete=models.PROTECT,
        related_name='devoluciones',
    )

    cantidad = models.PositiveIntegerField()

    estado_producto = models.CharField(
        max_length=50,
        blank=True,
        default='',
    )

    observacion = models.TextField(
        blank=True,
        default='',
    )

    class Meta:
        verbose_name        = 'Detalle de Devolución'
        verbose_name_plural = 'Detalles de Devolución'

    def subtotal(self):
        return self.cantidad * self.detalle_venta.precio_unitario

    def __str__(self):
        pres = self.detalle_venta.presentacion
        if pres:
            prod = pres.producto.nombre
            return f'{prod} ({pres.nombre}) x{self.cantidad}'
        return f'Producto x{self.cantidad}'

