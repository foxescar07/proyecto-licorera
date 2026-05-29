from django.contrib.auth.models import User
from django.db import models

from productos.models import PresentacionProducto


class Lote(models.Model):
    numero_lote       = models.CharField(max_length=100, unique=True)
    presentacion      = models.ForeignKey(
        PresentacionProducto,
        on_delete=models.PROTECT,
        related_name='lotes'
    )
    stock_actual      = models.PositiveIntegerField(default=0)
    costo_unitario    = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    fecha_registro    = models.DateTimeField(auto_now_add=True)
    registrado_por    = models.ForeignKey(
        User,
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
        from django.utils import timezone
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
    TIPO_CHOICES = [
        ('entrada', 'Entrada'),
        ('salida',  'Salida'),
        ('ajuste',  'Ajuste'),
    ]

    presentacion   = models.ForeignKey(
        PresentacionProducto,
        on_delete=models.PROTECT,
        related_name='movimientos'
    )
    lote           = models.ForeignKey(
        Lote,
        on_delete=models.PROTECT,
        related_name='movimientos'
    )
    registrado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='movimientos_inventario'
    )
    tipo              = models.CharField(max_length=20, choices=TIPO_CHOICES)
    cantidad          = models.IntegerField()
    motivo            = models.CharField(max_length=255, blank=True)
    fecha_actualizada = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Movimiento de Inventario'
        verbose_name_plural = 'Movimientos de Inventario'
        ordering            = ['-fecha_actualizada']

    def __str__(self):
        return f"{self.tipo} - {self.presentacion} ({self.cantidad})"


class SesionConteo(models.Model):
    ESTADO_CHOICES = [
        ('activa',      'Activa'),
        ('finalizada',  'Finalizada'),
        ('cancelada',   'Cancelada'),
    ]

    fecha_inicio = models.DateTimeField(auto_now_add=True)
    estado       = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='activa')
    fecha_fin    = models.DateTimeField(null=True, blank=True)
    responsable  = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='sesiones_conteo'
    )

    class Meta:
        verbose_name        = 'Sesión de Conteo'
        verbose_name_plural = 'Sesiones de Conteo'
        ordering            = ['-fecha_inicio']

    def __str__(self):
        return f"Conteo {self.id} - {self.estado}"


class ConteoProducto(models.Model):
    sesion           = models.ForeignKey(
        SesionConteo,
        on_delete=models.CASCADE,
        related_name='conteos'
    )
    presentacion     = models.ForeignKey(
        PresentacionProducto,
        on_delete=models.PROTECT,
        related_name='conteos'
    )
    cantidad_contada = models.PositiveIntegerField(default=0)
    actualizado_en   = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Conteo de Producto'
        verbose_name_plural = 'Conteos de Producto'
        unique_together     = ('sesion', 'presentacion')

    def __str__(self):
        return f"{self.presentacion} - Contado: {self.cantidad_contada}"


class ResultadoInventario(models.Model):
    sesion       = models.ForeignKey(
        SesionConteo,
        on_delete=models.CASCADE,
        related_name='resultados'
    )
    presentacion = models.ForeignKey(
        PresentacionProducto,
        on_delete=models.PROTECT,
        related_name='resultados_inventario'
    )
    cantidad_sistema = models.IntegerField()
    cantidad_fisica  = models.IntegerField()
    diferencia       = models.IntegerField()

    class Meta:
        verbose_name        = 'Resultado de Inventario'
        verbose_name_plural = 'Resultados de Inventario'

    def __str__(self):
        return f"Resultado {self.presentacion} - Diferencia: {self.diferencia}"


class AgendaInventario(models.Model):
    ESTADO_CHOICES = [
        ('pendiente',   'Pendiente'),
        ('en_proceso',  'En proceso'),
        ('completada',  'Completada'),
        ('cancelada',   'Cancelada'),
    ]

    titulo           = models.CharField(max_length=200)
    descripcion      = models.TextField(blank=True, null=True)
    fecha_programada = models.DateTimeField()
    estado           = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    creado_por       = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='agendas_creadas'
    )
    responsable      = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='agendas_asignadas'
    )

    class Meta:
        verbose_name        = 'Agenda de Inventario'
        verbose_name_plural = 'Agendas de Inventario'
        ordering            = ['fecha_programada']

    def __str__(self):
        return f"{self.titulo} - {self.fecha_programada.date()}"