from django.db import models
from django.conf import settings
from decimal import Decimal

class Proveedor(models.Model):
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
        ('sancionado', 'Sancionado'),
    ]

    TIPO_CHOICES = [
        ('distribuidor', 'Distribuidor'),
        ('fabricante', 'Fabricante'),
        ('importador', 'Importador'),
    ]

    nombre_empresa = models.CharField(max_length=200, unique=True)
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=20, blank=True)
    tipo_proveedor = models.CharField(max_length=20, choices=TIPO_CHOICES, default='distribuidor')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='activo')
    motivo_sancion = models.TextField(blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    ultima_modificacion = models.DateTimeField(auto_now=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='proveedores_registrados'
    )
    modificado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='proveedores_modificados'
    )

    class Meta:
        ordering = ['-fecha_registro']
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'

    def __str__(self):
        return self.nombre_empresa


class ProveedorCategoria(models.Model):
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.CASCADE,
        related_name='categorias'
    )
    categoria = models.ForeignKey(
        'productos.Categoria',
        on_delete=models.CASCADE,
        related_name='proveedores'
    )

    class Meta:
        unique_together = ('proveedor', 'categoria')
        verbose_name = 'Proveedor Categoría'
        verbose_name_plural = 'Proveedor Categorías'

    def __str__(self):
        return f"{self.proveedor.nombre_empresa} - {self.categoria.nombre}"


class OrdenCompra(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('confirmada', 'Confirmada'),
        ('recibida', 'Recibida'),
        ('cancelada', 'Cancelada'),
    ]

    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.CASCADE,
        related_name='ordenes_compra'
    )
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ordenes_compra_registradas'
    )
    fecha = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Orden de Compra'
        verbose_name_plural = 'Órdenes de Compra'

    def __str__(self):
        return f"Orden #{self.id} - {self.proveedor.nombre_empresa}"

    def calcular_total(self):
        self.total = sum(
            detalle.cantidad * detalle.precio_unitario
            for detalle in self.detalles.all()
        )
        self.save()


class DetalleCompra(models.Model):
    orden_compra = models.ForeignKey(
        OrdenCompra,
        on_delete=models.CASCADE,
        related_name='detalles'
    )
    presentacion = models.ForeignKey(
        'productos.PresentacionProducto',
        on_delete=models.CASCADE,
        related_name='detalles_compra'
    )
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'Detalle de Compra'
        verbose_name_plural = 'Detalles de Compra'

    def __str__(self):
        return f"{self.presentacion.nombre} - {self.cantidad} uds"

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario


class Compra(models.Model):
    """Modelo para registrar compras a proveedores (heredado)"""
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.CASCADE,
        related_name='compras_legacy'
    )
    producto = models.ForeignKey(
        'productos.Producto',
        on_delete=models.CASCADE,
        related_name='compras'
    )
    lote = models.ForeignKey(
        'inventario.Lote',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='compras'
    )
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)
    recibida = models.BooleanField(default=False)

    class Meta:
        ordering = ['-fecha_registro']
        verbose_name = 'Compra'
        verbose_name_plural = 'Compras'

    @property
    def total(self):
        if self.precio_unitario:
            return self.cantidad * self.precio_unitario
        return None

    def __str__(self):
        return f"{self.proveedor.nombre_empresa} → {self.producto.nombre} ({self.cantidad} uds)"