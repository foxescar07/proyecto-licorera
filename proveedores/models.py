from django.db import models
from django.conf import settings

class Proveedor(models.Model):
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
        ('sancionado', 'Sancionado'),
    ]
    
    TIPO_CHOICES = [
        ('distribuidor', 'Distribuidor'),
        ('fabricante', 'Fabricante'),
        ('importador', 'Importador'),
    ]
    
    nombre_empresa = models.CharField(max_length=200, unique=True)
    nombre_contacto = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=20, blank=True)
    direccion = models.TextField(blank=True)
    ciudad = models.CharField(max_length=100, blank=True)
    tipo_proveedor = models.CharField(max_length=20, choices=TIPO_CHOICES, default='distribuidor')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='activo')
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'
    
    def __str__(self):
        return self.nombre_empresa
    
    def get_tipo_proveedor_display(self):
        return dict(self.TIPO_CHOICES).get(self.tipo_proveedor, self.tipo_proveedor)
    
    def get_estado_display(self):
        return dict(self.ESTADO_CHOICES).get(self.estado, self.estado)