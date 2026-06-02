from django.db import models
from django.contrib.auth.models import User


class Perfil(models.Model):
    ROL_CHOICES = [
        ('admin',    'Administrador'),
        ('cajero',   'Cajero'),
        ('empleado', 'Empleado'),
    ]
    TIPO_ID_CHOICES = [
        ('CC',  'Cédula de Ciudadanía'),
        ('CE',  'Cédula de Extranjería'),
        ('TI',  'Tarjeta de Identidad'),
        ('PA',  'Pasaporte'),
        ('PT',  'Permiso de Permanencia Temporal'),
    ]

    user               = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    tipo_id            = models.CharField(max_length=5, choices=TIPO_ID_CHOICES, default='CC')
    identificacion     = models.CharField(max_length=20, unique=True)
    telefono           = models.CharField(max_length=15, blank=True, null=True)
    rol                = models.CharField(max_length=20, choices=ROL_CHOICES, default='empleado')
    activo             = models.BooleanField(default=True)
    reset_token        = models.CharField(max_length=64, blank=True, null=True)
    reset_token_expira = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name        = 'Perfil'
        verbose_name_plural = 'Perfiles'

    def __str__(self):
        return f'{self.nombre_completo} ({self.get_rol_display()})'

    @property
    def nombre(self):
        return self.user.first_name

    @property
    def apellidos(self):
        return self.user.last_name

    @property
    def nombre_completo(self):
        return f'{self.user.first_name} {self.user.last_name}'.strip()

    @property
    def email(self):
        return self.user.email

    @property
    def usuario(self):
        return self.user.username

    @property
    def fecha_registro(self):
        return self.user.date_joined