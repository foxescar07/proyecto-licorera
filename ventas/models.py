from django.db import models # type: ignore
from django.conf import settings # type: ignore
from django.utils import timezone # type: ignore
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from productos.models import Producto, PresentacionProducto
from decimal import Decimal


class Cliente(models.Model):
    TIPO_ID_CHOICES = [
        ('CC',  'Cédula de Ciudadanía'),
        ('CE',  'Cédula de Extranjería'),
        ('TI',  'Tarjeta de Identidad'),
        ('PA',  'Pasaporte'),
        ('PT',  'Permiso de Permanencia Temporal'),
        ('NIT', 'NIT'),
    ]

    tipo_id        = models.CharField(max_length=5, choices=TIPO_ID_CHOICES, default='CC')
    identificacion = models.CharField(max_length=20, unique=True, blank=True, null=True)
    nombre         = models.CharField(max_length=100)
    telefono       = models.CharField(max_length=15, blank=True, null=True)
    email          = models.EmailField(blank=True, null=True)
    direccion      = models.CharField(max_length=200, blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering            = ['nombre']

    def __str__(self):
        return self.nombre


class Venta(models.Model):
    cliente              = models.ForeignKey(Cliente, on_delete=models.PROTECT,
                                             related_name='ventas',
                                             verbose_name='Cliente')
    vendedor             = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                             related_name='ventas',
                                             verbose_name='Vendedor',
                                             null=True, blank=True)
    fecha                = models.DateTimeField(auto_now_add=True)
    descuento_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total_con_descuento  = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pago_efectivo        = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pago_tarjeta         = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pago_transferencia   = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pago_nequi           = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pago_daviplata       = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    comprobante_pago     = models.FileField(upload_to='comprobantes_pago/%Y/%m/',
                                            null=True, blank=True,
                                            verbose_name='Comprobante de pago')

    class Meta:
        verbose_name        = 'Venta'
        verbose_name_plural = 'Ventas'
        ordering            = ['-fecha']

    def __str__(self):
        return f'{self.cliente.nombre} — {self.fecha:%d/%m/%Y %H:%M}'

    def subtotal(self):
        return sum(d.subtotal() for d in self.detalles.all())

    @property
    def total_venta(self):
        return self.total_con_descuento if self.total_con_descuento else self.subtotal()


class DetalleVenta(models.Model):
    venta           = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto        = models.ForeignKey(Producto, on_delete=models.CASCADE,
                                        related_name='detalles_venta', null=True, blank=True)
    presentacion    = models.ForeignKey(PresentacionProducto, on_delete=models.CASCADE,
                                        related_name='detalles_venta', null=True, blank=True)
    lote            = models.ForeignKey('inventario.Lote', on_delete=models.SET_NULL,
                                        null=True, blank=True, related_name='detalles_venta')
    cantidad        = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        verbose_name        = 'Detalle de Venta'
        verbose_name_plural = 'Detalles de Venta'

    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def __str__(self):
        nombre_prod = self.presentacion.producto.nombre if self.presentacion else (self.producto.nombre if self.producto else "Producto")
        nombre_pres = f" ({self.presentacion.nombre})" if self.presentacion else ""
        return f'{nombre_prod}{nombre_pres} x{self.cantidad}'


class AperturaCaja(models.Model):
    fecha          = models.DateField()
    monto_base     = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    usuario        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                       null=True, blank=True, related_name='aperturas_caja')
    observacion    = models.TextField(blank=True)
    denominaciones = models.JSONField(default=dict, blank=True)
    creado_en      = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        verbose_name        = 'Apertura de Caja'
        verbose_name_plural = 'Aperturas de Caja'
        ordering            = ['-fecha']
        unique_together     = ['fecha', 'usuario']

    def __str__(self):
        return f'Apertura {self.fecha} ({self.usuario}) — ${self.monto_base:,.0f}'


class CierreCaja(models.Model):
    fecha                = models.DateField()
    apertura             = models.OneToOneField(AperturaCaja, on_delete=models.PROTECT, related_name='cierre')
    usuario              = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                             null=True, blank=True, related_name='cierres_caja')
    total_contado        = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    monto_base_siguiente = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_retirado       = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    denominaciones       = models.JSONField(default=dict, blank=True)
    creado_en            = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        verbose_name        = 'Cierre de Caja'
        verbose_name_plural = 'Cierres de Caja'
        ordering            = ['-fecha']

    def __str__(self):
        return f'Cierre {self.fecha} — contado: ${self.total_contado:,.0f}'


class Devolucion(models.Model):
    """Registra una devolución de productos por parte del cliente."""

    MOTIVO_CHOICES = [
        ('defectuoso',   'Producto defectuoso'),
        ('equivocado',   'Error en el pedido'),
        ('insatisfecho', 'Cliente insatisfecho'),
        ('calidad',      'Problema de calidad'),
        ('empaque',      'Empaque dañado'),
        ('otro',         'Otro motivo'),
    ]

    REEMBOLSO_CHOICES = [
        ('cambio',       'Cambio de producto'),
        ('nota_credito', 'Nota crédito'),
        ('reembolso',    'Reembolso'),
    ]

    METODO_PAGO_CHOICES = [
        ('efectivo',     'Efectivo'),
        ('tarjeta',      'Tarjeta'),
        ('transferencia', 'Transferencia'),
        ('nequi',        'Nequi'),
        ('daviplata',    'DaviPlata'),
    ]

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aprobada',  'Aprobada'),
        ('aplicada',  'Aplicada'),
    ]

    venta = models.ForeignKey(
        Venta,
        on_delete=models.PROTECT,
        related_name='devoluciones',
        verbose_name='Venta original',
        help_text="Venta a la cual corresponde la devolución"
    )
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='devoluciones_procesadas',
        verbose_name='Registrado por',
        null=True,
        blank=True,
        help_text="Empleado que registra la devolución"
    )
    fecha = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha de registro de la devolución"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='pendiente',
        help_text="Estado del proceso de la devolución"
    )
    motivo = models.CharField(
        max_length=20,
        choices=MOTIVO_CHOICES,
        default='otro',
        help_text="Motivo por el que se devuelve"
    )
    tipo_reembolso = models.CharField(
        max_length=20,
        choices=REEMBOLSO_CHOICES,
        default='cambio',
        help_text="Tipo de reembolso al cliente"
    )
    metodo_pago_devolucion = models.CharField(
        max_length=50,
        choices=METODO_PAGO_CHOICES,
        blank=True,
        help_text="Método de pago para la devolución"
    )
    producto_cambio = models.ForeignKey(
        Producto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='devoluciones_cambio',
        verbose_name='Producto de cambio',
        help_text="Producto de reemplazo cuando el tipo de reembolso es 'cambio'"
    )
    cantidad_cambio = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Cantidad de cambio'
    )
    saldo_credito = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Saldo a crédito',
        help_text="Monto disponible cuando el tipo de reembolso es 'nota_credito'"
    )
    observaciones = models.TextField(
        blank=True,
        help_text="Observaciones adicionales"
    )
    restaurar_stock = models.BooleanField(
        default=True,
        help_text="¿Restaurar el stock al inventario?"
    )
    tiene_comprobante = models.BooleanField(
        default=True,
        help_text="¿Tiene comprobante de compra?"
    )
    total_devuelto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total a devolver al cliente"
    )

    class Meta:
        verbose_name = 'Devolución'
        verbose_name_plural = 'Devoluciones'
        ordering = ['-fecha']

    def __str__(self):
        if self.pk:
            return f'DEV-{self.pk:04d} | {self.venta.cliente.nombre} — {self.fecha:%d/%m/%Y %H:%M}'
        return f'Nueva Devolución — {self.venta.cliente.nombre}'

    @property
    def numero(self):
        """Retorna el número de devolución formateado."""
        return f'DEV-{self.pk:04d}' if self.pk else 'NUEVA'

    def calcular_total(self):
        """Recalcula total_devuelto sumando los subtotales de los detalles y guarda."""
        total = sum(d.subtotal for d in self.detalles.all())
        self.total_devuelto = total
        self.save()
        return total

    def clean(self):
        """Validaciones adicionales."""
        from django.core.exceptions import ValidationError

        if self.total_devuelto < 0:
            raise ValidationError({'total_devuelto': 'No puede ser negativo'})

        if self.total_devuelto > self.venta.total_venta:
            raise ValidationError({
                'total_devuelto': f'No puede exceder el total de la venta (${self.venta.total_venta})'
            })


class DetalleDevolucion(models.Model):
    """Línea individual de una devolución."""

    devolucion = models.ForeignKey(
        Devolucion,
        on_delete=models.CASCADE,
        related_name='detalles',
        help_text="Devolución a la que pertenece"
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='detalles_devolucion',
        help_text="Producto devuelto (referencia directa, opcional)"
    )
    presentacion = models.ForeignKey(
        PresentacionProducto,
        on_delete=models.CASCADE,
        related_name='detalles_devolucion',
        help_text="Presentación del producto devuelto"
    )
    lote = models.ForeignKey(
        'inventario.Lote',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='detalles_devolucion',
        help_text="Lote del producto (si aplica)"
    )
    cantidad = models.PositiveIntegerField(
        validators=[MinValueValidator(1, 'Cantidad debe ser al menos 1')],
        help_text="Cantidad devuelta"
    )
    precio_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Precio unitario del producto"
    )

    class Meta:
        verbose_name = 'Detalle de Devolución'
        verbose_name_plural = 'Detalles de Devolución'

    @property
    def subtotal(self):
        """Calcula el subtotal de este detalle."""
        return self.cantidad * self.precio_unitario

    def __str__(self):
        nombre_prod = self.presentacion.producto.nombre if self.presentacion else "Producto"
        nombre_pres = f" ({self.presentacion.nombre})" if self.presentacion else ""
        return f'{nombre_prod}{nombre_pres} x{self.cantidad}'

    def clean(self):
        """Validaciones adicionales."""
        from django.core.exceptions import ValidationError

        if self.cantidad <= 0:
            raise ValidationError({'cantidad': 'Debe ser mayor a 0'})

        if self.precio_unitario <= 0:
            raise ValidationError({'precio_unitario': 'Debe ser mayor a 0'})