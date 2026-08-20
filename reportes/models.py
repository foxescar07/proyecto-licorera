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
        ('devoluciones', 'Reporte de Devoluciones'),
    ]

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