from django.test import TestCase
from django.core.exceptions import ValidationError
from .models import Proveedor, ProveedorCategoria, OrdenCompra, DetalleCompra
from productos.models import Categoria, Producto, PresentacionProducto
from usuarios.models import Usuario


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
        self.proveedor.motivo_sancion = 'Incumplimiento de contrato'
        self.proveedor.save()

        proveedor_actualizado = Proveedor.objects.get(id=self.proveedor.id)
        self.assertEqual(proveedor_actualizado.estado, 'sancionado')
        self.assertIsNotNone(proveedor_actualizado.motivo_sancion)

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


class OrdenCompraModelTest(TestCase):
    """Tests para el modelo OrdenCompra."""

    def setUp(self):
        """Crear datos de prueba."""
        self.usuario = Usuario.objects.create_user(
            username='empleado1',
            email='emp@test.com',
            password='pass123'
        )
        self.proveedor = Proveedor.objects.create(
            nombre_empresa="Dist Test",
            email="dist@test.com",
            tipo_proveedor='distribuidor'
        )
        self.orden = OrdenCompra.objects.create(
            proveedor=self.proveedor,
            registrado_por=self.usuario,
            estado='pendiente',
            total=0
        )

    # ✓ US-010: Crear orden de compra
    def test_crear_orden_compra(self):
        """Verificar que se crea una orden en estado pendiente."""
        self.assertEqual(self.orden.estado, 'pendiente')
        self.assertEqual(self.orden.proveedor, self.proveedor)
        self.assertEqual(self.orden.registrado_por, self.usuario)
        self.assertEqual(self.orden.total, 0)

    # ✓ US-010: Orden requiere proveedor
    def test_orden_requiere_proveedor(self):
        """Verificar que una orden necesita un proveedor."""
        with self.assertRaises(Exception):
            OrdenCompra.objects.create(
                proveedor=None,
                estado='pendiente'
            )

    # ✓ US-011: Cambiar estado de orden
    def test_cambiar_estado_pendiente_a_confirmada(self):
        """Verificar transición: pendiente → confirmada."""
        self.orden.estado = 'confirmada'
        self.orden.save()

        orden_actualizada = OrdenCompra.objects.get(id=self.orden.id)
        self.assertEqual(orden_actualizada.estado, 'confirmada')

    # ✓ US-011: Cambiar a estado recibida
    def test_cambiar_estado_a_recibida(self):
        """Verificar transición: confirmada → recibida."""
        self.orden.estado = 'confirmada'
        self.orden.save()

        self.orden.estado = 'recibida'
        self.orden.save()

        self.assertEqual(self.orden.estado, 'recibida')

    # ✓ US-011: Cambiar a estado cancelada
    def test_cambiar_estado_a_cancelada(self):
        """Verificar transición a cancelada."""
        self.orden.estado = 'cancelada'
        self.orden.save()

        self.assertEqual(self.orden.estado, 'cancelada')

    # ✓ US-012: Calcular total de orden
    def test_calcular_total_orden(self):
        """Verificar que calcula correctamente el total."""
        categoria = Categoria.objects.create(codigo="RON", nombre="Ron")
        producto = Producto.objects.create(
            codigo="BACARDI",
            nombre="Bacardi",
            categoria=categoria
        )
        presentacion = PresentacionProducto.objects.create(
            producto=producto,
            nombre="750ml",
            unidades=1,
            precio=45000
        )

        DetalleCompra.objects.create(
            orden_compra=self.orden,
            presentacion=presentacion,
            cantidad=24,
            precio_unitario=45000
        )

        self.orden.calcular_total()
        self.assertEqual(self.orden.total, 24 * 45000)

    # ✓ Validación: Total no puede ser negativo
    def test_total_no_negativo(self):
        """Verificar que el total no puede ser negativo."""
        self.orden.total = -1000
        with self.assertRaises(ValidationError):
            self.orden.full_clean()

    # ✓ Validación: String representation
    def test_str_representation(self):
        """Verificar que __str__ muestra ID y proveedor."""
        esperado = f"Orden #{self.orden.id} - {self.proveedor.nombre_empresa}"
        self.assertEqual(str(self.orden), esperado)


class DetalleCompraModelTest(TestCase):
    """Tests para el modelo DetalleCompra."""

    def setUp(self):
        """Crear datos de prueba."""
        self.usuario = Usuario.objects.create_user(username='emp', password='pass')

        self.proveedor = Proveedor.objects.create(
            nombre_empresa="Dist",
            email="dist@test.com"
        )

        self.orden = OrdenCompra.objects.create(
            proveedor=self.proveedor,
            registrado_por=self.usuario
        )

        self.categoria = Categoria.objects.create(codigo="RON", nombre="Ron")
        self.producto = Producto.objects.create(
            codigo="BACARDI",
            nombre="Bacardi",
            categoria=self.categoria
        )

        self.presentacion = PresentacionProducto.objects.create(
            producto=self.producto,
            nombre="750ml",
            unidades=1,
            precio=45000
        )

    # ✓ US-010: Crear detalle de compra válido
    def test_crear_detalle_compra_valido(self):
        """Verificar que se crea un detalle con datos válidos."""
        detalle = DetalleCompra.objects.create(
            orden_compra=self.orden,
            presentacion=self.presentacion,
            cantidad=24,
            precio_unitario=45000
        )

        self.assertEqual(detalle.cantidad, 24)
        self.assertEqual(detalle.precio_unitario, 45000)
        self.assertEqual(detalle.subtotal, 24 * 45000)

    # ✓ Validación: Cantidad positiva
    def test_cantidad_debe_ser_positiva(self):
        """Verificar que cantidad debe ser > 0."""
        detalle = DetalleCompra(
            orden_compra=self.orden,
            presentacion=self.presentacion,
            cantidad=0,
            precio_unitario=45000
        )
        with self.assertRaises(ValidationError):
            detalle.full_clean()

    # ✓ Validación: Precio positivo
    def test_precio_debe_ser_positivo(self):
        """Verificar que precio debe ser > 0."""
        detalle = DetalleCompra(
            orden_compra=self.orden,
            presentacion=self.presentacion,
            cantidad=10,
            precio_unitario=-5000
        )
        with self.assertRaises(ValidationError):
            detalle.full_clean()

    # ✓ Validación: Cantidad mínima
    def test_cantidad_minima_es_uno(self):
        """Verificar que cantidad mínima es 1."""
        with self.assertRaises(ValidationError):
            detalle = DetalleCompra(
                orden_compra=self.orden,
                presentacion=self.presentacion,
                cantidad=0,
                precio_unitario=45000
            )
            detalle.full_clean()

    # ✓ Calcular subtotal automático
    def test_subtotal_calculado_automaticamente(self):
        """Verificar que subtotal se calcula automáticamente."""
        detalle = DetalleCompra.objects.create(
            orden_compra=self.orden,
            presentacion=self.presentacion,
            cantidad=10,
            precio_unitario=50000
        )
        self.assertEqual(detalle.subtotal, 10 * 50000)
        self.assertEqual(detalle.subtotal, 500000)

    # ✓ Validación: Requiere presentación
    def test_requiere_presentacion(self):
        """Verificar que es obligatoria la presentación."""
        with self.assertRaises(Exception):
            DetalleCompra.objects.create(
                orden_compra=self.orden,
                presentacion=None,
                cantidad=10,
                precio_unitario=45000
            )

    # ✓ Validación: String representation
    def test_str_representation(self):
        """Verificar que __str__ muestra presentación y cantidad."""
        detalle = DetalleCompra.objects.create(
            orden_compra=self.orden,
            presentacion=self.presentacion,
            cantidad=24,
            precio_unitario=45000
        )
        esperado = f"{self.presentacion.nombre} - 24 uds"
        self.assertEqual(str(detalle), esperado)


class OrdenCompraIntegrationTest(TestCase):
    """Tests de integración para flujo completo de compra."""

    def setUp(self):
        """Crear datos para tests de integración."""
        self.usuario = Usuario.objects.create_user(username='empleado', password='pass')
        self.proveedor = Proveedor.objects.create(
            nombre_empresa="Distribuidora Test",
            email="dist@test.com"
        )
        self.categoria = Categoria.objects.create(codigo="RON", nombre="Ron")
        self.producto = Producto.objects.create(
            codigo="BACARDI",
            nombre="Bacardi",
            categoria=self.categoria
        )
        self.presentacion = PresentacionProducto.objects.create(
            producto=self.producto,
            nombre="750ml",
            unidades=1,
            precio=45000
        )

    # ✓ Flujo completo: Crear orden → Agregar detalles → Calcular total
    def test_flujo_completo_compra(self):
        """Verificar flujo completo de una compra."""
        orden = OrdenCompra.objects.create(
            proveedor=self.proveedor,
            registrado_por=self.usuario,
            estado='pendiente'
        )

        DetalleCompra.objects.create(
            orden_compra=orden,
            presentacion=self.presentacion,
            cantidad=24,
            precio_unitario=45000
        )

        DetalleCompra.objects.create(
            orden_compra=orden,
            presentacion=self.presentacion,
            cantidad=12,
            precio_unitario=45000
        )

        orden.calcular_total()

        self.assertEqual(orden.total, (24 + 12) * 45000)
        self.assertEqual(orden.detalles.count(), 2)

    # ✓ Flujo: Cambio de estados
    def test_flujo_estados_orden(self):
        """Verificar transiciones de estados correctas."""
        orden = OrdenCompra.objects.create(
            proveedor=self.proveedor,
            registrado_por=self.usuario
        )

        self.assertEqual(orden.estado, 'pendiente')

        orden.estado = 'confirmada'
        orden.save()
        self.assertEqual(orden.estado, 'confirmada')

        orden.estado = 'recibida'
        orden.save()
        self.assertEqual(orden.estado, 'recibida')
