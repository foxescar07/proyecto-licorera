from django.db import models
from django.conf import settings
from django.utils import timezone
from productos.models import Producto, PresentacionProducto


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
    presentacion    = models.ForeignKey('productos.PresentacionProducto', on_delete=models.CASCADE,
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
        return f'{self.presentacion.producto.nombre} ({self.presentacion.nombre}) x{self.cantidad}'


class AperturaCaja(models.Model):
    fecha_apertura = models.DateTimeField(default=timezone.now)
    fecha          = models.DateField(default=timezone.localdate)
    monto_base     = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    usuario        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                       related_name='aperturas_caja',
                                       verbose_name='Usuario',
                                       null=True, blank=True)
    observacion    = models.TextField(blank=True, default='')
    denominaciones = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering            = ['-fecha_apertura']
        verbose_name        = 'Apertura de caja'
        verbose_name_plural = 'Aperturas de caja'

    def __str__(self):
        return f'Apertura {self.fecha} — ${self.monto_base:,.0f}'


class CierreCaja(models.Model):
    apertura             = models.ForeignKey(AperturaCaja, on_delete=models.SET_NULL,
                                             null=True, blank=True, related_name='cierres')
    fecha_cierre         = models.DateTimeField(default=timezone.now)
    fecha                = models.DateField(default=timezone.localdate)
    turno                = models.PositiveIntegerField(default=1)
    total_contado        = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_retirado       = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    monto_base_siguiente = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    denominaciones       = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering            = ['-fecha_cierre']
        verbose_name        = 'Cierre de caja'
        verbose_name_plural = 'Cierres de caja'

    def __str__(self):
        return f'Cierre {self.fecha} turno {self.turno} — contado ${self.total_contado:,.0f}'


class Devolucion(models.Model):
    MOTIVO_CHOICES = [
        ('defectuoso',   'Producto defectuoso'),
        ('equivocado',   'Producto equivocado'),
        ('insatisfecho', 'Cliente insatisfecho'),
        ('otro',         'Otro'),
    ]

    venta             = models.ForeignKey(Venta, on_delete=models.PROTECT,
                                          related_name='devoluciones',
                                          verbose_name='Venta original')
    fecha             = models.DateTimeField(auto_now_add=True)
    motivo            = models.CharField(max_length=20, choices=MOTIVO_CHOICES, default='otro')
    observaciones     = models.TextField(blank=True)
    restaurar_stock   = models.BooleanField(default=True)
    tiene_comprobante = models.BooleanField(default=True)
    total_devuelto    = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        verbose_name        = 'Devolución'
        verbose_name_plural = 'Devoluciones'
        ordering            = ['-fecha']

    def __str__(self):
        return f'DEV-{self.pk:04d} | {self.venta.cliente.nombre} — {self.fecha:%d/%m/%Y %H:%M}'

    @property
    def numero(self):
        return f'DEV-{self.pk:04d}'


class DetalleDevolucion(models.Model):
    devolucion      = models.ForeignKey(Devolucion, on_delete=models.CASCADE,
                                        related_name='detalles')
    producto        = models.ForeignKey(Producto, on_delete=models.CASCADE,
                                        related_name='detalles_devolucion', null=True, blank=True)
    presentacion    = models.ForeignKey('productos.PresentacionProducto', on_delete=models.CASCADE,
                                        related_name='detalles_devolucion', null=True, blank=True)
    lote            = models.ForeignKey('inventario.Lote', on_delete=models.SET_NULL,
                                        null=True, blank=True, related_name='detalles_devolucion')
    cantidad        = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        verbose_name        = 'Detalle de Devolución'
        verbose_name_plural = 'Detalles de Devolución'

    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def __str__(self):
        return f'{self.presentacion.producto.nombre} ({self.presentacion.nombre}) x{self.cantidad}'