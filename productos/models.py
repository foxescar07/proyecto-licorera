from django.db import models


class Categoria(models.Model):
    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    padre = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='subcategorias'
    )

    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    # ✅ CORRECCIÓN #11: Se eliminó precio_unitario
    # El precio vive únicamente en PresentacionProducto
    unidad = models.CharField(max_length=50)
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name='productos'
    )

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class PresentacionProducto(models.Model):
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name='presentaciones'
    )
    nombre = models.CharField(max_length=200)
    unidades = models.PositiveIntegerField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'Presentación de Producto'
        verbose_name_plural = 'Presentaciones de Producto'

    def __str__(self):
        return f"{self.producto.nombre} - {self.nombre}"
