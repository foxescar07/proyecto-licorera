# inventario/tests.py

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from productos.models import Categoria, Producto, PresentacionProducto
from inventario.models import (
    AgendaInventario,
    Hallazgo,
    Inventario,
    Lote,
    MovimientoInventario,
)

User = get_user_model()


# ─────────────────────────────────────────────
#  DATOS BASE COMPARTIDOS (setUp)
# ─────────────────────────────────────────────
class BaseTestCase(TestCase):
    """Crea los objetos mínimos que todos los tests necesitan."""

    def setUp(self):
        self.usuario = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.categoria = Categoria.objects.create(
            codigo='CAT01',
            nombre='Medicamentos'
        )
        self.producto = Producto.objects.create(
            codigo='PROD01',
            nombre='Ibuprofeno',
            categoria=self.categoria
        )
        self.presentacion = PresentacionProducto.objects.create(
            producto=self.producto,
            nombre='Caja x10',
            unidades=10,
            cantidad=0,
            precio=Decimal('15000.00')
        )
        self.lote = Lote.objects.create(
            numero_lote='LOTE-001',
            presentacion=self.presentacion,
            stock_actual=100,
            costo_unitario=Decimal('1200.00'),
            registrado_por=self.usuario
        )
        self.inventario = Inventario.objects.create(
            producto=self.producto,
            presentacion=self.presentacion,
            stock_actual=100,
            stock_min=20,
            stock_max=200
        )


# ─────────────────────────────────────────────
#  TESTS: Lote
# ─────────────────────────────────────────────
class LoteModelTest(BaseTestCase):

    def test_str_retorna_numero_lote_y_presentacion(self):
        """__str__ debe mostrar número de lote y presentación."""
        esperado = f"{self.lote.numero_lote} - {self.presentacion}"
        self.assertEqual(str(self.lote), esperado)

    def test_numero_lote_es_unico(self):
        """No se pueden crear dos lotes con el mismo número."""
        with self.assertRaises(IntegrityError):
            Lote.objects.create(
                numero_lote='LOTE-001',  # duplicado
                presentacion=self.presentacion,
                stock_actual=50,
                costo_unitario=Decimal('1000.00'),
                registrado_por=self.usuario
            )

    def test_dias_para_vencer_sin_fecha(self):
        """Si no hay fecha de vencimiento, debe retornar None."""
        self.assertIsNone(self.lote.dias_para_vencer)

    def test_dias_para_vencer_con_fecha_futura(self):
        """Debe retornar número positivo si vence en el futuro."""
        self.lote.fecha_vencimiento = date.today() + timedelta(days=10)
        self.lote.save()
        self.assertEqual(self.lote.dias_para_vencer, 10)

    def test_esta_vencido_con_fecha_pasada(self):
        """Debe retornar True si la fecha de vencimiento ya pasó."""
        self.lote.fecha_vencimiento = date.today() - timedelta(days=1)
        self.lote.save()
        self.assertTrue(self.lote.esta_vencido)

    def test_esta_vencido_con_fecha_futura(self):
        """Debe retornar False si aún no ha vencido."""
        self.lote.fecha_vencimiento = date.today() + timedelta(days=5)
        self.lote.save()
        self.assertFalse(self.lote.esta_vencido)

    def test_proximo_a_vencer_dentro_de_30_dias(self):
        """Debe retornar True si vence en 0 a 30 días."""
        self.lote.fecha_vencimiento = date.today() + timedelta(days=20)
        self.lote.save()
        self.assertTrue(self.lote.proximo_a_vencer)

    def test_proximo_a_vencer_falso_si_vence_despues_de_30_dias(self):
        """Debe retornar False si vence en más de 30 días."""
        self.lote.fecha_vencimiento = date.today() + timedelta(days=31)
        self.lote.save()
        self.assertFalse(self.lote.proximo_a_vencer)

    def test_proximo_a_vencer_falso_sin_fecha(self):
        """Debe retornar False si no tiene fecha de vencimiento."""
        self.assertFalse(self.lote.proximo_a_vencer)

    def test_stock_actual_no_puede_ser_negativo(self):
        """PositiveIntegerField rechaza valores negativos."""
        lote = Lote(
            numero_lote='LOTE-NEG',
            presentacion=self.presentacion,
            stock_actual=-1,
            costo_unitario=Decimal('1000.00'),
            registrado_por=self.usuario
        )
        with self.assertRaises(Exception):
            lote.full_clean()

    def test_ordering_por_fecha_registro_descendente(self):
        """Los lotes más recientes deben aparecer primero."""
        lote2 = Lote.objects.create(
            numero_lote='LOTE-002',
            presentacion=self.presentacion,
            stock_actual=50,
            costo_unitario=Decimal('1000.00'),
            registrado_por=self.usuario
        )
        primero = Lote.objects.first()
        self.assertEqual(primero, lote2)


# ─────────────────────────────────────────────
#  TESTS: Inventario (stock)
# ─────────────────────────────────────────────
class InventarioModelTest(BaseTestCase):

    def test_str_retorna_producto_presentacion_y_stock(self):
        """__str__ debe mostrar producto, presentación y stock actual."""
        self.assertIn(str(self.producto), str(self.inventario))
        self.assertIn('100', str(self.inventario))

    def test_necesita_reabastecimiento_true_si_stock_bajo(self):
        """Debe ser True cuando el stock actual está en o bajo el mínimo."""
        self.inventario.stock_actual = 20
        self.inventario.save()
        self.assertTrue(self.inventario.necesita_reabastecimiento)

    def test_necesita_reabastecimiento_false_si_stock_suficiente(self):
        """Debe ser False cuando el stock actual supera el mínimo."""
        self.inventario.stock_actual = 50
        self.inventario.save()
        self.assertFalse(self.inventario.necesita_reabastecimiento)

    def test_unique_together_producto_presentacion(self):
        """No se puede tener dos registros de stock para el mismo producto+presentación."""
        with self.assertRaises(IntegrityError):
            Inventario.objects.create(
                producto=self.producto,
                presentacion=self.presentacion,
                stock_actual=10,
                stock_min=5,
                stock_max=50
            )

    def test_stock_min_y_max_por_defecto_cero(self):
        otra_presentacion = PresentacionProducto.objects.create(
            producto=self.producto,
            nombre='Caja x20',
            unidades=20,
            cantidad=0,
            precio=Decimal('28000.00')
        )
        inv = Inventario.objects.create(
            producto=self.producto,
            presentacion=otra_presentacion
        )
        self.assertEqual(inv.stock_min, 0)
        self.assertEqual(inv.stock_max, 0)


# ─────────────────────────────────────────────
#  TESTS: MovimientoInventario
# ─────────────────────────────────────────────
class MovimientoInventarioModelTest(BaseTestCase):

    def _crear_movimiento(self, tipo='entrada', cantidad=10):
        return MovimientoInventario.objects.create(
            inventario=self.inventario,
            lote=self.lote,
            registrado_por=self.usuario,
            tipo=tipo,
            cantidad=cantidad,
            motivo='Test'
        )

    def test_str_retorna_tipo_inventario_cantidad(self):
        """__str__ debe mostrar tipo, inventario y cantidad."""
        mov = self._crear_movimiento(tipo='entrada', cantidad=10)
        self.assertIn('entrada', str(mov))
        self.assertIn('10', str(mov))

    def test_crear_movimiento_entrada(self):
        mov = self._crear_movimiento(tipo='entrada', cantidad=20)
        self.assertEqual(mov.tipo, 'entrada')
        self.assertEqual(mov.cantidad, 20)

    def test_crear_movimiento_salida(self):
        mov = self._crear_movimiento(tipo='salida', cantidad=5)
        self.assertEqual(mov.tipo, 'salida')

    def test_crear_movimiento_ajuste(self):
        mov = self._crear_movimiento(tipo='ajuste', cantidad=-3)
        self.assertEqual(mov.tipo, 'ajuste')

    def test_motivo_puede_estar_en_blanco(self):
        """El campo motivo es opcional."""
        mov = MovimientoInventario.objects.create(
            inventario=self.inventario,
            lote=self.lote,
            registrado_por=self.usuario,
            tipo='entrada',
            cantidad=5,
            motivo=''
        )
        self.assertEqual(mov.motivo, '')

    def test_stock_resultante_puede_ser_nulo(self):
        """stock_resultante es opcional."""
        mov = self._crear_movimiento()
        self.assertIsNone(mov.stock_resultante)

    def test_fecha_se_asigna_automaticamente(self):
        """fecha debe llenarse sola (auto_now_add), no se pasa manualmente."""
        mov = self._crear_movimiento()
        self.assertIsNotNone(mov.fecha)

    def test_ordering_por_fecha_descendente(self):
        """El movimiento más reciente debe aparecer primero."""
        mov1 = self._crear_movimiento(cantidad=5)
        mov2 = self._crear_movimiento(cantidad=15)
        primero = MovimientoInventario.objects.first()
        self.assertEqual(primero, mov2)


# ─────────────────────────────────────────────
#  TESTS: AgendaInventario
# ─────────────────────────────────────────────
class AgendaInventarioModelTest(BaseTestCase):

    def _crear_agenda(self, estado='pendiente'):
        return AgendaInventario.objects.create(
            titulo='Conteo mensual',
            descripcion='Conteo físico del almacén principal',
            fecha=timezone.now() + timedelta(days=7),
            tipo='conteo',
            estado=estado,
            documento_usuario=self.usuario,
            responsable=self.usuario
        )

    def test_str_incluye_titulo_y_fecha(self):
        agenda = self._crear_agenda()
        self.assertIn('Conteo mensual', str(agenda))

    def test_estado_por_defecto_es_pendiente(self):
        agenda = self._crear_agenda()
        self.assertEqual(agenda.estado, 'pendiente')

    def test_estado_en_proceso(self):
        agenda = self._crear_agenda(estado='en_proceso')
        self.assertEqual(agenda.estado, 'en_proceso')

    def test_estado_completada(self):
        agenda = self._crear_agenda(estado='completada')
        self.assertEqual(agenda.estado, 'completada')

    def test_descripcion_puede_ser_nula(self):
        agenda = AgendaInventario.objects.create(
            titulo='Sin descripción',
            fecha=timezone.now() + timedelta(days=7),
            documento_usuario=self.usuario
        )
        self.assertIsNone(agenda.descripcion)

    def test_responsable_puede_ser_nulo(self):
        """responsable es opcional; solo documento_usuario es obligatorio."""
        agenda = AgendaInventario.objects.create(
            titulo='Sin responsable asignado',
            fecha=timezone.now() + timedelta(days=7),
            documento_usuario=self.usuario
        )
        self.assertIsNone(agenda.responsable)

    def test_ordering_por_fecha_ascendente(self):
        """La agenda más próxima debe aparecer primero."""
        agenda1 = AgendaInventario.objects.create(
            titulo='Segunda',
            fecha=timezone.now() + timedelta(days=14),
            documento_usuario=self.usuario
        )
        agenda2 = AgendaInventario.objects.create(
            titulo='Primera',
            fecha=timezone.now() + timedelta(days=3),
            documento_usuario=self.usuario
        )
        primera = AgendaInventario.objects.first()
        self.assertEqual(primera, agenda2)


# ─────────────────────────────────────────────
#  TESTS: Hallazgo
# ─────────────────────────────────────────────
class HallazgoModelTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.agenda = AgendaInventario.objects.create(
            titulo='Conteo bodega',
            fecha=timezone.now(),
            documento_usuario=self.usuario
        )

    def _crear_hallazgo(self, cantidad_sistema, cantidad_fisica):
        return Hallazgo.objects.create(
            agenda=self.agenda,
            producto=self.producto,
            cantidad_sistema=cantidad_sistema,
            cantidad_fisica=cantidad_fisica,
            sesion_conteo='SESION-001'
        )

    def test_str_incluye_producto_y_diferencia(self):
        hallazgo = self._crear_hallazgo(100, 90)
        self.assertIn(str(hallazgo.diferencia), str(hallazgo))

    def test_diferencia_se_calcula_automaticamente(self):
        """diferencia = cantidad_fisica - cantidad_sistema, sin necesidad de pasarla."""
        hallazgo = self._crear_hallazgo(80, 100)
        self.assertEqual(hallazgo.diferencia, 20)

    def test_tipo_hallazgo_sobrante_si_diferencia_positiva(self):
        hallazgo = self._crear_hallazgo(80, 100)
        self.assertEqual(hallazgo.tipo_hallazgo, 'sobrante')

    def test_tipo_hallazgo_faltante_si_diferencia_negativa(self):
        hallazgo = self._crear_hallazgo(100, 80)
        self.assertEqual(hallazgo.tipo_hallazgo, 'faltante')

    def test_tipo_hallazgo_exacto_si_diferencia_cero(self):
        hallazgo = self._crear_hallazgo(50, 50)
        self.assertEqual(hallazgo.tipo_hallazgo, 'exacto')

    def test_tipo_hallazgo_se_recalcula_al_actualizar(self):
        """Si se edita cantidad_fisica, diferencia y tipo_hallazgo deben recalcularse."""
        hallazgo = self._crear_hallazgo(50, 50)
        self.assertEqual(hallazgo.tipo_hallazgo, 'exacto')
        hallazgo.cantidad_fisica = 30
        hallazgo.save()
        self.assertEqual(hallazgo.diferencia, -20)
        self.assertEqual(hallazgo.tipo_hallazgo, 'faltante')

    def test_observaciones_puede_estar_en_blanco(self):
        hallazgo = self._crear_hallazgo(50, 50)
        self.assertEqual(hallazgo.observaciones, '')

    def test_ordering_por_fecha_hallazgo_descendente(self):
        """El hallazgo más reciente debe aparecer primero."""
        h1 = self._crear_hallazgo(50, 50)
        h2 = self._crear_hallazgo(60, 55)
        primero = Hallazgo.objects.first()
        self.assertEqual(primero, h2)