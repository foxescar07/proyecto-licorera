from django.conf import settings  # type: ignore
from django.db import models
from django.utils import timezone

from productos.models import Producto, PresentacionProducto


class Lote(models.Model):
    """MER: lote (#codigo, stock_actual, costo_unitario, fecha_vencimiento,
    fecha_registro, documento_usuario(fk), codigo_producto(fk), codigo_presentacion(fk))"""

    numero_lote       = models.CharField(max_length=100, unique=True)
    producto          = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name='lotes'
    )
    presentacion      = models.ForeignKey(
        PresentacionProducto,
        on_delete=models.PROTECT,
        related_name='lotes'
    )
    stock_actual      = models.PositiveIntegerField(default=0)
    costo_unitario    = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    fecha_registro    = models.DateTimeField(default=timezone.now, editable=False)
    registrado_por    = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='lotes_registrados'
    )

    class Meta:
        verbose_name        = 'Lote'
        verbose_name_plural = 'Lotes'
        ordering            = ['-fecha_registro']

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
    """MER: inventario (#codigo_inventario, codigo_producto(fk),
    codigo_presentacion(fk), stock_actual, stock_min, stock_max)

    Ya NO es un log de movimientos: es el registro de stock vigente y sus
    umbrales por presentación. El histórico de entradas/salidas ahora vive
    en compra/venta; los ajustes por conteo físico viven en Hallazgo.
    """

    producto      = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name='inventarios'
    )
    presentacion  = models.OneToOneField(
        PresentacionProducto,
        on_delete=models.PROTECT,
        related_name='inventario'
    )
    stock_actual  = models.PositiveIntegerField(default=0)
    stock_min     = models.PositiveIntegerField(default=0)
    stock_max     = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name        = 'Inventario'
        verbose_name_plural = 'Inventarios'

    def __str__(self):
        return f"Inventario {self.presentacion} - stock: {self.stock_actual}"

    @property
    def estado_stock(self):
        if self.stock_actual <= 0:
            return 'rojo'
        if self.stock_actual <= self.stock_min:
            return 'amarillo'
        return 'verde'


class AgendaInventario(models.Model):
    """MER: agenda_inventario (#codigo, fecha, tipo, estado, documento_usuario(fk))"""

    TIPO_CHOICES = [
        ('conteo_fisico', 'Conteo físico'),
        ('revision',      'Revisión'),
        ('auditoria',     'Auditoría'),
    ]
    ESTADO_CHOICES = [
        ('pendiente',  'Pendiente'),
        ('en_proceso', 'En proceso'),
        ('completada', 'Completada'),
        ('cancelada',  'Cancelada'),
    ]

    fecha           = models.DateTimeField()
    tipo            = models.CharField(max_length=30, choices=TIPO_CHOICES, default='conteo_fisico')
    estado          = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    documento_usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='agendas_inventario'
    )

    class Meta:
        verbose_name        = 'Agenda de Inventario'
        verbose_name_plural = 'Agendas de Inventario'
        ordering            = ['fecha']

    def __str__(self):
        return f"Agenda {self.pk} - {self.get_tipo_display()} ({self.fecha.date()})"


class Hallazgo(models.Model):
    """MER: hallazgo (#codigo, codigo_agenda(fk), codigo_producto(fk),
    cantidad_sistema, cantidad_fisica, diferencia, sesion_conteo,
    tipo_hallazgo, resultado_inventario, observaciones, fecha_hallazgo)

    Reemplaza a SesionConteo + ConteoProducto + ResultadoInventario.
    """

    TIPO_HALLAZGO_CHOICES = [
        ('sobrante', 'Sobrante'),
        ('faltante', 'Faltante'),
        ('ok',       'Sin diferencia'),
    ]

    agenda              = models.ForeignKey(
        AgendaInventario,
        on_delete=models.CASCADE,
        related_name='hallazgos'
    )
    producto            = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name='hallazgos'
    )
    cantidad_sistema     = models.IntegerField()
    cantidad_fisica       = models.IntegerField()
    diferencia            = models.IntegerField()
    sesion_conteo         = models.PositiveIntegerField(help_text='Número de sesión de conteo en la que se registró')
    tipo_hallazgo         = models.CharField(max_length=20, choices=TIPO_HALLAZGO_CHOICES)
    resultado_inventario  = models.CharField(max_length=100, blank=True)
    observaciones         = models.TextField(blank=True, null=True)
    fecha_hallazgo         = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Hallazgo'
        verbose_name_plural = 'Hallazgos'
        ordering            = ['-fecha_hallazgo']

    def __str__(self):
        return f"Hallazgo {self.pk} - {self.producto} ({self.diferencia})"

    def save(self, *args, **kwargs):
        self.diferencia = self.cantidad_fisica - self.cantidad_sistema
        if self.diferencia == 0:
            self.tipo_hallazgo = 'ok'
        elif self.diferencia > 0:
            self.tipo_hallazgo = 'sobrante'
        else:
            self.tipo_hallazgo = 'faltante'
        super().save(*args, **kwargs)