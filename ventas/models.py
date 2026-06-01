from django.db import models
from productos.models import Producto, PresentacionProducto


# ════════════════════════════════════════
# VENTAS
# ════════════════════════════════════════
class Venta(models.Model):
    cliente = models.CharField(
        max_length=200,
        default='Cliente general'
    )

    fecha = models.DateTimeField(
        auto_now_add=True
    )

    descuento_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    class Meta:
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'
        ordering = ['-fecha']

    @property
    def total_venta(self):
        subtotal = sum(
            detalle.subtotal()
            for detalle in self.detalles.all()
        )

        descuento = subtotal * (
            self.descuento_porcentaje / 100
        )

        return subtotal - descuento

    def __str__(self):
        return (
            f'VTA-{self.pk:04d} | '
            f'{self.cliente} — '
            f'{self.fecha:%d/%m/%Y}'
        )


# ════════════════════════════════════════
# DETALLE DE VENTA
# ════════════════════════════════════════
class DetalleVenta(models.Model):

    venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        related_name='detalles'
    )

    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT
    )

    presentacion = models.ForeignKey(
        PresentacionProducto,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    cantidad = models.PositiveIntegerField(
        default=1
    )

    precio_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    class Meta:
        verbose_name = 'Detalle de Venta'
        verbose_name_plural = 'Detalles de Venta'

    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def __str__(self):
        return (
            f'{self.producto.nombre} '
            f'x{self.cantidad}'
        )


# ════════════════════════════════════════
# DEVOLUCIONES
# ════════════════════════════════════════
class Devolucion(models.Model):

    MOTIVO_CHOICES = [
        ('defectuoso', 'Producto defectuoso'),
        ('equivocado', 'Producto equivocado'),
        ('insatisfecho', 'Cliente insatisfecho'),
        ('otro', 'Otro'),
    ]

    REEMBOLSO_CHOICES = [
        ('cambio', 'Cambio de producto'),
        ('nota_credito', 'Nota crédito'),
        ('reembolso', 'Reembolso'),
    ]

    venta = models.ForeignKey(
        Venta,
        on_delete=models.PROTECT,
        related_name='devoluciones',
        verbose_name='Venta original'
    )

    fecha = models.DateTimeField(
        auto_now_add=True
    )

    motivo = models.CharField(
        max_length=20,
        choices=MOTIVO_CHOICES,
        default='otro'
    )

    tipo_reembolso = models.CharField(
        max_length=20,
        choices=REEMBOLSO_CHOICES,
        default='cambio'
    )

    observaciones = models.TextField(
        blank=True
    )

    total_devuelto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    class Meta:
        verbose_name = 'Devolución'
        verbose_name_plural = 'Devoluciones'
        ordering = ['-fecha']

    @property
    def numero(self):
        return f'DEV-{self.pk:04d}'

    def __str__(self):
        return (
            f'DEV-{self.pk:04d} | '
            f'{self.venta.cliente} — '
            f'{self.fecha:%d/%m/%Y %H:%M}'
        )


# ════════════════════════════════════════
# DETALLE DEVOLUCIÓN
# ════════════════════════════════════════
class DetalleDevolucion(models.Model):

    devolucion = models.ForeignKey(
        Devolucion,
        on_delete=models.CASCADE,
        related_name='detalles'
    )

    detalle_venta = models.ForeignKey(
        DetalleVenta,
        on_delete=models.PROTECT,
        related_name='devoluciones'
    )

    cantidad = models.PositiveIntegerField()

    estado_producto = models.CharField(
        max_length=50,
        blank=True,
        default=''
    )

    observacion = models.TextField(
        blank=True,
        default=''
    )

    class Meta:
        verbose_name = 'Detalle de Devolución'
        verbose_name_plural = 'Detalles de Devolución'

    def subtotal(self):
        return (
            self.cantidad *
            self.detalle_venta.precio_unitario
        )

    def __str__(self):
        pres = self.detalle_venta.presentacion

        if pres:
            return (
                f'{pres.producto.nombre} '
                f'({pres.nombre}) '
                f'x{self.cantidad}'
            )

        return f'Producto x{self.cantidad}'