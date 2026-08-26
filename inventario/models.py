from django.conf import settings
from django.db import models
from django.utils import timezone
from productos.models import Producto, PresentacionProducto

class Lote(models.Model):
    numero_lote = models.CharField(max_length=100, unique=True)
    presentacion = models.ForeignKey(
        PresentacionProducto, on_delete=models.PROTECT, related_name="lotes"
    )
    stock_actual = models.PositiveIntegerField(default=0)
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    fecha_registro = models.DateTimeField(default=timezone.now, editable=False)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="lotes_registrados",
    )

    class Meta:
        verbose_name = "Lote"
        verbose_name_plural = "Lotes"
        ordering = ["-fecha_registro"]

    def __str__(self):
        return f"{self.numero_lote} - {self.presentacion}"

    @property
    def dias_para_vencer(self):
        if not self.fecha_vencimiento:
            return None
        return (self.fecha_vencimiento - timezone.now().date()).days

    @property
    def esta_vencido(self):
        d = self.dias_para_vencer
        return d is not None and d < 0

    @property
    def proximo_a_vencer(self):
        d = self.dias_para_vencer
        return d is not None and 0 <= d <= 30


class Inventario(models.Model):
    producto = models.ForeignKey(
        Producto, on_delete=models.PROTECT, related_name="inventarios"
    )
    presentacion = models.ForeignKey(
        PresentacionProducto, on_delete=models.PROTECT, related_name="inventarios"
    )
    stock_actual = models.PositiveIntegerField(default=0)
    stock_min = models.PositiveIntegerField(default=0)
    stock_max = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Inventario"
        verbose_name_plural = "Inventarios"
        unique_together = ("producto", "presentacion")

    def __str__(self):
        return f"{self.producto} - {self.presentacion} (stock: {self.stock_actual})"

    @property
    def necesita_reabastecimiento(self):
        return self.stock_actual <= self.stock_min


class MovimientoInventario(models.Model):
    TIPO_CHOICES = [
        ("entrada", "Entrada"),
        ("salida", "Salida"),
        ("ajuste", "Ajuste"),
    ]
    inventario = models.ForeignKey(
        Inventario, on_delete=models.PROTECT, related_name="movimientos"
    )
    lote = models.ForeignKey(Lote, on_delete=models.PROTECT, related_name="movimientos")
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="movimientos_inventario",
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    fecha = models.DateTimeField(auto_now_add=True)
    cantidad = models.IntegerField()
    motivo = models.CharField(max_length=255, blank=True)
    stock_resultante = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = "Movimiento de Inventario"
        verbose_name_plural = "Movimientos de Inventario"
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.tipo} - {self.inventario} ({self.cantidad})"