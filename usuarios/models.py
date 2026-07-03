from django.db import models
from django.contrib.auth.models import AbstractUser
from urllib.parse import quote


# ── FUNCIÓN DE RENOMBRADO (nivel módulo) ───────────────────────────────────────
def renombrar_foto_perfil(instance, filename):
    ext = filename.split('.')[-1]
    return f'usuarios/fotos/{instance.username}.{ext}'


# ── HELPERS DE AVATAR (nivel módulo) ──────────────────────────────────────────
def _get_avatar_first(first_name):
    return first_name.split()[0] if first_name else ''


def _get_avatar_last(last_name):
    return last_name.split()[0] if last_name else ''


# ── MODELO ─────────────────────────────────────────────────────────────────────
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
    foto               = models.ImageField(upload_to=renombrar_foto_perfil, null=True, blank=True, verbose_name='Foto de Perfil')

    REQUIRED_FIELDS = ['identificacion', 'email']

    class Meta:
        verbose_name        = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        nombre_visible = self.nombre_completo if self.nombre_completo else self.username
        return f'{nombre_visible} ({self.get_rol_display()})'

    # ── Propiedades ──────────────────────────────────────────────────────────

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
        f_name = _get_avatar_first(self.first_name)
        l_name = _get_avatar_last(self.last_name)
        return f'{quote(f_name)}+{quote(l_name)}'

    # ── Save ─────────────────────────────────────────────────────────────────

    def save(self, *args, **kwargs):
        if self.first_name:
            self.first_name = self.first_name.title()
        if self.last_name:
            self.last_name = self.last_name.title()
        super().save(*args, **kwargs)


# ── ACTIVIDAD DE USUARIOS ──────────────────────────────────────────────────────
class RegistroActividad(models.Model):
    usuario = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.CASCADE,
        related_name='registros_actividad',
        verbose_name='Usuario'
    )
    fecha_hora  = models.DateTimeField(auto_now_add=True, verbose_name='Fecha y hora')
    ip_address  = models.GenericIPAddressField(null=True, blank=True, verbose_name='Dirección IP')

    class Meta:
        ordering            = ['-fecha_hora']
        verbose_name        = 'Registro de actividad'
        verbose_name_plural = 'Registros de actividad'

    def __str__(self):
        return f'{self.usuario} - {self.fecha_hora:%d/%m/%Y %H:%M}'