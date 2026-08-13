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
    nit = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        help_text="Número de Identificación Tributaria"
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
        blank=True,
        help_text="Tipo de negocio del proveedor"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='activo',
        help_text="Estado actual del proveedor"
    )
    observacion = models.TextField(
        blank=True,
        null=True,
        help_text="Observaciones adicionales sobre el proveedor"
    )
    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha de creación del registro"
    )
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='proveedores_registrados',
        help_text="Usuario que creó el registro"
    )

    class Meta:
        ordering = ['-fecha_registro']
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'

    def __str__(self):
        return f"{self.nombre_empresa} ({self.get_estado_display()})"

    def clean(self):
        """Validaciones adicionales del modelo."""
        if self.estado == 'sancionado' and not self.observacion:
            raise ValidationError({
                'observacion': 'Debe indicar el motivo de la sanción'
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


class DetalleCompra(models.Model):
    """Línea individual de una compra."""

    compra = models.ForeignKey(
        'Compra',
        on_delete=models.CASCADE,
        related_name='detalles',
        null=True,
        blank=True,
        help_text="Compra a la que pertenece"
    )
    producto = models.ForeignKey(
        'productos.Producto',
        on_delete=models.CASCADE,
        related_name='detalles_compra_producto',
        null=True,
        blank=True,
        help_text="Producto"
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
    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha de registro"
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

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('confirmada', 'Confirmada'),
        ('recibida', 'Recibida'),
        ('pagada', 'Pagada'),
        ('cancelada', 'Cancelada'),
    ]

    METODO_PAGO_CHOICES = [
        ('transferencia', 'Transferencia Bancaria'),
        ('efectivo', 'Efectivo'),
        ('cheque', 'Cheque'),
        ('tarjeta', 'Tarjeta de Crédito'),
        ('credito', 'Crédito a 30 días'),
        ('otro', 'Otro'),
    ]

    ESTADO_PAGO_CHOICES = [
        ('pendiente', 'Pendiente de Pago'),
        ('pagada', 'Pagada'),
        ('parcial', 'Pago Parcial'),
    ]

    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.CASCADE,
        related_name='compras',
        help_text="Proveedor"
    )
    documento_usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='compras_registradas',
        help_text="Usuario que registra la compra"
    )
    fecha = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha de la compra"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='pendiente',
        help_text="Estado de la compra"
    )
    valor = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Valor total de la compra"
    )
    saldo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Saldo pendiente de pago"
    )
    motivo_pago = models.TextField(
        blank=True,
        null=True,
        help_text="Motivo o nota del pago"
    )
    observacion = models.TextField(
        blank=True,
        null=True,
        help_text="Observaciones adicionales sobre la compra"
    )

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Compra'
        verbose_name_plural = 'Compras'

    def __str__(self):
        return f"Compra #{self.id} - {self.proveedor.nombre_empresa}"

    @property
    def monto_pagado(self):
        """Monto abonado, derivado del valor y el saldo persistidos."""
        return max(Decimal('0.00'), self.valor - self.saldo)

    @property
    def estado_pago(self):
        if self.saldo <= 0:
            return 'pagada'
        if self.monto_pagado > 0:
            return 'parcial'
        return 'pendiente'

    @property
    def total(self):
        """Alias de compatibilidad para las vistas que muestran el total."""
        return self.valor

    @property
    def fecha_registro(self):
        """Alias de compatibilidad para el nombre histórico del campo fecha."""
        return self.fecha


class HistorialCompra(models.Model):
    """Registro de cambios en las compras."""

    EVENTO_CHOICES = [
        ('creada', 'Compra Creada'),
        ('recibida', 'Recibida'),
        ('pagada', 'Pagada'),
        ('cancelada', 'Cancelada'),
        ('editada', 'Editada'),
    ]

    compra = models.ForeignKey(
        'Compra',
        on_delete=models.CASCADE,
        related_name='historial',
        help_text="Compra"
    )
    evento = models.CharField(
        max_length=20,
        choices=EVENTO_CHOICES,
        help_text="Tipo de evento"
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Usuario que realizó la acción"
    )
    fecha = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha del evento"
    )
    descripcion = models.TextField(
        blank=True,
        help_text="Descripción adicional del evento"
    )

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Historial de Compra'
        verbose_name_plural = 'Historial de Compras'

    def __str__(self):
        return f"Compra {self.compra.id} - {self.get_evento_display()}"
