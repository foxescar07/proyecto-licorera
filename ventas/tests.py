from django.test import TestCase
from django.core.exceptions import ValidationError
from .models import Cliente, Venta, DetalleVenta, Devolucion, DetalleDevolucion
from usuarios.models import Usuario
from productos.models import Categoria, Producto, PresentacionProducto
from inventario.models import Lote
from decimal import Decimal


class DevolucionModelTest(TestCase):
    """Tests para el modelo Devolucion."""

    def setUp(self):
        """Crear datos de prueba."""
        self.usuario = Usuario.objects.create_user(
            username='empleado',
            email='emp@test.com',
            password='pass123'
        )

        self.cliente = Cliente.objects.create(
            nombre="Juan García",
            tipo_id='CC',
            identificacion='12345678',
            email='juan@test.com'
        )

        self.venta = Venta.objects.create(
            cliente=self.cliente,
            vendedor=self.usuario,
            total_con_descuento=150000
        )

    # ✓ US-020: Crear devolución válida
    def test_crear_devolucion_valida(self):
        """Verificar que se crea una devolución con datos válidos."""
        devolucion = Devolucion.objects.create(
            venta=self.venta,
            registrado_por=self.usuario,
            motivo='defectuoso',
            tipo_reembolso='cambio',
            total_devuelto=50000
        )

        self.assertEqual(devolucion.venta, self.venta)
        self.assertEqual(devolucion.registrado_por, self.usuario)
        self.assertEqual(devolucion.motivo, 'defectuoso')
        self.assertEqual(devolucion.total_devuelto, 50000)

    # ✓ US-020: Devolución requiere venta
    def test_devolucion_requiere_venta(self):
        """Verificar que una devolución está vinculada a una venta."""
        devolucion = Devolucion.objects.create(
            venta=self.venta,
            registrado_por=self.usuario,
            total_devuelto=50000
        )

        self.assertIsNotNone(devolucion.venta)
        self.assertEqual(devolucion.venta.cliente.nombre, "Juan García")

    # ✓ US-020: No se puede eliminar venta con devoluciones
    def test_no_eliminar_venta_con_devoluciones(self):
        """Verificar que no se puede eliminar una venta que tiene devoluciones."""
        Devolucion.objects.create(
            venta=self.venta,
            registrado_por=self.usuario,
            total_devuelto=50000
        )

        with self.assertRaises(Exception):
            self.venta.delete()

    # ✓ Validación: Total devuelto no puede exceder total venta
    def test_total_devuelto_no_excede_venta(self):
        """Verificar que total devuelto no puede exceder total venta."""
        devolucion = Devolucion(
            venta=self.venta,
            registrado_por=self.usuario,
            total_devuelto=200000  # Mayor que total venta (150000)
        )

        with self.assertRaises(ValidationError):
            devolucion.full_clean()

    # ✓ Validación: Total devuelto no puede ser negativo
    def test_total_devuelto_no_negativo(self):
        """Verificar que total devuelto no puede ser negativo."""
        devolucion = Devolucion(
            venta=self.venta,
            registrado_por=self.usuario,
            total_devuelto=-10000
        )

        with self.assertRaises(ValidationError):
            devolucion.full_clean()

    # ✓ Validación: Motivos válidos
    def test_motivos_validos(self):
        """Verificar que solo acepta motivos predefinidos."""
        motivos = ['defectuoso', 'equivocado', 'insatisfecho', 'calidad', 'empaque', 'otro']

        for motivo in motivos:
            devolucion = Devolucion.objects.create(
                venta=self.venta,
                registrado_por=self.usuario,
                motivo=motivo,
                total_devuelto=10000
            )
            self.assertEqual(devolucion.motivo, motivo)

    # ✓ Validación: Tipos de reembolso válidos
    def test_tipos_reembolso_validos(self):
        """Verificar que solo acepta tipos de reembolso válidos."""
        tipos = ['cambio', 'nota_credito', 'reembolso']

        for tipo in tipos:
            devolucion = Devolucion.objects.create(
                venta=self.venta,
                registrado_por=self.usuario,
                tipo_reembolso=tipo,
                total_devuelto=10000
            )
            self.assertEqual(devolucion.tipo_reembolso, tipo)

    # ✓ Propiedad: Número de devolución formateado
    def test_numero_devolucion_formateado(self):
        """Verificar que el número se formatea correctamente."""
        devolucion = Devolucion.objects.create(
            venta=self.venta,
            registrado_por=self.usuario,
            total_devuelto=50000
        )

        esperado = f'DEV-{devolucion.pk:04d}'
        self.assertEqual(devolucion.numero, esperado)

    # ✓ Validación: Restaurar stock por defecto
    def test_restaurar_stock_por_defecto(self):
        """Verificar que por defecto restaura stock."""
        devolucion = Devolucion.objects.create(
            venta=self.venta,
            registrado_por=self.usuario,
            total_devuelto=50000
        )

        self.assertTrue(devolucion.restaurar_stock)

    # ✓ Validación: String representation
    def test_str_representation(self):
        """Verificar que __str__ muestra número y cliente."""
        devolucion = Devolucion.objects.create(
            venta=self.venta,
            registrado_por=self.usuario,
            total_devuelto=50000
        )

        esperado = f'DEV-{devolucion.pk:04d} | {self.cliente.nombre} — {devolucion.fecha:%d/%m/%Y %H:%M}'
        self.assertEqual(str(devolucion), esperado)


class DetalleDevolucionModelTest(TestCase):
    """Tests para el modelo DetalleDevolucion."""

    def setUp(self):
        """Crear datos de prueba."""
        self.usuario = Usuario.objects.create_user(username='emp', password='pass')

        self.cliente = Cliente.objects.create(
            nombre="Cliente Test",
            tipo_id='CC',
            identificacion='87654321'
        )

        self.venta = Venta.objects.create(
            cliente=self.cliente,
            vendedor=self.usuario,
            total_con_descuento=150000
        )

        self.devolucion = Devolucion.objects.create(
            venta=self.venta,
            registrado_por=self.usuario,
            total_devuelto=50000
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
            precio=50000
        )

    # ✓ US-021: Crear detalle de devolución
    def test_crear_detalle_devolucion(self):
        """Verificar que se crea un detalle de devolución."""
        detalle = DetalleDevolucion.objects.create(
            devolucion=self.devolucion,
            presentacion=self.presentacion,
            cantidad=1,
            precio_unitario=50000
        )

        self.assertEqual(detalle.devolucion, self.devolucion)
        self.assertEqual(detalle.presentacion, self.presentacion)
        self.assertEqual(detalle.cantidad, 1)
        self.assertEqual(detalle.subtotal(), 50000)

    # ✓ US-021: Detalle devuelto requiere presentación
    def test_detalle_requiere_presentacion(self):
        """Verificar que es obligatoria la presentación."""
        with self.assertRaises(Exception):
            DetalleDevolucion.objects.create(
                devolucion=self.devolucion,
                presentacion=None,
                cantidad=1,
                precio_unitario=50000
            )

    # ✓ Validación: Cantidad positiva
    def test_cantidad_debe_ser_positiva(self):
        """Verificar que cantidad debe ser > 0."""
        detalle = DetalleDevolucion(
            devolucion=self.devolucion,
            presentacion=self.presentacion,
            cantidad=0,
            precio_unitario=50000
        )

        with self.assertRaises(ValidationError):
            detalle.full_clean()

    # ✓ Validación: Precio positivo
    def test_precio_debe_ser_positivo(self):
        """Verificar que precio debe ser > 0."""
        detalle = DetalleDevolucion(
            devolucion=self.devolucion,
            presentacion=self.presentacion,
            cantidad=1,
            precio_unitario=-50000
        )

        with self.assertRaises(ValidationError):
            detalle.full_clean()

    # ✓ Calcular subtotal automático
    def test_subtotal_calculado_automaticamente(self):
        """Verificar que subtotal se calcula automáticamente."""
        detalle = DetalleDevolucion.objects.create(
            devolucion=self.devolucion,
            presentacion=self.presentacion,
            cantidad=3,
            precio_unitario=50000
        )

        self.assertEqual(detalle.subtotal(), 3 * 50000)
        self.assertEqual(detalle.subtotal(), 150000)

    # ✓ Validación: String representation
    def test_str_representation(self):
        """Verificar que __str__ muestra producto y cantidad."""
        detalle = DetalleDevolucion.objects.create(
            devolucion=self.devolucion,
            presentacion=self.presentacion,
            cantidad=2,
            precio_unitario=50000
        )

        esperado = f"{self.presentacion.producto.nombre} ({self.presentacion.nombre}) x2"
        self.assertEqual(str(detalle), esperado)

    # ✓ Con lote asociado
    def test_detalle_con_lote_asociado(self):
        """Verificar que se puede asociar un lote."""
        lote = Lote.objects.create(
            numero_lote="LOT-20260625-001",
            presentacion=self.presentacion,
            stock_actual=10,
            costo_unitario=Decimal('40000.00')
        )

        detalle = DetalleDevolucion.objects.create(
            devolucion=self.devolucion,
            presentacion=self.presentacion,
            lote=lote,
            cantidad=1,
            precio_unitario=50000
        )

        self.assertEqual(detalle.lote, lote)


class DevolucionIntegrationTest(TestCase):
    """Tests de integración para flujo de devoluciones."""

    def setUp(self):
        """Crear datos para tests."""
        self.usuario = Usuario.objects.create_user(username='emp', password='pass')

        self.cliente = Cliente.objects.create(
            nombre="Cliente Completo",
            tipo_id='CC',
            identificacion='11111111'
        )

        self.venta = Venta.objects.create(
            cliente=self.cliente,
            vendedor=self.usuario,
            total_con_descuento=200000
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
            precio=50000
        )

    # ✓ Flujo completo: Crear devolución → Agregar detalles
    def test_flujo_completo_devolucion(self):
        """Verificar flujo completo de una devolución."""
        devolucion = Devolucion.objects.create(
            venta=self.venta,
            registrado_por=self.usuario,
            motivo='defectuoso',
            tipo_reembolso='cambio',
            restaurar_stock=True,
            total_devuelto=100000
        )

        DetalleDevolucion.objects.create(
            devolucion=devolucion,
            presentacion=self.presentacion,
            cantidad=2,
            precio_unitario=50000
        )

        self.assertEqual(devolucion.detalles.count(), 1)
        self.assertEqual(devolucion.detalles.first().subtotal(), 100000)

    # ✓ Devolución con múltiples líneas
    def test_devolucion_multiples_detalles(self):
        """Verificar devolución con varios productos."""
        presentacion2 = PresentacionProducto.objects.create(
            producto=self.producto,
            nombre="1L",
            unidades=2,
            precio=80000
        )

        devolucion = Devolucion.objects.create(
            venta=self.venta,
            registrado_por=self.usuario,
            total_devuelto=180000
        )

        DetalleDevolucion.objects.create(
            devolucion=devolucion,
            presentacion=self.presentacion,
            cantidad=2,
            precio_unitario=50000
        )

        DetalleDevolucion.objects.create(
            devolucion=devolucion,
            presentacion=presentacion2,
            cantidad=1,
            precio_unitario=80000
        )

        self.assertEqual(devolucion.detalles.count(), 2)

        total_detalles = sum(d.subtotal() for d in devolucion.detalles.all())
        self.assertEqual(total_detalles, 180000)

    # ✓ Devolución parcial
    def test_devolucion_parcial(self):
        """Verificar que se puede hacer devolución parcial."""
        devolucion = Devolucion.objects.create(
            venta=self.venta,
            registrado_por=self.usuario,
            tipo_reembolso='reembolso',
            total_devuelto=50000  # Solo 1 de 4 botellas
        )

        DetalleDevolucion.objects.create(
            devolucion=devolucion,
            presentacion=self.presentacion,
            cantidad=1,
            precio_unitario=50000
        )

        self.assertLess(devolucion.total_devuelto, self.venta.total_venta)
        self.assertEqual(devolucion.detalles.count(), 1)
