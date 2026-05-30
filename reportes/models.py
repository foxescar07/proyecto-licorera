from django.db import models
from django.contrib.auth.models import User

class ReporteGenerado(models.Model):
    TIPO_CHOICES = [
        ('inventario', 'Estado de Inventario'),
        ('movimientos', 'Movimientos de Stock'),
        ('vencimientos', 'Productos por Vencer'),
    ]

    titulo = models.CharField(max_length=200)
    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    archivo = models.FileField(upload_to='reportes/archivos/', null=True, blank=True)

    def __str__(self):
        return f"{self.titulo} ({self.get_tipo_display()})"