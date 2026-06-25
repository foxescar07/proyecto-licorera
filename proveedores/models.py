from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.core.exceptions import ValidationError
from decimal import Decimal

class Proveedor(models.Model):
    """Representa un proveedor de bebidas alcohólicas para la licorería."""

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

    nombre_empresa = models.CharField(
        max_length=200,
        unique=True,
        help_text="Nombre comercial único del proveedor"
    )
    email = models.EmailField(
        unique=True,
        help_text="Correo electrónico para comunicación"
    )
    telefono = models.CharField(
        max_length=20,
        blank=True,
        validators=[RegexValidator(
            regex=r'^\d{7,15}$|^$',
            message='Teléfono debe tener 7-15 dígitos',
            code='invalid_phone'
        )],
        help_text="Formato: 7-15 dígitos (opcional)"
    )
    tipo_proveedor = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default='distribuidor',
        help_text="Tipo de negocio del proveedor"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='activo',
        help_text="Estado actual del proveedor"
    )
    motivo_sancion = models.TextField(
        blank=True,
        null=True,
        help_text="Motivo de sanción (requerido si está sancionado)"
    )
    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha de creación del registro"
    )
    ultima_modificacion = models.DateTimeField(
        auto_now=True,
        help_text="Última fecha de modificación"
    )
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='proveedores_registrados',
        help_text="Usuario que creó el registro"
    )
    modificado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='proveedores_modificados',
        help_text="Usuario que realizó la última modificación"
    )

    class Meta:
        ordering = ['-fecha_registro']
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'

    def __str__(self):
        return f"{self.nombre_empresa} ({self.get_estado_display()})"

    def clean(self):
        """Validaciones adicionales del modelo."""
        if self.estado == 'sancionado' and not self.motivo_sancion:
            raise ValidationError({
                'motivo_sancion': 'Debe indicar el motivo de la sanción'
            })


class ProveedorCategoria(models.Model):
    """Relaciona proveedores con las categorías de productos que surten."""

    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.CASCADE,
        related_name='categorias',
        help_text="Proveedor"
    )
    categoria = models.ForeignKey(
        'productos.Categoria',
        on_delete=models.CASCADE,
        related_name='proveedores',
        help_text="Categoría de productos"
    )

    class Meta:
        unique_together = ('proveedor', 'categoria')
        verbose_name = 'Proveedor Categoría'
        verbose_name_plural = 'Proveedor Categorías'

    def __str__(self):
        return f"{self.proveedor.nombre_empresa} - {self.categoria.nombre}"


class OrdenCompra(models.Model):
    """Orden de compra realizada a un proveedor."""

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('confirmada', 'Confirmada'),
        ('recibida', 'Recibida'),
        ('cancelada', 'Cancelada'),
    ]

    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.CASCADE,
        related_name='ordenes_compra',
        help_text="Proveedor de la orden"
    )
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ordenes_compra_registradas',
        help_text="Empleado que creó la orden"
    )
    fecha = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha de creación de la orden"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='pendiente',
        help_text="Estado actual de la orden"
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total de la orden (calculado automáticamente)"
    )

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Orden de Compra'
        verbose_name_plural = 'Órdenes de Compra'

    def __str__(self):
        return f"Orden #{self.id} - {self.proveedor.nombre_empresa}"

    def calcular_total(self):
        """Calcula el total de la orden sumando detalles."""
        self.total = sum(
            detalle.cantidad * detalle.precio_unitario
            for detalle in self.detalles.all()
        )
        self.save()

    def clean(self):
        """Validaciones adicionales."""
        if self.estado == 'cancelada' and self.detalles.exists():
            if any(d.cantidad > 0 for d in self.detalles.all()):
                raise ValidationError(
                    'No se puede cancelar una orden con detalles pendientes'
                )


class DetalleCompra(models.Model):
    """Línea individual de una orden de compra."""

    orden_compra = models.ForeignKey(
        OrdenCompra,
        on_delete=models.CASCADE,
        related_name='detalles',
        help_text="Orden de compra a la que pertenece"
    )
    presentacion = models.ForeignKey(
        'productos.PresentacionProducto',
        on_delete=models.CASCADE,
        related_name='detalles_compra',
        help_text="Presentación del producto"
    )
    cantidad = models.IntegerField(
        validators=[MinValueValidator(1, 'La cantidad debe ser al menos 1')],
        help_text="Cantidad a comprar"
    )
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'), 'El precio debe ser mayor a 0')],
        help_text="Precio por unidad"
    )

    class Meta:
        verbose_name = 'Detalle de Compra'
        verbose_name_plural = 'Detalles de Compra'

    def __str__(self):
        return f"{self.presentacion.nombre} - {self.cantidad} uds"

    @property
    def subtotal(self):
        """Calcula automáticamente el subtotal."""
        return self.cantidad * self.precio_unitario

    def clean(self):
        """Validaciones adicionales."""
        if self.cantidad <= 0:
            raise ValidationError({'cantidad': 'La cantidad debe ser mayor a 0'})
        if self.precio_unitario <= 0:
            raise ValidationError({'precio_unitario': 'El precio debe ser mayor a 0'})


class Compra(models.Model):
    """Modelo para registrar compras a proveedores (heredado/legacy)."""

    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.CASCADE,
        related_name='compras_legacy',
        help_text="Proveedor"
    )
    producto = models.ForeignKey(
        'productos.Producto',
        on_delete=models.CASCADE,
        related_name='compras',
        help_text="Producto comprado"
    )
    lote = models.ForeignKey(
        'inventario.Lote',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='compras',
        help_text="Lote asociado (opcional)"
    )
    cantidad = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Cantidad comprada"
    )
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Precio por unidad"
    )
    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha de registro"
    )
    recibida = models.BooleanField(
        default=False,
        help_text="¿Ha sido recibida?"
    )

    class Meta:
        ordering = ['-fecha_registro']
        verbose_name = 'Compra'
        verbose_name_plural = 'Compras'

    @property
    def total(self):
        """Calcula el total de la compra."""
        if self.precio_unitario:
            return self.cantidad * self.precio_unitario
        return None

    def __str__(self):
        return f"{self.proveedor.nombre_empresa} → {self.producto.nombre} ({self.cantidad} uds)"