from django.db import models
from django.conf import settings


class Reporte(models.Model):
    """
    Bitácora de reportes generados por los usuarios.

    Corresponde a la entidad 'reportes' del MER:
        #codigo
        *documento_usuario (FK -> usuario)
        *tipo_reporte
        *fecha
        *formato
        observaciones
    """

    TIPO_REPORTE_CHOICES = [
        ('ventas', 'Historial de Ventas'),
        ('inventario', 'Reporte de Inventario'),
        ('proveedores', 'Reporte de Proveedores'),
        ('resumen_diario', 'Resumen Diario'),
        ('analisis', 'Análisis de Ventas'),
        ('movimientos', 'Movimientos de Inventario'),
    ]


    id = models.AutoField(primary_key=True)
    presentacion_id = models.ForeignKey('productos.PresentacionProducto', on_delete=models.CASCADE)
    lote_id = models.ForeignKey('inventario.Lote', on_delete=models.CASCADE)
    sesion_conteo = models.CharField(max_length=50, null=True, blank=True)
    stock_sistema = models.IntegerField()
    stock_fisico = models.IntegerField()
    diferencia = models.IntegerField()
    estado_lote = models.CharField(max_length=50, choices=ESTADO_LOTE_CHOICES)
    fecha_vencimiento = models.DateField()
    generado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reportes_reporteinventario'
        ordering = ['-generado_en']
        verbose_name = "Reporte de Inventario"
        verbose_name_plural = "Reportes de Inventario"

    def __str__(self):
        return f"Inventario {self.presentacion_id} - Diferencia: {self.diferencia}"


class ReporteCaja(models.Model):
    """Reporte de caja y movimientos de dinero"""
    id = models.AutoField(primary_key=True)
    apertura_id = models.ForeignKey('ventas.AperturaCaja', on_delete=models.SET_NULL, null=True)
    cierre_id = models.ForeignKey('ventas.CierreCaja', on_delete=models.SET_NULL, null=True, blank=True)
    usuario_id = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    total_ventas = models.DecimalField(max_digits=12, decimal_places=2)
    total_devoluciones = models.DecimalField(max_digits=12, decimal_places=2)
    total_contado = models.DecimalField(max_digits=12, decimal_places=2)
    diferencia = models.DecimalField(max_digits=12, decimal_places=2)
    generado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reportes_reportecaja'
        ordering = ['-generado_en']
        verbose_name = "Reporte de Caja"
        verbose_name_plural = "Reportes de Caja"

    def __str__(self):
        return f"Caja - ${self.total_ventas}"


class ReporteCompra(models.Model):
    """Reporte de órdenes de compra"""
    ESTADO_ORDEN_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('confirmada', 'Confirmada'),
        ('recibida', 'Recibida'),
        ('facturada', 'Facturada'),
        ('cancelada', 'Cancelada'),
      
    FORMATO_CHOICES = [
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
      
    ]

    codigo = models.AutoField(primary_key=True)
    documento_usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reportes_generados',
    )
    tipo_reporte = models.CharField(max_length=50, choices=TIPO_REPORTE_CHOICES)
    fecha = models.DateTimeField(auto_now_add=True)
    formato = models.CharField(max_length=20, choices=FORMATO_CHOICES)
    observaciones = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'reportes_reporte'
        ordering = ['-fecha']
        verbose_name = "Reporte"
        verbose_name_plural = "Reportes"

    def __str__(self):
        usuario = self.documento_usuario or "Anónimo"
        return f"{self.get_tipo_reporte_display()} ({self.formato}) - {usuario} - {self.fecha.strftime('%Y-%m-%d %H:%M')}"