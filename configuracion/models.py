from django.db import models


class ConfiguracionEmpresa(models.Model):
    nombre_empresa  = models.CharField(max_length=200, default='CYS Ltda')
    nit             = models.CharField(max_length=50,  blank=True, default='')
    direccion       = models.CharField(max_length=300, blank=True, default='')
    telefono        = models.CharField(max_length=50,  blank=True, default='')
    email           = models.EmailField(blank=True, default='')
    iva_porcentaje  = models.DecimalField(max_digits=5, decimal_places=2, default=19)
    moneda          = models.CharField(max_length=10, default='COP')
    unidades_medida = models.JSONField(default=list)   # ['750ml', '1L', '375ml']

    class Meta:
        verbose_name        = 'Configuración de Empresa'
        verbose_name_plural = 'Configuración de Empresa'

    def __str__(self):
        return self.nombre_empresa

    @classmethod
    def get_config(cls):
        """Devuelve la única fila de configuración, creándola si no existe."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class BackupRegistro(models.Model):
    nombre    = models.CharField(max_length=200)
    ruta      = models.CharField(max_length=500, blank=True)
    fecha     = models.DateTimeField(auto_now_add=True)
    tamaño_mb = models.FloatField(default=0)

    class Meta:
        verbose_name        = 'Respaldo'
        verbose_name_plural = 'Respaldos'
        ordering            = ['-fecha']

    def __str__(self):
        return self.nombre