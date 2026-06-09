from django.db import models
from django.contrib.auth.models import AbstractUser

def renombrar_foto_perfil(instance, filename):
    ext = filename.split('.')[-1]
    return f'usuarios/fotos/{instance.username}.{ext}'

class Usuario(AbstractUser):
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

    tipo_id            = models.CharField(max_length=5, choices=TIPO_ID_CHOICES, default='CC', verbose_name='Tipo de ID')
    identificacion     = models.CharField(max_length=20, unique=True, verbose_name='Identificación')
    telefono           = models.CharField(max_length=15, blank=True, null=True, verbose_name='Teléfono')
    rol                = models.CharField(max_length=20, choices=ROL_CHOICES, default='empleado', verbose_name='Rol')
    activo             = models.BooleanField(default=True, verbose_name='Activo')
    reset_token        = models.CharField(max_length=64, blank=True, null=True)
    reset_token_expira = models.DateTimeField(blank=True, null=True)
    
    # Nuevos campos solicitados
    foto               = models.ImageField(upload_to=renombrar_foto_perfil, null=True, blank=True, verbose_name='Foto de Perfil')

    REQUIRED_FIELDS = ['identificacion', 'email']

    class Meta:
        verbose_name        = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        # Ajuste para cumplir con la Fase de Modelado sin errores visuales
        nombre_visible = self.nombre_completo if self.nombre_completo else self.username
        return f'{nombre_visible} ({self.get_rol_display()})'

    @property
    def nombre(self):
        return self.first_name

    @property
    def apellidos(self):
        return self.last_name

    @property
    def nombre_completo(self):
        return f'{self.first_name} {self.last_name}'.strip()

    @property
    def usuario(self):
        return self.username

    @property
    def fecha_registro(self):
        return self.date_joined

    @property
    def avatar_name(self):
        from urllib.parse import quote
        f_name = self.first_name.split()[0] if self.first_name else ''
        l_name = self.last_name.split()[0] if self.last_name else ''
        return f"{quote(f_name)}+{quote(l_name)}"

    def save(self, *args, **kwargs):
        if self.first_name:
            self.first_name = self.first_name.title()
        if self.last_name:
            self.last_name = self.last_name.title()
        super().save(*args, **kwargs)