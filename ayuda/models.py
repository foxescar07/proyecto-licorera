from django.db import models
from django.conf import settings


class CategoriaAyuda(models.Model):
    """Agrupa artículos de ayuda por módulo (Ventas, Productos, etc.)"""
    nombre = models.CharField(max_length=50)
    icono = models.CharField(max_length=50, default='bi-question-circle-fill')
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['orden', 'nombre']
        verbose_name = 'Categoría de ayuda'
        verbose_name_plural = 'Categorías de ayuda'

    def __str__(self):
        return self.nombre


class ArticuloAyuda(models.Model):
    """Una FAQ o una guía rápida dentro de una categoría."""
    TIPO_CHOICES = [
        ('faq', 'Pregunta frecuente'),
        ('guia', 'Guía rápida'),
    ]

    categoria = models.ForeignKey(
        CategoriaAyuda, on_delete=models.CASCADE, related_name='articulos'
    )
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default='faq')
    titulo = models.CharField(max_length=150)
    contenido = models.TextField(help_text='Puedes usar HTML simple (listas, negritas, etc.)')
    orden = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['orden', 'titulo']
        verbose_name = 'Artículo de ayuda'
        verbose_name_plural = 'Artículos de ayuda'

    def __str__(self):
        return self.titulo


class MensajeSoporte(models.Model):
    """Mensajes que un empleado envía cuando no encuentra respuesta en la FAQ."""
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    asunto = models.CharField(max_length=150)
    mensaje = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    atendido = models.BooleanField(default=False)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Mensaje de soporte'
        verbose_name_plural = 'Mensajes de soporte'

    def __str__(self):
        return f'{self.asunto} — {self.usuario}'
