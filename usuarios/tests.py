from django.test import TestCase
from django.utils import timezone
from urllib.parse import quote

from .models import Usuario, renombrar_foto_perfil


class UsuarioModelTest(TestCase):

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username='cristian',
            password='123456',
            first_name='cristian',
            last_name='canaria sogamoso',
            email='cristian@test.com',
            identificacion='123456789',
            telefono='3001234567',
            rol='admin'
        )

    # -------------------------------------------------
    # Creación
    # -------------------------------------------------

    def test_usuario_se_crea_correctamente(self):
        self.assertEqual(self.usuario.username, 'cristian')
        self.assertEqual(self.usuario.identificacion, '123456789')
        self.assertEqual(self.usuario.rol, 'admin')
        self.assertTrue(self.usuario.activo)

    # -------------------------------------------------
    # __str__
    # -------------------------------------------------

    def test_str_usuario(self):
        esperado = "Cristian Canaria Sogamoso (Administrador)"
        self.assertEqual(str(self.usuario), esperado)

    # -------------------------------------------------
    # Propiedades
    # -------------------------------------------------

    def test_propiedad_nombre(self):
        self.assertEqual(self.usuario.nombre, "Cristian")

    def test_propiedad_apellidos(self):
        self.assertEqual(self.usuario.apellidos, "Canaria Sogamoso")

    def test_nombre_completo(self):
        self.assertEqual(
            self.usuario.nombre_completo,
            "Cristian Canaria Sogamoso"
        )

    def test_usuario_property(self):
        self.assertEqual(self.usuario.usuario, "cristian")

    def test_fecha_registro(self):
        self.assertIsNotNone(self.usuario.fecha_registro)

    # -------------------------------------------------
    # Avatar
    # -------------------------------------------------

    def test_avatar_name(self):
        esperado = f"{quote('Cristian')}+{quote('Canaria')}"
        self.assertEqual(self.usuario.avatar_name, esperado)

    # -------------------------------------------------
    # Save()
    # -------------------------------------------------

    def test_save_capitaliza_nombres(self):
        usuario = Usuario.objects.create_user(
            username='juan',
            password='123456',
            first_name='jUaN',
            last_name='péRez gómez',
            identificacion='987654321'
        )

        self.assertEqual(usuario.first_name, "Juan")
        self.assertEqual(usuario.last_name, "Pérez Gómez")

    # -------------------------------------------------
    # Renombrar foto
    # -------------------------------------------------

    def test_renombrar_foto_perfil(self):
        ruta = renombrar_foto_perfil(self.usuario, "foto.png")
        self.assertEqual(
            ruta,
            "usuarios/fotos/cristian.png"
        )

    # -------------------------------------------------
    # Valores por defecto
    # -------------------------------------------------

    def test_valores_por_defecto(self):
        usuario = Usuario.objects.create_user(
            username='empleado',
            password='123456',
            identificacion='55555'
        )

        self.assertEqual(usuario.rol, 'empleado')
        self.assertEqual(usuario.tipo_id, 'CC')
        self.assertTrue(usuario.activo)

    # -------------------------------------------------
    # Nombre completo vacío
    # -------------------------------------------------

    def test_nombre_completo_vacio(self):
        usuario = Usuario.objects.create_user(
            username='test',
            password='123456',
            identificacion='999999'
        )

        self.assertEqual(usuario.nombre_completo, '')

    # -------------------------------------------------
    # __str__ sin nombres
    # -------------------------------------------------

    def test_str_sin_nombre(self):
        usuario = Usuario.objects.create_user(
            username='usuario1',
            password='123456',
            identificacion='111111'
        )

        self.assertEqual(
            str(usuario),
            "usuario1 (Empleado)"
        )