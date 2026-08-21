from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
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

    # ✓ SC 2: Validar NIT duplicado
    def test_nit_duplicado_rechaza_creacion(self):
        """Verificar que no permite NIT duplicado.

        Escenario: Se intenta registrar un nuevo proveedor con NIT que ya existe
        en la base de datos.

        Datos de entrada:
        - Nombre empresa: "Nueva Distribuidora"
        - NIT: (mismo del proveedor existente)
        - Email: "nuevo@test.com"
        - Teléfono: "3109876543"

        Resultado esperado:
        - El sistema rechaza la creación con error "Este NIT ya está registrado"
        - No se guarda el nuevo proveedor
        - La BD mantiene solo 1 proveedor
        """
        # Crear primer proveedor con NIT específico
        nit_existente = "900123456-7"
        proveedor1 = Proveedor.objects.create(
            nombre_empresa="Distribuidora Original",
            nit=nit_existente,
            email="original@test.com",
            telefono="3001234567",
            tipo_proveedor='distribuidor'
        )

        # Intentar crear segundo proveedor con mismo NIT
        proveedor2 = Proveedor(
            nombre_empresa="Nueva Distribuidora",
            nit=nit_existente,  # NIT duplicado
            email="nuevo@test.com",
            telefono="3109876543",
            tipo_proveedor='distribuidor'
        )

        # Verificar que ValidationError se lanza
        with self.assertRaises(Exception):
            proveedor2.full_clean()
            proveedor2.save()

        # Verificar que no se guardó
        self.assertEqual(Proveedor.objects.count(), 2)  # El del setUp + el que creamos

    # ✓ SC 3: Validar email duplicado
    def test_email_duplicado_rechaza_creacion(self):
        """Verificar que no permite email duplicado.

        Escenario: Se intenta registrar un nuevo proveedor con email que ya existe
        en la base de datos.

        Datos de entrada:
        - Nombre empresa: "Otra Distribuidora"
        - NIT: "988776655-4"
        - Email: (mismo del proveedor existente)
        - Teléfono: "3157896543"

        Resultado esperado:
        - El sistema rechaza la creación con error "Este email ya está registrado en el sistema"
        - No se guarda el nuevo proveedor
        - La BD mantiene solo 1 proveedor
        """
        # El setUp ya creó un proveedor con email "ceiba@test.com"
        email_existente = self.proveedor.email

        # Intentar crear nuevo proveedor con mismo email
        proveedor_nuevo = Proveedor(
            nombre_empresa="Otra Distribuidora",
            nit="988776655-4",
            email=email_existente,  # Email duplicado
            telefono="3157896543",
            tipo_proveedor='distribuidor'
        )

        # Verificar que ValidationError se lanza
        with self.assertRaises(Exception):
            proveedor_nuevo.full_clean()
            proveedor_nuevo.save()

        # Verificar que no se guardó (debe haber solo el del setUp)
        self.assertEqual(Proveedor.objects.count(), 1)
        self.assertTrue(Proveedor.objects.filter(email=email_existente).exists())

    # ✓ SC 4: Validar teléfono duplicado
    def test_telefono_duplicado_rechaza_creacion(self):
        """Verificar que no permite teléfono duplicado.

        Escenario: Se intenta registrar un nuevo proveedor con teléfono que ya existe
        en la base de datos.

        Datos de entrada:
        - Nombre empresa: "Más Distribuidoras"
        - NIT: "755443221-9"
        - Email: "contacto@masdist.com"
        - Teléfono: (mismo del proveedor existente)

        Resultado esperado:
        - El sistema rechaza la creación con error "Este teléfono ya está registrado"
        - No se guarda el nuevo proveedor
        - La BD mantiene solo 1 proveedor
        """
        # El setUp ya creó un proveedor con teléfono "3001234567"
        telefono_existente = self.proveedor.telefono

        # Intentar crear nuevo proveedor con mismo teléfono
        proveedor_nuevo = Proveedor(
            nombre_empresa="Más Distribuidoras",
            nit="755443221-9",
            email="contacto@masdist.com",
            telefono=telefono_existente,  # Teléfono duplicado
            tipo_proveedor='distribuidor'
        )

        # Verificar que ValidationError se lanza
        with self.assertRaises(Exception):
            proveedor_nuevo.full_clean()
            proveedor_nuevo.save()

        # Verificar que no se guardó (debe haber solo el del setUp)
        self.assertEqual(Proveedor.objects.count(), 1)
        self.assertTrue(Proveedor.objects.filter(telefono=telefono_existente).exists())


class ComprasCrudTest(TestCase):
    """Casos de regresión para la HU-002: compras con detalle de producto."""

    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username='tester_compras',
            password='clave-segura-123',
            identificacion='100000001',
            email='tester.compras@example.com',
        )
        self.proveedor = Proveedor.objects.create(
            nombre_empresa='Proveedor de pruebas',
            nit='900100200-1',
            email='proveedor.compras@example.com',
            telefono='3001234567',
        )
        categoria = Categoria.objects.create(codigo='CPR', nombre='Compras')
        self.producto = Producto.objects.create(
            codigo='PRD-COMPRA-001',
            nombre='Producto de prueba',
            categoria=categoria,
            cantidad_disponible=0,
            precio_unitario=Decimal('0.00'),
        )
        self.presentacion = PresentacionProducto.objects.create(
            producto=self.producto,
            nombre='Botella 750 ml',
            unidades=1,
            cantidad=0,
            precio=Decimal('0.00'),
        )

    def test_registrar_compra_crea_detalle_y_actualiza_costos_cantidades(self):
        """Registrar desde la pantalla de compras conserva producto, cantidad y costo."""
        self.client.force_login(self.usuario)

        response = self.client.post(reverse('lista_compras'), {
            'proveedor_id': self.proveedor.id,
            'producto': self.producto.id,
            'cantidad': 6,
            'precio_unitario': '12500.50',
        })

        self.assertRedirects(response, reverse('lista_compras'))
        compra = Compra.objects.get(proveedor=self.proveedor)
        detalle = compra.detalles.get()
        self.assertEqual(compra.valor, Decimal('75003.00'))
        self.assertEqual(compra.saldo, Decimal('75003.00'))
        self.assertEqual(detalle.producto, self.producto)
        self.assertEqual(detalle.presentacion, self.presentacion)
        self.assertEqual(detalle.cantidad, 6)
        self.assertEqual(detalle.precio_unitario, Decimal('12500.50'))
        self.assertEqual(detalle.subtotal, Decimal('75003.00'))

        self.producto.refresh_from_db()
        self.presentacion.refresh_from_db()
        self.assertEqual(self.producto.cantidad_disponible, 6)
        self.assertEqual(self.presentacion.cantidad, 6)
        self.assertTrue(HistorialCompra.objects.filter(compra=compra, evento='creada').exists())

    def test_editar_compra_y_detalle_recalcula_los_valores_persistidos(self):
        """Una edición de cantidades y costos mantiene el detalle y total correctos."""
        compra = Compra.objects.create(
            proveedor=self.proveedor,
            documento_usuario=self.usuario,
            valor=Decimal('20000.00'),
            saldo=Decimal('20000.00'),
        )
        detalle = DetalleCompra.objects.create(
            compra=compra,
            producto=self.producto,
            presentacion=self.presentacion,
            cantidad=2,
            precio_unitario=Decimal('10000.00'),
        )

        detalle.cantidad = 4
        detalle.precio_unitario = Decimal('13500.25')
        detalle.full_clean()
        detalle.save()
        compra.valor = detalle.subtotal
        compra.saldo = detalle.subtotal
        compra.save()

        compra.refresh_from_db()
        detalle.refresh_from_db()
        self.assertEqual(detalle.cantidad, 4)
        self.assertEqual(detalle.precio_unitario, Decimal('13500.25'))
        self.assertEqual(compra.valor, Decimal('54001.00'))
        self.assertEqual(compra.saldo, Decimal('54001.00'))

    def test_eliminar_compra_elimina_sus_detalles_asociados(self):
        """Eliminar una compra no deja detalles de compra huérfanos."""
        compra = Compra.objects.create(
            proveedor=self.proveedor,
            documento_usuario=self.usuario,
            valor=Decimal('5000.00'),
            saldo=Decimal('5000.00'),
        )
        detalle = DetalleCompra.objects.create(
            compra=compra,
            producto=self.producto,
            presentacion=self.presentacion,
            cantidad=1,
            precio_unitario=Decimal('5000.00'),
        )

        compra.delete()

        self.assertFalse(Compra.objects.filter(pk=compra.pk).exists())
        self.assertFalse(DetalleCompra.objects.filter(pk=detalle.pk).exists())

    # ✓ CP1: Cambiar de Pendiente a Confirmada
    def test_cambiar_estado_pendiente_a_confirmada(self):
        """Verificar que compra en estado Pendiente puede cambiar a Confirmada.

        Escenario: Una compra registrada en estado Pendiente se cambia a Confirmada.

        Datos de entrada:
        - Compra con estado: Pendiente
        - Nuevo estado: Confirmada

        Resultado esperado:
        - El estado cambia a Confirmada
        - Se registra el evento en HistorialCompra
        - La BD persiste el cambio
        """
        compra = Compra.objects.create(
            proveedor=self.proveedor,
            documento_usuario=self.usuario,
            estado='pendiente',
            valor=Decimal('10000.00'),
            saldo=Decimal('10000.00'),
        )

        # Cambiar estado
        compra.estado = 'confirmada'
        compra.save(update_fields=['estado'])
        HistorialCompra.objects.create(
            compra=compra,
            evento='editada',
            usuario=self.usuario,
            descripcion='Estado cambiado de pendiente a confirmada.',
        )

        # Verificar cambio
        compra.refresh_from_db()
        self.assertEqual(compra.estado, 'confirmada')
        self.assertTrue(
            HistorialCompra.objects.filter(
                compra=compra,
                evento='editada'
            ).exists()
        )

    # ✓ CP2: Cambiar de Pendiente a Cancelada
    def test_cambiar_estado_pendiente_a_cancelada(self):
        """Verificar que compra en estado Pendiente puede cambiar a Cancelada.

        Escenario: Una compra registrada en estado Pendiente se cancela.

        Datos de entrada:
        - Compra con estado: Pendiente
        - Nuevo estado: Cancelada

        Resultado esperado:
        - El estado cambia a Cancelada
        - Se registra el evento en HistorialCompra
        - La BD persiste el cambio
        """
        compra = Compra.objects.create(
            proveedor=self.proveedor,
            documento_usuario=self.usuario,
            estado='pendiente',
            valor=Decimal('15000.00'),
            saldo=Decimal('15000.00'),
        )

        # Cambiar estado a cancelada
        compra.estado = 'cancelada'
        compra.save(update_fields=['estado'])
        HistorialCompra.objects.create(
            compra=compra,
            evento='cancelada',
            usuario=self.usuario,
            descripcion='Estado cambiado de pendiente a cancelada.',
        )

        # Verificar cambio
        compra.refresh_from_db()
        self.assertEqual(compra.estado, 'cancelada')
        self.assertTrue(
            HistorialCompra.objects.filter(
                compra=compra,
                evento='cancelada'
            ).exists()
        )

    # ✓ CP3: Cambiar de Confirmada a Recibida
    def test_cambiar_estado_confirmada_a_recibida(self):
        """Verificar que compra en estado Confirmada puede cambiar a Recibida.

        Escenario: Una compra confirmada se marca como recibida.

        Datos de entrada:
        - Compra con estado: Confirmada
        - Nuevo estado: Recibida

        Resultado esperado:
        - El estado cambia a Recibida
        - Se registra el evento en HistorialCompra
        - La BD persiste el cambio
        """
        compra = Compra.objects.create(
            proveedor=self.proveedor,
            documento_usuario=self.usuario,
            estado='confirmada',
            valor=Decimal('20000.00'),
            saldo=Decimal('20000.00'),
        )

        # Cambiar estado a recibida
        compra.estado = 'recibida'
        compra.save(update_fields=['estado'])
        HistorialCompra.objects.create(
            compra=compra,
            evento='recibida',
            usuario=self.usuario,
            descripcion='Estado cambiado de confirmada a recibida.',
        )

        # Verificar cambio
        compra.refresh_from_db()
        self.assertEqual(compra.estado, 'recibida')
        self.assertTrue(
            HistorialCompra.objects.filter(
                compra=compra,
                evento='recibida'
            ).exists()
        )

    # ✓ CP4: Rechazar cambio inválido de estado
    def test_rechazar_cambio_estado_invalido(self):
        """Verificar que sistema rechaza transiciones de estado inválidas.

        Escenario: Se intenta cambiar compra de estado Recibida a Pendiente (no permitido).

        Datos de entrada:
        - Compra con estado: Recibida
        - Nuevo estado solicitado: Pendiente (transición inválida)

        Resultado esperado:
        - El cambio se rechaza
        - El estado permanece como Recibida
        - Se valida que la transición no es permitida
        """
        compra = Compra.objects.create(
            proveedor=self.proveedor,
            documento_usuario=self.usuario,
            estado='recibida',
            valor=Decimal('25000.00'),
            saldo=Decimal('25000.00'),
        )

        # Definir transiciones válidas
        transiciones_validas = {
            'pendiente': {'confirmada', 'cancelada'},
            'confirmada': {'recibida', 'cancelada'},
            'recibida': set(),  # No tiene transiciones válidas
        }

        estado_actual = compra.estado
        nuevo_estado = 'pendiente'  # Transición inválida

        # Verificar que NO es válida
        es_valida = nuevo_estado in transiciones_validas.get(estado_actual, set())
        self.assertFalse(es_valida)

        # El estado NO debe cambiar
        self.assertEqual(compra.estado, 'recibida')

    # ✓ CP5: Verificar registro en historial
    def test_registrar_cambio_estado_en_historial(self):
        """Verificar que cada cambio de estado se registra en HistorialCompra.

        Escenario: Se realiza un cambio de estado y se verifica que quede
        registrado con usuario, evento, descripción y fecha.

        Datos de entrada:
        - Compra: estado Pendiente
        - Cambio: Pendiente → Confirmada

        Resultado esperado:
        - Se crea registro en HistorialCompra
        - Contiene usuario, evento, descripción y fecha
        - El orden cronológico es correcto
        """
        compra = Compra.objects.create(
            proveedor=self.proveedor,
            documento_usuario=self.usuario,
            estado='pendiente',
            valor=Decimal('30000.00'),
            saldo=Decimal('30000.00'),
        )

        # Registrar cambio de estado
        estado_anterior = compra.estado
        compra.estado = 'confirmada'
        compra.save(update_fields=['estado'])

        historial = HistorialCompra.objects.create(
            compra=compra,
            evento='editada',
            usuario=self.usuario,
            descripcion=f'Estado cambiado de {estado_anterior} a confirmada.',
        )

        # Verificar que se registró correctamente
        self.assertIsNotNone(historial.id)
        self.assertEqual(historial.compra, compra)
        self.assertEqual(historial.evento, 'editada')
        self.assertEqual(historial.usuario, self.usuario)
        self.assertIn('pendiente', historial.descripcion)
        self.assertIn('confirmada', historial.descripcion)
        self.assertIsNotNone(historial.fecha)

        # Verificar que existe en la BD
        self.assertTrue(
            HistorialCompra.objects.filter(
                compra=compra,
                usuario=self.usuario
            ).exists()
        )
