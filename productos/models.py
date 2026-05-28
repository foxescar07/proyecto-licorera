from django.db import models
from django.db.models import Sum


class Categoria(models.Model):
    codigo      = models.CharField(max_length=50, unique=True)
    nombre      = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    padre       = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='subcategorias'
    )

    class Meta:
        verbose_name        = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering            = ['nombre']

    def __str__(self):
        if self.padre:
            return f"{self.padre.nombre} → {self.nombre}"
        return self.nombre


class Producto(models.Model):
    codigo      = models.CharField(max_length=50, unique=True)
    nombre      = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    unidad      = models.CharField(max_length=50, default='UND', blank=True)
    categoria   = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name='productos'
    )

    class Meta:
        verbose_name        = 'Producto'
        verbose_name_plural = 'Productos'
        ordering            = ['nombre']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    @property
    def stock_total(self):
        return self.presentaciones.aggregate(
            total=Sum('lotes__stock_actual')
        )['total'] or 0

    @property
    def stock_critico(self):
        return self.stock_total < 10


class PresentacionProducto(models.Model):
    producto  = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name='presentaciones'
    )
    nombre    = models.CharField(max_length=200)
    unidades  = models.PositiveIntegerField()
    precio    = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name        = 'Presentación de Producto'
        verbose_name_plural = 'Presentaciones de Producto'

    def __str__(self):
        return f"{self.producto.nombre} — {self.nombre} ({self.unidades} uds)"