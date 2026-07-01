from django.db import models
from django.db.models import Sum


class Categoria(models.Model):
    codigo      = models.CharField(max_length=20, unique=True)
    nombre      = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    padre       = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='subcategorias'
    )

    class Meta:
        verbose_name        = "Categoría"
        verbose_name_plural = "Categorías"
        ordering            = ["nombre"]

    def __str__(self):
        if self.padre:
            return f"{self.padre.nombre} → {self.nombre}"
        return self.nombre


class Producto(models.Model):
    codigo              = models.CharField(max_length=30, unique=True)
    nombre              = models.CharField(max_length=150)
    descripcion         = models.TextField(blank=True, null=True)
    cantidad_disponible = models.PositiveIntegerField(default=0)
    precio_unitario     = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True)
    unidad              = models.CharField(max_length=10, default="UND", blank=True)
    categoria           = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name="productos"
    )
    activo              = models.BooleanField(default=True) 

    class Meta:
        verbose_name        = "Producto"
        verbose_name_plural = "Productos"
        ordering            = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"

    
    @property
    def stock_total(self):
        from django.db.models import Sum
        try:
            from inventario.models import Lote
            total_lotes = Lote.objects.filter(
                presentacion__producto=self
            ).aggregate(total=Sum('stock_actual'))['total'] or 0
            return total_lotes
        except Exception:
            return 0
    
    @property
    def stock_critico(self):
        return self.stock_total <= 5

    def precio_base(self):
        pres = self.presentaciones.order_by('unidades').first()
        return pres.precio if pres else self.precio_unitario


class PresentacionProducto(models.Model):
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name='presentaciones'
    )
    nombre   = models.CharField(max_length=50)
    unidades = models.PositiveIntegerField(default=1)
    cantidad = models.PositiveIntegerField(default=0)
    precio   = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        verbose_name        = "Presentación de Producto"
        verbose_name_plural = "Presentaciones de Producto"
        ordering            = ["unidades"]

    def __str__(self):
        return f"{self.producto.nombre} — {self.nombre} ({self.unidades} uds)"
    
    @property
    def stock_real(self):
        from django.db.models import Sum
        return self.lotes.aggregate(total=Sum('stock_actual'))['total'] or 0

