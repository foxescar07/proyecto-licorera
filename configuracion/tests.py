from django.test import TestCase

from .models import ConfiguracionEmpresa, BackupRegistro


class ConfiguracionEmpresaModelTest(TestCase):

    # -------------------------------------------------
    # Creación
    # -------------------------------------------------

    def test_crear_configuracion(self):
        config = ConfiguracionEmpresa.objects.create(
            nombre_empresa="Licorera CYS",
            nit="900123456",
            direccion="Calle 10 #20-30",
            telefono="3101234567",
            email="empresa@test.com",
            iva_porcentaje=19,
            moneda="COP",
            unidades_medida=["375ml", "750ml", "1L"]
        )

        self.assertEqual(config.nombre_empresa, "Licorera CYS")
        self.assertEqual(config.nit, "900123456")
        self.assertEqual(config.moneda, "COP")
        self.assertEqual(
            config.unidades_medida,
            ["375ml", "750ml", "1L"]
        )

    # -------------------------------------------------
    # __str__
    # -------------------------------------------------

    def test_str(self):
        config = ConfiguracionEmpresa.objects.create(
            nombre_empresa="Mi Empresa"
        )

        self.assertEqual(str(config), "Mi Empresa")

    # -------------------------------------------------
    # Valores por defecto
    # -------------------------------------------------

    def test_valores_por_defecto(self):
        config = ConfiguracionEmpresa.objects.create()

        self.assertEqual(config.nombre_empresa, "CYS Ltda")
        self.assertEqual(config.nit, "")
        self.assertEqual(config.direccion, "")
        self.assertEqual(config.telefono, "")
        self.assertEqual(config.email, "")
        self.assertEqual(config.iva_porcentaje, 19)
        self.assertEqual(config.moneda, "COP")
        self.assertEqual(config.unidades_medida, [])

    # -------------------------------------------------
    # get_config()
    # -------------------------------------------------

    def test_get_config_crea_registro(self):
        self.assertEqual(
            ConfiguracionEmpresa.objects.count(),
            0
        )

        config = ConfiguracionEmpresa.get_config()

        self.assertEqual(
            ConfiguracionEmpresa.objects.count(),
            1
        )

        self.assertEqual(config.pk, 1)

    def test_get_config_retorna_mismo_registro(self):
        config1 = ConfiguracionEmpresa.get_config()
        config2 = ConfiguracionEmpresa.get_config()

        self.assertEqual(config1.pk, config2.pk)
        self.assertEqual(
            ConfiguracionEmpresa.objects.count(),
            1
        )


class BackupRegistroModelTest(TestCase):

    # -------------------------------------------------
    # Creación
    # -------------------------------------------------

    def test_crear_backup(self):
        backup = BackupRegistro.objects.create(
            nombre="backup.sql",
            ruta="/respaldos/backup.sql",
            tamaño_mb=25.6
        )

        self.assertEqual(backup.nombre, "backup.sql")
        self.assertEqual(backup.ruta, "/respaldos/backup.sql")
        self.assertEqual(backup.tamaño_mb, 25.6)
        self.assertIsNotNone(backup.fecha)

    # -------------------------------------------------
    # __str__
    # -------------------------------------------------

    def test_str_backup(self):
        backup = BackupRegistro.objects.create(
            nombre="respaldo.zip"
        )

        self.assertEqual(str(backup), "respaldo.zip")

    # -------------------------------------------------
    # Valores por defecto
    # -------------------------------------------------

    def test_valores_por_defecto_backup(self):
        backup = BackupRegistro.objects.create(
            nombre="backup.sql"
        )

        self.assertEqual(backup.ruta, "")
        self.assertEqual(backup.tamaño_mb, 0)
        self.assertIsNotNone(backup.fecha)

    # -------------------------------------------------
    # Ordering
    # -------------------------------------------------

    def test_ordering_por_fecha_descendente(self):
        primero = BackupRegistro.objects.create(
            nombre="backup1"
        )

        segundo = BackupRegistro.objects.create(
            nombre="backup2"
        )

        backups = list(BackupRegistro.objects.all())

        self.assertEqual(backups[0], segundo)
        self.assertEqual(backups[1], primero)