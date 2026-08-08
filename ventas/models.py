from django.db import models  # type: ignore
from django.conf import settings  # type: ignore
from django.utils import timezone  # type: ignore
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from productos.models import Producto, PresentacionProducto
from decimal import Decimal


# ════════════════════════════════════════
# CLIENTE
# ════════════════════════════════════════

class Cliente(models.Model):
    """
    MER: cliente
    #codigo | *documento_usuario(FK) | *identificacion | *nombre | *apellido
    *telefono | correo_personal
    """
    TIPO_ID_CHOICES = [
        ('CC',  'Cédula de Ciudadanía'),
        ('CE',  'Cédula de Extranjería'),
        ('TI',  'Tarjeta de Identidad'),
        ('PA',  'Pasaporte'),
        ('PT',  'Permiso de Permanencia Temporal'),
        ('NIT', 'NIT'),
    ]

    # FK al usuario que registró al cliente (documento_usuario en MER)
    documento_usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clientes_registrados',
        verbose_name='Usuario que registró',
    )
    tipo_id        = models.CharField(
        max_length=5, choices=TIPO_ID_CHOICES, default='CC',
        verbose_name='Tipo de identificación',
    )
    identificacion = models.CharField(
        max_length=20, unique=True, blank=True, null=True,
        verbose_name='Identificación',
    )
    nombre         = models.CharField(max_length=100, verbose_name='Nombre')
    apellido       = models.CharField(
        max_length=100, blank=True, default='',
        verbose_name='Apellido',
    )
    telefono       = models.CharField(
        max_length=15, blank=True, null=True,
        verbose_name='Teléfono',
    )
    correo_personal = models.EmailField(
        blank=True, null=True,
        verbose_name='Correo personal',
    )
    # Campos auxiliares mantenidos por utilidad del negocio
    direccion      = models.CharField(max_length=200, blank=True, null=True, verbose_name='Dirección')
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de registro')

    class Meta:
        verbose_name        = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering            = ['nombre']

    def __str__(self):
        apellido = f' {self.apellido}' if self.apellido else ''
        return f'{self.nombre}{apellido}'

    @property
    def nombre_completo(self):
        return f'{self.nombre} {self.apellido}'.strip()


# ════════════════════════════════════════
# VENTA
# ════════════════════════════════════════

class Venta(models.Model):
    """
    MER: venta
    #codigo_venta | *documento_usuario(FK) | *codigo_cliente(FK)
    *fecha | *total_venta | *metodo_pago
    """
    METODO_PAGO_CHOICES = [
        ('efectivo',      'Efectivo'),
        ('tarjeta',       'Tarjeta'),
        ('transferencia', 'Transferencia bancaria'),
        ('nequi',         'Nequi'),
        ('daviplata',     'DaviPlata'),
        ('mixto',         'Pago mixto'),
    ]

    # FK → Usuario (documento_usuario en MER)
    documento_usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='ventas',
        verbose_name='Vendedor',
        null=True,
        blank=True,
    )
    # FK → Cliente (codigo_cliente en MER)
    codigo_cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name='ventas',
        verbose_name='Cliente',
    )
    fecha        = models.DateTimeField(auto_now_add=True, verbose_name='Fecha')
    total_venta  = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Total de la venta',
    )
    metodo_pago  = models.CharField(
        max_length=20,
        choices=METODO_PAGO_CHOICES,
        default='efectivo',
        verbose_name='Método de pago',
    )
    # Campos auxiliares mantenidos por utilidad del negocio
    descuento_porcentaje = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name='Descuento (%)',
    )
    comprobante_pago = models.FileField(
        upload_to='comprobantes_pago/%Y/%m/',
        null=True, blank=True,
        verbose_name='Comprobante de pago',
    )

    class Meta:
        verbose_name        = 'Venta'
        verbose_name_plural = 'Ventas'
        ordering            = ['-fecha']

    def __str__(self):
        return f'{self.codigo_cliente.nombre} — {self.fecha:%d/%m/%Y %H:%M}'

    @property
    def subtotal(self):
        """Suma de subtotales de todos los detalles."""
        return sum(d.subtotal for d in self.detalles.all())

    @property
    def total_venta_calculado(self):
        """Total con descuento aplicado."""
        return self.total_venta if self.total_venta else self.subtotal


# ════════════════════════════════════════
# DETALLE VENTA
# ════════════════════════════════════════

class DetalleVenta(models.Model):
    """
    MER: detalle_venta
    #codigo | *codigo_venta(FK) | *codigo_producto(FK) | *codigo_lote(FK)
    *codigo_presentacion(FK) | *cantidad | *subtotal | valor_descuento
    *total | codigo_reporte(FK)
    """
    # FK → Venta
    codigo_venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        related_name='detalles',
        verbose_name='Venta',
    )
    # FK → Producto
    codigo_producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name='detalles_venta',
        null=True, blank=True,
        verbose_name='Producto',
    )
    # FK → Lote
    codigo_lote = models.ForeignKey(
        'inventario.Lote',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='detalles_venta',
        verbose_name='Lote',
    )
    # FK → PresentacionProducto
    codigo_presentacion = models.ForeignKey(
        PresentacionProducto,
        on_delete=models.CASCADE,
        related_name='detalles_venta',
        null=True, blank=True,
        verbose_name='Presentación',
    )
    # FK → Reporte (opcional, para trazabilidad)
    codigo_reporte = models.ForeignKey(
        'reportes.Reporte',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='detalles_venta',
        verbose_name='Reporte asociado',
    )

    cantidad        = models.PositiveIntegerField(verbose_name='Cantidad')
    precio_unitario = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name='Precio unitario',
    )
    valor_descuento = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Descuento aplicado',
    )
    # subtotal = precio_unitario * cantidad (antes de descuento)
    subtotal = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Subtotal',
    )
    # total = subtotal - valor_descuento
    total = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Total',
    )

    class Meta:
        verbose_name        = 'Detalle de Venta'
        verbose_name_plural = 'Detalles de Venta'

    def save(self, *args, **kwargs):
        """Calcula subtotal y total automáticamente antes de guardar."""
        precio = self.precio_unitario or Decimal('0')
        cant   = self.cantidad or 0
        descto = self.valor_descuento or Decimal('0')
        self.subtotal = precio * cant
        self.total    = self.subtotal - descto
        super().save(*args, **kwargs)

    def __str__(self):
        if self.codigo_presentacion:
            nombre_prod = self.codigo_presentacion.producto.nombre
            nombre_pres = f' ({self.codigo_presentacion.nombre})'
        elif self.codigo_producto:
            nombre_prod = self.codigo_producto.nombre
            nombre_pres = ''
        else:
            nombre_prod = 'Producto'
            nombre_pres = ''
        return f'{nombre_prod}{nombre_pres} x{self.cantidad}'


# ════════════════════════════════════════
# APERTURA DE CAJA
# ════════════════════════════════════════

class AperturaCaja(models.Model):
    """
    MER: apertura_caja
    #codigo | *documento_usuario(FK) | *fecha | *hora | *monto_base
    *denominaciones | observacion
    """
    fecha          = models.DateField(verbose_name='Fecha')
    hora           = models.TimeField(auto_now_add=True, verbose_name='Hora')
    monto_base     = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Monto base',
    )
    documento_usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='aperturas_caja',
        verbose_name='Usuario',
    )
    observacion    = models.TextField(blank=True, verbose_name='Observación')
    denominaciones = models.JSONField(default=dict, blank=True, verbose_name='Denominaciones')
    creado_en      = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        verbose_name        = 'Apertura de Caja'
        verbose_name_plural = 'Aperturas de Caja'
        ordering            = ['-fecha']
        unique_together     = ['fecha', 'documento_usuario']

    def __str__(self):
        return f'Apertura {self.fecha} ({self.documento_usuario}) — ${self.monto_base:,.0f}'


# ════════════════════════════════════════
# CIERRE DE CAJA
# ════════════════════════════════════════

class CierreCaja(models.Model):
    """
    MER: cierre_caja
    #codigo | *documento_usuario(FK) | *codigo_apertura(FK) | *fecha
    *hora | *total_en_efectivo | *total_transferencias | *total_retirado_efectivo
    *monto_base
    """
    fecha                = models.DateField(verbose_name='Fecha')
    hora                 = models.TimeField(auto_now_add=True, verbose_name='Hora')
    apertura             = models.OneToOneField(
        AperturaCaja,
        on_delete=models.PROTECT,
        related_name='cierre',
        verbose_name='Apertura de caja',
    )
    documento_usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='cierres_caja',
        verbose_name='Usuario',
    )
    # Campos del MER
    total_en_efectivo      = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Total en efectivo',
    )
    total_transferencias   = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Total transferencias',
    )
    total_retirado_efectivo = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Total retirado efectivo',
    )
    monto_base             = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Monto base siguiente',
    )
    # Campos auxiliares mantenidos
    total_contado          = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Total contado',
    )
    monto_base_siguiente   = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Monto base para próxima apertura',
    )
    total_retirado         = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Total retirado',
    )
    denominaciones         = models.JSONField(default=dict, blank=True, verbose_name='Denominaciones')
    creado_en              = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        verbose_name        = 'Cierre de Caja'
        verbose_name_plural = 'Cierres de Caja'
        ordering            = ['-fecha']

    def __str__(self):
        return f'Cierre {self.fecha} — contado: ${self.total_contado:,.0f}'


# ════════════════════════════════════════
# DEVOLUCIÓN
# ════════════════════════════════════════

class Devolucion(models.Model):
    """
    MER: devolucion
    #codigo_devolucion | *codigo_venta(FK) | *codigo_detalle_venta(FK)
    *documento_usuario(FK) | *fecha | *motivo | *tipo_devolucion
    observaciones | *presenta_comprobante | *total_devuelto | *estado
    *cantidad_cambio | *metodo_pago_devolucion
    """

    MOTIVO_CHOICES = [
        ('defectuoso',   'Producto defectuoso'),
        ('equivocado',   'Error en el pedido'),
        ('insatisfecho', 'Cliente insatisfecho'),
        ('calidad',      'Problema de calidad'),
        ('empaque',      'Empaque dañado'),
        ('otro',         'Otro motivo'),
    ]

    TIPO_DEVOLUCION_CHOICES = [
        ('cambio',       'Cambio de producto'),
        ('nota_credito', 'Nota crédito'),
        ('reembolso',    'Reembolso'),
    ]

    METODO_PAGO_CHOICES = [
        ('efectivo',      'Efectivo'),
        ('tarjeta',       'Tarjeta'),
        ('transferencia', 'Transferencia'),
        ('nequi',         'Nequi'),
        ('daviplata',     'DaviPlata'),
    ]

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aprobada',  'Aprobada'),
        ('aplicada',  'Aplicada'),
    ]

    # FK → Venta
    codigo_venta = models.ForeignKey(
        Venta,
        on_delete=models.PROTECT,
        related_name='devoluciones',
        verbose_name='Venta original',
        help_text='Venta a la cual corresponde la devolución',
    )
    # FK → DetalleVenta (referencia principal del MER)
    codigo_detalle_venta = models.ForeignKey(
        DetalleVenta,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='devoluciones',
        verbose_name='Detalle de venta',
        help_text='Línea de detalle principal de la devolución',
    )
    # FK → Usuario (documento_usuario en MER)
    documento_usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='devoluciones_procesadas',
        verbose_name='Registrado por',
        null=True,
        blank=True,
        help_text='Empleado que registra la devolución',
    )
    fecha = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha',
        help_text='Fecha de registro de la devolución',
    )
    motivo = models.CharField(
        max_length=20,
        choices=MOTIVO_CHOICES,
        default='otro',
        verbose_name='Motivo',
        help_text='Motivo por el que se devuelve',
    )
    tipo_devolucion = models.CharField(
        max_length=20,
        choices=TIPO_DEVOLUCION_CHOICES,
        default='cambio',
        verbose_name='Tipo de devolución',
        help_text='Tipo de resolución para el cliente',
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name='Observaciones',
        help_text='Observaciones adicionales',
    )
    presenta_comprobante = models.BooleanField(
        default=True,
        verbose_name='Presenta comprobante',
        help_text='¿El cliente presenta comprobante de compra?',
    )
    total_devuelto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Total devuelto',
        help_text='Total a devolver al cliente',
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='pendiente',
        verbose_name='Estado',
        help_text='Estado del proceso de la devolución',
    )
    cantidad_cambio = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Cantidad de cambio',
        help_text='Cantidad de producto de reemplazo cuando tipo es cambio',
    )
    metodo_pago_devolucion = models.CharField(
        max_length=50,
        choices=METODO_PAGO_CHOICES,
        blank=True,
        verbose_name='Método de pago de devolución',
        help_text='Método de pago para la devolución',
    )
    # Campos auxiliares mantenidos por utilidad del negocio
    restaurar_stock = models.BooleanField(
        default=True,
        verbose_name='Restaurar stock',
        help_text='¿Restaurar el stock al inventario?',
    )
    producto_cambio = models.ForeignKey(
        Producto,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='devoluciones_cambio',
        verbose_name='Producto de cambio',
        help_text="Producto de reemplazo cuando tipo_devolucion es 'cambio'",
    )
    saldo_credito = models.DecimalField(
        max_digits=12, decimal_places=2,
        null=True, blank=True,
        verbose_name='Saldo a crédito',
        help_text="Monto disponible cuando tipo_devolucion es 'nota_credito'",
    )

    class Meta:
        verbose_name        = 'Devolución'
        verbose_name_plural = 'Devoluciones'
        ordering            = ['-fecha']

    def __str__(self):
        if self.pk:
            return f'DEV-{self.pk:04d} | {self.codigo_venta.codigo_cliente.nombre} — {self.fecha:%d/%m/%Y %H:%M}'
        return f'Nueva Devolución — {self.codigo_venta.codigo_cliente.nombre}'

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
        if self.total_devuelto < 0:
            raise ValidationError({'total_devuelto': 'No puede ser negativo'})

        if self.total_devuelto > self.codigo_venta.total_venta:
            raise ValidationError({
                'total_devuelto': (
                    f'No puede exceder el total de la venta '
                    f'(${self.codigo_venta.total_venta})'
                )
            })


# ════════════════════════════════════════
# DETALLE DEVOLUCIÓN
# ════════════════════════════════════════

class DetalleDevolucion(models.Model):
    """
    Línea individual de una devolución.
    Se mantiene para soportar devoluciones con múltiples productos.
    """

    devolucion = models.ForeignKey(
        Devolucion,
        on_delete=models.CASCADE,
        related_name='detalles',
        verbose_name='Devolución',
        help_text='Devolución a la que pertenece',
    )
    presentacion = models.ForeignKey(
        PresentacionProducto,
        on_delete=models.CASCADE,
        related_name='detalles_devolucion',
        verbose_name='Presentación',
        help_text='Presentación del producto devuelto',
    )
    codigo_lote = models.ForeignKey(
        'inventario.Lote',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='detalles_devolucion',
        verbose_name='Lote',
        help_text='Lote del producto (si aplica)',
    )
    cantidad = models.PositiveIntegerField(
        validators=[MinValueValidator(1, 'Cantidad debe ser al menos 1')],
        verbose_name='Cantidad',
        help_text='Cantidad devuelta',
    )
    precio_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Precio unitario',
        help_text='Precio unitario del producto',
    )

    class Meta:
        verbose_name        = 'Detalle de Devolución'
        verbose_name_plural = 'Detalles de Devolución'

    @property
    def subtotal(self):
        """Calcula el subtotal de este detalle."""
        return self.cantidad * self.precio_unitario

    def __str__(self):
        nombre_prod = self.presentacion.producto.nombre
        nombre_pres = f' ({self.presentacion.nombre})'
        return f'{nombre_prod}{nombre_pres} x{self.cantidad}'

    def clean(self):
        """Validaciones adicionales."""
        if self.cantidad <= 0:
            raise ValidationError({'cantidad': 'Debe ser mayor a 0'})
        if self.precio_unitario <= 0:
            raise ValidationError({'precio_unitario': 'Debe ser mayor a 0'})