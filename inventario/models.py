from django.contrib.auth.models import User
from django.db import models

from productos.models import PresentacionProducto


class Lote(models.Model):
    numero_lote = models.CharField(max_length=100, unique=True)
    presentacion = models.ForeignKey(
        PresentacionProducto,
        on_delete=models.PROTECT,
        related_name='lotes'
    )
    # ✅ CORRECCIÓN #10: Lote referencia a DetalleCompra (no al revés)
    # Se importa con string para evitar dependencia circular con compras
    # FK a compras.DetalleCompra — se activa cuando se cree la app compras
# detalle_compra = models.ForeignKey(
#     'compras.DetalleCompra',
#     null=True,
#     blank=True,
#     on_delete=models.SET_NULL,
#     related_name='lotes'
# )
    stock_actual = models.PositiveIntegerField(default=0)
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    registrado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='lotes_registrados'
    )

    class Meta:
        verbose_name = 'Lote'
        verbose_name_plural = 'Lotes'

    def __str__(self):
        return f"{self.numero_lote} - {self.presentacion}"


class Inventario(models.Model):
    TIPO_CHOICES = [
        ('entrada', 'Entrada'),
        ('salida', 'Salida'),
        ('ajuste', 'Ajuste'),
    ]

    presentacion = models.ForeignKey(
        PresentacionProducto,
        on_delete=models.PROTECT,
        related_name='movimientos'
    )
    lote = models.ForeignKey(
        Lote,
        on_delete=models.PROTECT,
        related_name='movimientos'
    )
    # ✅ CORRECCIÓN #8: Se agregó registrado_por para trazabilidad
    registrado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='movimientos_inventario'
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    cantidad = models.IntegerField()
    motivo = models.CharField(max_length=255, blank=True)
    fecha_actualizada = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Movimiento de Inventario'
        verbose_name_plural = 'Movimientos de Inventario'

    def __str__(self):
        return f"{self.tipo} - {self.presentacion} ({self.cantidad})"


class SesionConteo(models.Model):
    ESTADO_CHOICES = [
        ('activa', 'Activa'),
        ('finalizada', 'Finalizada'),
        ('cancelada', 'Cancelada'),
    ]

    fecha_inicio = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='activa')
    fecha_fin = models.DateTimeField(null=True, blank=True)
    responsable = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='sesiones_conteo'
    )

    class Meta:
        verbose_name = 'Sesión de Conteo'
        verbose_name_plural = 'Sesiones de Conteo'

    def __str__(self):
        return f"Conteo {self.id} - {self.estado}"


class ConteoProducto(models.Model):
    sesion = models.ForeignKey(
        SesionConteo,
        on_delete=models.CASCADE,
        related_name='conteos'
    )
    presentacion = models.ForeignKey(
        PresentacionProducto,
        on_delete=models.PROTECT,
        related_name='conteos'
    )
    cantidad_contada = models.PositiveIntegerField(default=0)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Conteo de Producto'
        verbose_name_plural = 'Conteos de Producto'

    def __str__(self):
        return f"{self.presentacion} - Contado: {self.cantidad_contada}"


class ResultadoInventario(models.Model):
    sesion = models.ForeignKey(
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
    cantidad_fisica = models.IntegerField()
    diferencia = models.IntegerField()

    class Meta:
        verbose_name = 'Resultado de Inventario'
        verbose_name_plural = 'Resultados de Inventario'

    def __str__(self):
        return f"Resultado {self.presentacion} - Diferencia: {self.diferencia}"


class AgendaInventario(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('en_proceso', 'En proceso'),
        ('completada', 'Completada'),
        ('cancelada', 'Cancelada'),
    ]

    titulo = models.CharField(max_length=200)
    fecha_programada = models.DateTimeField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    # ✅ CORRECCIÓN #7: Se agregaron creado_por y responsable
    creado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='agendas_creadas'
    )
    responsable = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='agendas_asignadas'
    )

    class Meta:
        verbose_name = 'Agenda de Inventario'
        verbose_name_plural = 'Agendas de Inventario'

    def __str__(self):
        return f"{self.titulo} - {self.fecha_programada.date()}"