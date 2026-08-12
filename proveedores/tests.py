from django.test import TestCase
from django.core.exceptions import ValidationError
from .models import Proveedor, ProveedorCategoria, DetalleCompra, Compra, HistorialCompra
from productos.models import Categoria, Producto, PresentacionProducto
from usuarios.models import Usuario
from decimal import Decimal


class ProveedorModelTest(TestCase):
    """Tests para el modelo Proveedor."""

    def setUp(self):
        """Crear datos de prueba para cada test."""
        self.proveedor = Proveedor.objects.create(
            nombre_empresa="Distribuidora La Ceiba",
            email="ceiba@test.com",
            telefono="3001234567",
            tipo_proveedor='distribuidor',
            estado='activo'
        )

    # ✓ US-001: Crear proveedor válido
    def test_crear_proveedor_valido(self):
        """Verificar que se crea un proveedor con datos válidos."""
        self.assertEqual(self.proveedor.nombre_empresa, "Distribuidora La Ceiba")
        self.assertEqual(self.proveedor.estado, 'activo')
        self.assertEqual(self.proveedor.tipo_proveedor, 'distribuidor')
        self.assertTrue(Proveedor.objects.filter(
            nombre_empresa="Distribuidora La Ceiba"
        ).exists())

    # ✓ US-001: Email único
    def test_email_unico_no_duplicados(self):
        """Verificar que no permite emails duplicados."""
        with self.assertRaises(Exception):
            Proveedor.objects.create(
                nombre_empresa="Otra Distribuidora",
                email="ceiba@test.com",
                tipo_proveedor='distribuidor'
            )

    # ✓ US-001: Nombre empresa único
    def test_nombre_empresa_unico(self):
        """Verificar que no permite nombres de empresa duplicados."""
        with self.assertRaises(Exception):
            Proveedor.objects.create(
                nombre_empresa="Distribuidora La Ceiba",
                email="otro@test.com",
                tipo_proveedor='distribuidor'
            )

    # ✓ US-001: Teléfono formato válido
    def test_telefono_formato_valido(self):
        """Verificar que acepta teléfonos con 7-15 dígitos."""
        telefonos_validos = ["3001234567", "1234567", "123456789012345"]
        for tel in telefonos_validos:
            proveedor = Proveedor(
                nombre_empresa=f"Dist_{tel}",
                email=f"{tel}@test.com",
                telefono=tel,
                tipo_proveedor='distribuidor'
            )
            try:
                proveedor.full_clean()
            except ValidationError:
                self.fail(f"Teléfono {tel} fue rechazado incorrectamente")

    # ✓ US-001: Teléfono formato inválido
    def test_telefono_formato_invalido(self):
        """Verificar que rechaza teléfonos con formato inválido."""
        proveedor = Proveedor(
            nombre_empresa="Test Invalid",
            email="invalid@test.com",
            telefono="abc123def",
            tipo_proveedor='distribuidor'
        )
        with self.assertRaises(ValidationError):
            proveedor.full_clean()

    # ✓ US-002: Asignar categoría a proveedor
    def test_asignar_categoria_a_proveedor(self):
        """Verificar que se puede asociar una categoría a un proveedor."""
        categoria = Categoria.objects.create(
            codigo="RON",
            nombre="Ron"
        )
        prov_cat = ProveedorCategoria.objects.create(
            proveedor=self.proveedor,
            categoria=categoria
        )
        self.assertEqual(prov_cat.proveedor, self.proveedor)
        self.assertEqual(prov_cat.categoria, categoria)
        self.assertTrue(
            ProveedorCategoria.objects.filter(
                proveedor=self.proveedor,
                categoria=categoria
            ).exists()
        )

    # ✓ US-002: No duplicar categoría para mismo proveedor
    def test_no_duplicar_categoria_proveedor(self):
        """Verificar que no permite la misma categoría dos veces."""
        categoria = Categoria.objects.create(codigo="WHISKY", nombre="Whisky")
        ProveedorCategoria.objects.create(
            proveedor=self.proveedor,
            categoria=categoria
        )
        with self.assertRaises(Exception):
            ProveedorCategoria.objects.create(
                proveedor=self.proveedor,
                categoria=categoria
            )

    # ✓ US-003: Cambiar estado a sancionado con motivo
    def test_cambiar_estado_sancionado_con_motivo(self):
        """Verificar que se puede cambiar estado a sancionado."""
        self.proveedor.estado = 'sancionado'
        self.proveedor.observacion = 'Incumplimiento de contrato'
        self.proveedor.save()

        proveedor_actualizado = Proveedor.objects.get(id=self.proveedor.id)
        self.assertEqual(proveedor_actualizado.estado, 'sancionado')
        self.assertIsNotNone(proveedor_actualizado.observacion)

    # ✓ US-003: Sancionado sin motivo genera error
    def test_sancionado_requiere_motivo(self):
        """Verificar que no se puede sancionar sin motivo."""
        proveedor = Proveedor(
            nombre_empresa="Test Sancion",
            email="sancion@test.com",
            estado='sancionado'
        )
        with self.assertRaises(ValidationError):
            proveedor.full_clean()

    # ✓ Validación: Valores por defecto
    def test_valores_por_defecto(self):
        """Verificar que tiene valores por defecto correctos."""
        nuevo = Proveedor.objects.create(
            nombre_empresa="Test Default",
            email="default@test.com"
        )
        self.assertEqual(nuevo.estado, 'activo')
        self.assertEqual(nuevo.tipo_proveedor, 'distribuidor')

    # ✓ Validación: String representation
    def test_str_representation(self):
        """Verificar que __str__ retorna nombre y estado."""
        esperado = f"{self.proveedor.nombre_empresa} (Activo)"
        self.assertEqual(str(self.proveedor), esperado)

    # ✓ US-002: Editar proveedor con cambios válidos en todos los campos
    def test_editar_proveedor_cambios_validos_todos_campos(self):
        """Verificar que se pueden editar todos los campos válidos del proveedor.

        Escenario: Un usuario con permisos edita un proveedor existente cambiando
        todos los campos editables (nombre_empresa, nit, email, telefono,
        tipo_proveedor, estado, observacion).

        Datos de entrada:
        - Nombre empresa original: "Distribuidora La Ceiba"
        - Nuevos valores a cambiar:
          * nombre_empresa: "Distribuidora Premium Export"
          * nit: "123456789-0"
          * email: "premium.export@test.com"
          * telefono: "3157654321"
          * tipo_proveedor: "importador" (cambio de "distribuidor")
          * estado: "inactivo" (cambio de "activo")
          * observacion: "Proveedor temporal para importación especial"

        Resultado esperado:
        - Todos los cambios se guardan correctamente
        - Los datos se persisten en la base de datos
        - El proveedor se puede recuperar con los nuevos valores
        """
        # Guardar valores originales para verificación
        proveedor_id = self.proveedor.id

        # Actualizar todos los campos editables
        self.proveedor.nombre_empresa = "Distribuidora Premium Export"
        self.proveedor.nit = "123456789-0"
        self.proveedor.email = "premium.export@test.com"
        self.proveedor.telefono = "3157654321"
        self.proveedor.tipo_proveedor = "importador"
        self.proveedor.estado = "inactivo"
        self.proveedor.observacion = "Proveedor temporal para importación especial"
        self.proveedor.save()

        # Recuperar el proveedor de la base de datos para verificar persistencia
        proveedor_actualizado = Proveedor.objects.get(id=proveedor_id)

        # Verificaciones de cambios exitosos
        self.assertEqual(proveedor_actualizado.nombre_empresa, "Distribuidora Premium Export")
        self.assertEqual(proveedor_actualizado.nit, "123456789-0")
        self.assertEqual(proveedor_actualizado.email, "premium.export@test.com")
        self.assertEqual(proveedor_actualizado.telefono, "3157654321")
        self.assertEqual(proveedor_actualizado.tipo_proveedor, "importador")
        self.assertEqual(proveedor_actualizado.estado, "inactivo")
        self.assertEqual(proveedor_actualizado.observacion, "Proveedor temporal para importación especial")

        # Verificar que el ID no cambió (es el mismo registro)
        self.assertEqual(proveedor_actualizado.id, proveedor_id)

        # Verificar que fecha_registro se mantiene igual
        self.assertEqual(proveedor_actualizado.fecha_registro, self.proveedor.fecha_registro)

        # Verificar que solo existe 1 proveedor en la BD (no se duplicó)
        self.assertEqual(Proveedor.objects.count(), 1)
