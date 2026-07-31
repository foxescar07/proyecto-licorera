from django.test import TestCase
from django.core.exceptions import ValidationError
from .models import (
    Cliente, Venta, DetalleVenta,
    AperturaCaja, CierreCaja,
    Devolucion, DetalleDevolucion,
)
from usuarios.models import Usuario
from productos.models import Categoria, Producto, PresentacionProducto
from inventario.models import Lote
from decimal import Decimal


# ════════════════════════════════════════
# TESTS — CLIENTE
# ════════════════════════════════════════

class ClienteModelTest(TestCase):
    """Tests para el modelo Cliente (MER)."""

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username='cajero1',
            email='cajero@test.com',
            password='pass123',
        )

    # ✓ Cliente con todos los campos del MER
    def test_crear_cliente_completo(self):
        """Verifica que se crean todos los campos del MER."""
        cliente = Cliente.objects.create(
            documento_usuario=self.usuario,
            identificacion='12345678',
            nombre='Juan',
            apellido='García',
            telefono='3001234567',
            correo_personal='juan@test.com',
        )

        self.assertEqual(cliente.nombre, 'Juan')
        self.assertEqual(cliente.apellido, 'García')
        self.assertEqual(cliente.correo_personal, 'juan@test.com')
        self.assertEqual(cliente.documento_usuario, self.usuario)

    # ✓ Propiedad nombre_completo
    def test_nombre_completo(self):
        """Verifica que nombre_completo une nombre y apellido."""
        cliente = Cliente.objects.create(nombre='Ana', apellido='López')
        self.assertEqual(cliente.nombre_completo, 'Ana López')

    # ✓ Cliente sin apellido (campo opcional)
    def test_cliente_sin_apellido(self):
        """El apellido es opcional, campo blank."""
        cliente = Cliente.objects.create(nombre='Consumidor final')
        self.assertEqual(cliente.apellido, '')
        self.assertEqual(cliente.nombre_completo, 'Consumidor final')

    # ✓ Identificación única
    def test_identificacion_unica(self):
        """La identificación debe ser única."""
        Cliente.objects.create(nombre='A', identificacion='111')
        with self.assertRaises(Exception):
            Cliente.objects.create(nombre='B', identificacion='111')


# ════════════════════════════════════════
# TESTS — VENTA
# ════════════════════════════════════════

class VentaModelTest(TestCase):
    """Tests para el modelo Venta (MER)."""

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username='vendedor',
            email='vend@test.com',
            password='pass123',
        )
        self.cliente = Cliente.objects.create(
            nombre='María',
            apellido='Torres',
            identificacion='99887766',
        )

    # ✓ Crear venta con metodo_pago único (MER)
    def test_crear_venta_metodo_pago_unico(self):
        """Verifica la estructura del MER: un solo metodo_pago."""
        venta = Venta.objects.create(
            documento_usuario=self.usuario,
            codigo_cliente=self.cliente,
            total_venta=Decimal('100000'),
            metodo_pago='efectivo',
        )

        self.assertEqual(venta.metodo_pago, 'efectivo')
        self.assertEqual(venta.total_venta, Decimal('100000'))
        self.assertEqual(venta.codigo_cliente, self.cliente)
        self.assertEqual(venta.documento_usuario, self.usuario)

    # ✓ Métodos de pago válidos del MER
    def test_metodos_pago_validos(self):
        """Verifica todos los métodos de pago definidos."""
        metodos = ['efectivo', 'tarjeta', 'transferencia', 'nequi', 'daviplata', 'mixto']
        for metodo in metodos:
            venta = Venta.objects.create(
                documento_usuario=self.usuario,
                codigo_cliente=self.cliente,
                total_venta=Decimal('50000'),
                metodo_pago=metodo,
            )
            self.assertEqual(venta.metodo_pago, metodo)

    # ✓ String representation
    def test_str_venta(self):
        """Verifica __str__ de la venta."""
        venta = Venta.objects.create(
            codigo_cliente=self.cliente,
            total_venta=Decimal('80000'),
            metodo_pago='tarjeta',
        )
        self.assertIn('María', str(venta))

    # ✓ FK codigo_cliente (MER)
    def test_venta_requiere_codigo_cliente(self):
        """Venta no puede crearse sin codigo_cliente."""
        with self.assertRaises(Exception):
            Venta.objects.create(
                codigo_cliente=None,
                total_venta=Decimal('10000'),
                metodo_pago='efectivo',
            )


# ════════════════════════════════════════
# TESTS — DETALLE VENTA
# ════════════════════════════════════════

class DetalleVentaModelTest(TestCase):
    """Tests para el modelo DetalleVenta (MER)."""

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username='emp_det',
            password='pass',
        )
        self.cliente = Cliente.objects.create(nombre='Cliente DV')
        self.venta   = Venta.objects.create(
            codigo_cliente=self.cliente,
            total_venta=Decimal('200000'),
            metodo_pago='efectivo',
        )

        self.categoria    = Categoria.objects.create(codigo='RON', nombre='Ron')
        self.producto     = Producto.objects.create(
            codigo='BACARDI',
            nombre='Bacardi',
            categoria=self.categoria,
        )
        self.presentacion = PresentacionProducto.objects.create(
            producto=self.producto,
            nombre='750ml',
            unidades=1,
            precio=Decimal('50000'),
        )

    # ✓ Crear detalle con campos del MER
    def test_crear_detalle_venta_mer(self):
        """Verifica campos del MER: subtotal, valor_descuento, total."""
        detalle = DetalleVenta.objects.create(
            codigo_venta=self.venta,
            codigo_producto=self.producto,
            codigo_presentacion=self.presentacion,
            cantidad=2,
            precio_unitario=Decimal('50000'),
            valor_descuento=Decimal('5000'),
        )

        # subtotal = precio * cantidad
        self.assertEqual(detalle.subtotal, Decimal('100000'))
        # total = subtotal - descuento
        self.assertEqual(detalle.total, Decimal('95000'))
        self.assertEqual(detalle.valor_descuento, Decimal('5000'))

    # ✓ Subtotal y total se calculan automáticamente al guardar
    def test_subtotal_total_auto(self):
        """Subtotal y total se calculan en save()."""
        detalle = DetalleVenta.objects.create(
            codigo_venta=self.venta,
            codigo_presentacion=self.presentacion,
            cantidad=3,
            precio_unitario=Decimal('40000'),
        )
        self.assertEqual(detalle.subtotal, Decimal('120000'))
        self.assertEqual(detalle.total, Decimal('120000'))  # sin descuento

    # ✓ FK codigo_venta (MER)
    def test_fk_codigo_venta(self):
        """Detalle tiene FK codigo_venta correctamente."""
        detalle = DetalleVenta.objects.create(
            codigo_venta=self.venta,
            codigo_presentacion=self.presentacion,
            cantidad=1,
            precio_unitario=Decimal('50000'),
        )
        self.assertEqual(detalle.codigo_venta, self.venta)

    # ✓ FK codigo_producto y codigo_presentacion (MER)
    def test_fk_codigo_producto_presentacion(self):
        """Detalle tiene FK codigo_producto y codigo_presentacion."""
        detalle = DetalleVenta.objects.create(
            codigo_venta=self.venta,
            codigo_producto=self.producto,
            codigo_presentacion=self.presentacion,
            cantidad=1,
            precio_unitario=Decimal('50000'),
        )
        self.assertEqual(detalle.codigo_producto, self.producto)
        self.assertEqual(detalle.codigo_presentacion, self.presentacion)

    # ✓ FK codigo_lote (MER) — opcional
    def test_fk_codigo_lote_opcional(self):
        """codigo_lote es opcional en el detalle."""
        lote = Lote.objects.create(
            numero_lote='LOT-001',
            presentacion=self.presentacion,
            stock_actual=10,
            costo_unitario=Decimal('40000'),
            registrado_por=self.usuario,
        )
        detalle = DetalleVenta.objects.create(
            codigo_venta=self.venta,
            codigo_presentacion=self.presentacion,
            codigo_lote=lote,
            cantidad=2,
            precio_unitario=Decimal('50000'),
        )
        self.assertEqual(detalle.codigo_lote, lote)

    # ✓ String representation
    def test_str_detalle_venta(self):
        """Verifica __str__ del detalle."""
        detalle = DetalleVenta.objects.create(
            codigo_venta=self.venta,
            codigo_producto=self.producto,
            codigo_presentacion=self.presentacion,
            cantidad=2,
            precio_unitario=Decimal('50000'),
        )
        self.assertIn('Bacardi', str(detalle))
        self.assertIn('x2', str(detalle))


# ════════════════════════════════════════
# TESTS — DEVOLUCIÓN
# ════════════════════════════════════════

class DevolucionModelTest(TestCase):
    """Tests para el modelo Devolucion (MER)."""

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username='empleado',
            email='emp@test.com',
            password='pass123',
        )
        self.cliente = Cliente.objects.create(
            nombre='Juan',
            apellido='García',
            identificacion='12345678',
            correo_personal='juan@test.com',
        )
        self.venta = Venta.objects.create(
            codigo_cliente=self.cliente,
            documento_usuario=self.usuario,
            total_venta=Decimal('150000'),
            metodo_pago='efectivo',
        )

    # ✓ US-020: Crear devolución válida con campos del MER
    def test_crear_devolucion_valida_mer(self):
        """Verifica que se crea la devolución con los campos del MER."""
        devolucion = Devolucion.objects.create(
            codigo_venta=self.venta,
            documento_usuario=self.usuario,
            motivo='defectuoso',
            tipo_devolucion='cambio',
            total_devuelto=Decimal('50000'),
            presenta_comprobante=True,
            estado='pendiente',
        )

        self.assertEqual(devolucion.codigo_venta, self.venta)
        self.assertEqual(devolucion.documento_usuario, self.usuario)
        self.assertEqual(devolucion.motivo, 'defectuoso')
        self.assertEqual(devolucion.tipo_devolucion, 'cambio')
        self.assertTrue(devolucion.presenta_comprobante)

    # ✓ FK codigo_detalle_venta (MER)
    def test_fk_codigo_detalle_venta(self):
        """Verifica que codigo_detalle_venta apunta a un DetalleVenta."""
        categoria    = Categoria.objects.create(codigo='VIN', nombre='Vino')
        producto     = Producto.objects.create(codigo='MERLOT', nombre='Merlot', categoria=categoria)
        presentacion = PresentacionProducto.objects.create(
            producto=producto, nombre='750ml', unidades=1, precio=Decimal('45000')
        )
        detalle = DetalleVenta.objects.create(
            codigo_venta=self.venta,
            codigo_presentacion=presentacion,
            cantidad=1,
            precio_unitario=Decimal('45000'),
        )

        devolucion = Devolucion.objects.create(
            codigo_venta=self.venta,
            codigo_detalle_venta=detalle,
            documento_usuario=self.usuario,
            total_devuelto=Decimal('45000'),
            tipo_devolucion='reembolso',
        )

        self.assertEqual(devolucion.codigo_detalle_venta, detalle)

    # ✓ tipo_devolucion válidos (MER)
    def test_tipos_devolucion_validos(self):
        """Verifica que solo acepta tipos de devolución del MER."""
        tipos = ['cambio', 'nota_credito', 'reembolso']
        for tipo in tipos:
            devolucion = Devolucion.objects.create(
                codigo_venta=self.venta,
                documento_usuario=self.usuario,
                tipo_devolucion=tipo,
                total_devuelto=Decimal('10000'),
            )
            self.assertEqual(devolucion.tipo_devolucion, tipo)

    # ✓ presenta_comprobante (MER — antes tiene_comprobante)
    def test_presenta_comprobante(self):
        """Verifica campo presenta_comprobante (nombre del MER)."""
        dev_con    = Devolucion.objects.create(
            codigo_venta=self.venta, total_devuelto=Decimal('5000'),
            presenta_comprobante=True,
        )
        dev_sin    = Devolucion.objects.create(
            codigo_venta=self.venta, total_devuelto=Decimal('5000'),
            presenta_comprobante=False,
        )
        self.assertTrue(dev_con.presenta_comprobante)
        self.assertFalse(dev_sin.presenta_comprobante)

    # ✓ documento_usuario (MER — antes registrado_por)
    def test_documento_usuario_en_devolucion(self):
        """Verifica campo documento_usuario en Devolucion."""
        devolucion = Devolucion.objects.create(
            codigo_venta=self.venta,
            documento_usuario=self.usuario,
            total_devuelto=Decimal('20000'),
        )
        self.assertEqual(devolucion.documento_usuario, self.usuario)

    # ✓ US-020: No se puede eliminar venta con devoluciones
    def test_no_eliminar_venta_con_devoluciones(self):
        """Verificar que no se puede eliminar una venta que tiene devoluciones."""
        Devolucion.objects.create(
            codigo_venta=self.venta,
            documento_usuario=self.usuario,
            total_devuelto=Decimal('50000'),
        )
        with self.assertRaises(Exception):
            self.venta.delete()

    # ✓ Validación: Total devuelto no puede exceder total venta
    def test_total_devuelto_no_excede_venta(self):
        """Verificar que total devuelto no puede exceder total venta."""
        devolucion = Devolucion(
            codigo_venta=self.venta,
            documento_usuario=self.usuario,
            total_devuelto=Decimal('200000'),  # Mayor que 150000
        )
        with self.assertRaises(ValidationError):
            devolucion.full_clean()

    # ✓ Validación: Total devuelto no puede ser negativo
    def test_total_devuelto_no_negativo(self):
        """Verificar que total devuelto no puede ser negativo."""
        devolucion = Devolucion(
            codigo_venta=self.venta,
            documento_usuario=self.usuario,
            total_devuelto=Decimal('-10000'),
        )
        with self.assertRaises(ValidationError):
            devolucion.full_clean()

    # ✓ Motivos válidos
    def test_motivos_validos(self):
        """Verificar que solo acepta motivos predefinidos."""
        motivos = ['defectuoso', 'equivocado', 'insatisfecho', 'calidad', 'empaque', 'otro']
        for motivo in motivos:
            devolucion = Devolucion.objects.create(
                codigo_venta=self.venta,
                documento_usuario=self.usuario,
                motivo=motivo,
                total_devuelto=Decimal('10000'),
            )
            self.assertEqual(devolucion.motivo, motivo)

    # ✓ Propiedad: Número de devolución formato (DEV-XXXX)
    def test_numero_devolucion_formateado(self):
        """Verificar que el número se formatea correctamente."""
        devolucion = Devolucion.objects.create(
            codigo_venta=self.venta,
            documento_usuario=self.usuario,
            total_devuelto=Decimal('50000'),
        )
        esperado = f'DEV-{devolucion.pk:04d}'
        self.assertEqual(devolucion.numero, esperado)

    # ✓ Estado inicial por defecto
    def test_estado_inicial_pendiente(self):
        """Verificar que el estado inicial por defecto es 'pendiente'."""
        devolucion = Devolucion.objects.create(
            codigo_venta=self.venta,
            documento_usuario=self.usuario,
        )
        self.assertEqual(devolucion.estado, 'pendiente')

    # ✓ String representation
    def test_str_representation(self):
        """Verificar que __str__ muestra número y cliente."""
        devolucion = Devolucion.objects.create(
            codigo_venta=self.venta,
            documento_usuario=self.usuario,
            total_devuelto=Decimal('50000'),
        )
        esperado = f'DEV-{devolucion.pk:04d} | {self.cliente.nombre} — {devolucion.fecha:%d/%m/%Y %H:%M}'
        self.assertEqual(str(devolucion), esperado)

    # ✓ cantidad_cambio (MER)
    def test_cantidad_cambio(self):
        """Verifica campo cantidad_cambio del MER."""
        devolucion = Devolucion.objects.create(
            codigo_venta=self.venta,
            tipo_devolucion='cambio',
            cantidad_cambio=2,
            total_devuelto=Decimal('30000'),
        )
        self.assertEqual(devolucion.cantidad_cambio, 2)

    # ✓ metodo_pago_devolucion (MER)
    def test_metodo_pago_devolucion(self):
        """Verifica campo metodo_pago_devolucion del MER."""
        devolucion = Devolucion.objects.create(
            codigo_venta=self.venta,
            tipo_devolucion='reembolso',
            metodo_pago_devolucion='nequi',
            total_devuelto=Decimal('30000'),
        )
        self.assertEqual(devolucion.metodo_pago_devolucion, 'nequi')


# ════════════════════════════════════════
# TESTS — DETALLE DEVOLUCIÓN
# ════════════════════════════════════════

class DetalleDevolucionModelTest(TestCase):
    """Tests para el modelo DetalleDevolucion."""

    def setUp(self):
        self.usuario = Usuario.objects.create_user(username='emp', password='pass')
        self.cliente = Cliente.objects.create(nombre='Cliente Test', identificacion='87654321')
        self.venta   = Venta.objects.create(
            codigo_cliente=self.cliente,
            total_venta=Decimal('150000'),
            metodo_pago='efectivo',
        )
        self.devolucion = Devolucion.objects.create(
            codigo_venta=self.venta,
            documento_usuario=self.usuario,
            total_devuelto=Decimal('0'),
        )
        self.categoria    = Categoria.objects.create(codigo='RON', nombre='Ron')
        self.producto     = Producto.objects.create(codigo='BACARDI', nombre='Bacardi', categoria=self.categoria)
        self.presentacion = PresentacionProducto.objects.create(
            producto=self.producto, nombre='750ml', unidades=1, precio=Decimal('50000')
        )

    # ✓ US-021: Crear detalle de devolución
    def test_crear_detalle_devolucion(self):
        """Verificar que se crea un detalle de devolución."""
        detalle = DetalleDevolucion.objects.create(
            devolucion=self.devolucion,
            presentacion=self.presentacion,
            cantidad=1,
            precio_unitario=Decimal('50000'),
        )
        self.assertEqual(detalle.devolucion, self.devolucion)
        self.assertEqual(detalle.presentacion, self.presentacion)
        self.assertEqual(detalle.cantidad, 1)
        self.assertEqual(detalle.subtotal, Decimal('50000'))

    # ✓ Subtotal calculado como propiedad
    def test_subtotal_calculado(self):
        """Verificar que subtotal se calcula como propiedad."""
        detalle = DetalleDevolucion.objects.create(
            devolucion=self.devolucion,
            presentacion=self.presentacion,
            cantidad=3,
            precio_unitario=Decimal('50000'),
        )
        self.assertEqual(detalle.subtotal, Decimal('150000'))

    # ✓ Validación: Cantidad positiva
    def test_cantidad_debe_ser_positiva(self):
        """Verificar que cantidad debe ser > 0."""
        detalle = DetalleDevolucion(
            devolucion=self.devolucion,
            presentacion=self.presentacion,
            cantidad=-5,
            precio_unitario=Decimal('50000'),
        )
        with self.assertRaises(ValidationError):
            detalle.full_clean()

    # ✓ Cantidad mínima es 1
    def test_cantidad_minima_es_uno(self):
        """Verificar que la cantidad mínima es 1."""
        detalle = DetalleDevolucion(
            devolucion=self.devolucion,
            presentacion=self.presentacion,
            cantidad=0,
            precio_unitario=Decimal('50000'),
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
            precio_unitario=Decimal('-50000'),
        )
        with self.assertRaises(ValidationError):
            detalle.full_clean()

    # ✓ String representation
    def test_str_representation(self):
        """Verificar que __str__ muestra producto y cantidad."""
        detalle = DetalleDevolucion.objects.create(
            devolucion=self.devolucion,
            presentacion=self.presentacion,
            cantidad=2,
            precio_unitario=Decimal('50000'),
        )
        esperado = f"{self.presentacion.producto.nombre} ({self.presentacion.nombre}) x2"
        self.assertEqual(str(detalle), esperado)

    # ✓ codigo_lote asociado (MER)
    def test_detalle_con_codigo_lote(self):
        """Verificar que se puede asociar un lote (codigo_lote en MER)."""
        lote = Lote.objects.create(
            numero_lote='LOT-20260625-001',
            presentacion=self.presentacion,
            stock_actual=10,
            costo_unitario=Decimal('40000'),
            registrado_por=self.usuario,
        )
        detalle = DetalleDevolucion.objects.create(
            devolucion=self.devolucion,
            presentacion=self.presentacion,
            codigo_lote=lote,
            cantidad=1,
            precio_unitario=Decimal('50000'),
        )
        self.assertEqual(detalle.codigo_lote, lote)


# ════════════════════════════════════════
# TESTS DE INTEGRACIÓN
# ════════════════════════════════════════

class DevolucionIntegrationTest(TestCase):
    """Tests de integración para flujo de devoluciones."""

    def setUp(self):
        self.usuario = Usuario.objects.create_user(username='emp_int', password='pass')
        self.cliente = Cliente.objects.create(
            nombre='Cliente Completo',
            apellido='Pérez',
            identificacion='11111111',
        )
        self.venta = Venta.objects.create(
            codigo_cliente=self.cliente,
            documento_usuario=self.usuario,
            total_venta=Decimal('200000'),
            metodo_pago='nequi',
        )
        self.categoria    = Categoria.objects.create(codigo='RON', nombre='Ron')
        self.producto     = Producto.objects.create(codigo='BACARDI', nombre='Bacardi', categoria=self.categoria)
        self.presentacion = PresentacionProducto.objects.create(
            producto=self.producto, nombre='750ml', unidades=1, precio=Decimal('50000')
        )

    # ✓ Flujo completo con recálculo de total desde detalles
    def test_flujo_completo_calculo_total(self):
        """Verifica que la devolución calcula el total desde sus detalles."""
        devolucion = Devolucion.objects.create(
            codigo_venta=self.venta,
            documento_usuario=self.usuario,
            motivo='defectuoso',
            total_devuelto=Decimal('0'),
        )

        DetalleDevolucion.objects.create(
            devolucion=devolucion,
            presentacion=self.presentacion,
            cantidad=2,
            precio_unitario=Decimal('50000'),
        )

        devolucion.calcular_total()
        self.assertEqual(devolucion.total_devuelto, Decimal('100000'))
        self.assertEqual(devolucion.detalles.count(), 1)

    # ✓ Devolución con múltiples líneas
    def test_devolucion_multiples_detalles(self):
        """Verifica devolución con varios productos."""
        presentacion2 = PresentacionProducto.objects.create(
            producto=self.producto, nombre='1L', unidades=2, precio=Decimal('80000')
        )
        devolucion = Devolucion.objects.create(
            codigo_venta=self.venta,
            documento_usuario=self.usuario,
            total_devuelto=Decimal('180000'),
        )
        DetalleDevolucion.objects.create(
            devolucion=devolucion, presentacion=self.presentacion,
            cantidad=2, precio_unitario=Decimal('50000'),
        )
        DetalleDevolucion.objects.create(
            devolucion=devolucion, presentacion=presentacion2,
            cantidad=1, precio_unitario=Decimal('80000'),
        )

        self.assertEqual(devolucion.detalles.count(), 2)
        total_detalles = sum(d.subtotal for d in devolucion.detalles.all())
        self.assertEqual(total_detalles, Decimal('180000'))

    # ✓ Ciclo de vida y transiciones de estado
    def test_flujo_estados_devolucion(self):
        """Verifica transiciones lógicas de estado."""
        devolucion = Devolucion.objects.create(
            codigo_venta=self.venta,
            documento_usuario=self.usuario,
        )
        self.assertEqual(devolucion.estado, 'pendiente')

        devolucion.estado = 'aprobada'
        devolucion.save()
        self.assertEqual(devolucion.estado, 'aprobada')

        devolucion.estado = 'aplicada'
        devolucion.save()
        self.assertEqual(devolucion.estado, 'aplicada')

    # ✓ Devolución parcial
    def test_devolucion_parcial(self):
        """Verifica que se puede hacer devolución parcial."""
        devolucion = Devolucion.objects.create(
            codigo_venta=self.venta,
            documento_usuario=self.usuario,
            tipo_devolucion='reembolso',
            total_devuelto=Decimal('50000'),
        )
        DetalleDevolucion.objects.create(
            devolucion=devolucion,
            presentacion=self.presentacion,
            cantidad=1,
            precio_unitario=Decimal('50000'),
        )

        self.assertLess(devolucion.total_devuelto, self.venta.total_venta)
        self.assertEqual(devolucion.detalles.count(), 1)

    # ✓ Venta con metodo_pago y datos de cliente completos
    def test_venta_datos_mer_completos(self):
        """Verifica que Venta almacena todos los datos del MER correctamente."""
        self.assertEqual(self.venta.codigo_cliente.nombre, 'Cliente Completo')
        self.assertEqual(self.venta.codigo_cliente.apellido, 'Pérez')
        self.assertEqual(self.venta.metodo_pago, 'nequi')
        self.assertEqual(self.venta.documento_usuario, self.usuario)
        self.assertEqual(self.venta.total_venta, Decimal('200000'))

    # ✓ DetalleVenta con subtotal, valor_descuento y total del MER
    def test_detalle_venta_campos_mer(self):
        """Verifica campos subtotal, valor_descuento y total del MER en detalle."""
        detalle = DetalleVenta.objects.create(
            codigo_venta=self.venta,
            codigo_producto=self.producto,
            codigo_presentacion=self.presentacion,
            cantidad=2,
            precio_unitario=Decimal('50000'),
            valor_descuento=Decimal('10000'),
        )
        # subtotal = 2 * 50000 = 100000
        self.assertEqual(detalle.subtotal, Decimal('100000'))
        # total = 100000 - 10000 = 90000
        self.assertEqual(detalle.total, Decimal('90000'))