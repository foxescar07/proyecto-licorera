from django.db import models
from django.conf import settings
from productos.models import Producto

class AgendaInventario(models.Model):
    ESTADO_CHOICES = [
        ("pendiente", "Pendiente"),
        ("en_proceso", "En proceso"),
        ("completada", "Completada"),
        ("cancelada", "Cancelada"),
    ]
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    fecha = models.DateTimeField()
    tipo = models.CharField(max_length=50, blank=True)
    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES, default="pendiente"
    )
    documento_usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="agendas_creadas",
        null=True,
        blank=True,
    )
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="agendas_asignadas",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Agenda de Inventario"
        verbose_name_plural = "Agendas de Inventario"
        ordering = ["fecha"]

    def __str__(self):
        return f"{self.titulo} - {self.fecha.date()}"


class Hallazgo(models.Model):
    TIPO_HALLAZGO_CHOICES = [
        ("faltante", "Faltante"),
        ("sobrante", "Sobrante"),
        ("exacto", "Exacto"),
    ]
    agenda = models.ForeignKey(
        AgendaInventario, on_delete=models.CASCADE, related_name="hallazgos"
    )
    producto = models.ForeignKey(
        Producto, on_delete=models.PROTECT, related_name="hallazgos_bodega"
    )
    cantidad_sistema = models.IntegerField()
    cantidad_fisica = models.IntegerField()
    diferencia = models.IntegerField()
    sesion_conteo = models.CharField(max_length=50)
    tipo_hallazgo = models.CharField(max_length=20, choices=TIPO_HALLAZGO_CHOICES)
    resultado_inventario = models.CharField(max_length=255, blank=True)
    observaciones = models.TextField(blank=True)
    fecha_hallazgo = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Hallazgo"
        verbose_name_plural = "Hallazgos"
        ordering = ["-fecha_hallazgo"]

    def __str__(self):
        return f"Hallazgo {self.producto} ({self.diferencia})"

    def save(self, *args, **kwargs):
        self.diferencia = self.cantidad_fisica - self.cantidad_sistema
        if self.diferencia > 0:
            self.tipo_hallazgo = "sobrante"
        elif self.diferencia < 0:
            self.tipo_hallazgo = "faltante"
        else:
            self.tipo_hallazgo = "exacto"
        super().save(*args, **kwargs)