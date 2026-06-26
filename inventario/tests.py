# inventario/tests.py

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal

from productos.models import Categoria, Producto, PresentacionProducto
from inventario.models import (
    Lote, Inventario, SesionConteo,
    ConteoProducto, ResultadoInventario, AgendaInventario
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
        from django.db import IntegrityError
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
        from django.core.exceptions import ValidationError
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
#  TESTS: Inventario (movimientos)
# ─────────────────────────────────────────────
class InventarioModelTest(BaseTestCase):

    def _crear_movimiento(self, tipo='entrada', cantidad=10):
        return Inventario.objects.create(
            presentacion=self.presentacion,
            lote=self.lote,
            registrado_por=self.usuario,
            tipo=tipo,
            cantidad=cantidad,
            motivo='Test'
        )

    def test_str_retorna_tipo_presentacion_cantidad(self):
        """__str__ debe mostrar tipo, presentación y cantidad."""
        mov = self._crear_movimiento(tipo='entrada', cantidad=10)
        self.assertIn('entrada', str(mov))
        self.assertIn('10', str(mov))

    def test_crear_movimiento_entrada(self):
        """Debe poder crear un movimiento de tipo entrada."""
        mov = self._crear_movimiento(tipo='entrada', cantidad=20)
        self.assertEqual(mov.tipo, 'entrada')
        self.assertEqual(mov.cantidad, 20)

    def test_crear_movimiento_salida(self):
        """Debe poder crear un movimiento de tipo salida."""
        mov = self._crear_movimiento(tipo='salida', cantidad=5)
        self.assertEqual(mov.tipo, 'salida')

    def test_crear_movimiento_ajuste(self):
        """Debe poder crear un movimiento de tipo ajuste."""
        mov = self._crear_movimiento(tipo='ajuste', cantidad=-3)
        self.assertEqual(mov.tipo, 'ajuste')

    def test_motivo_puede_estar_en_blanco(self):
        """El campo motivo es opcional."""
        mov = Inventario.objects.create(
            presentacion=self.presentacion,
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

    def test_ordering_por_fecha_descendente(self):
        """El movimiento más reciente debe aparecer primero."""
        mov1 = self._crear_movimiento(cantidad=5)
        mov2 = self._crear_movimiento(cantidad=15)
        primero = Inventario.objects.first()
        self.assertEqual(primero, mov2)


# ─────────────────────────────────────────────
#  TESTS: SesionConteo
# ─────────────────────────────────────────────
class SesionConteoModelTest(BaseTestCase):

    def _crear_sesion(self, estado='activa'):
        return SesionConteo.objects.create(
            estado=estado,
            responsable=self.usuario
        )

    def test_str_incluye_id_y_estado(self):
        sesion = self._crear_sesion()
        self.assertIn(str(sesion.id), str(sesion))
        self.assertIn('activa', str(sesion))

    def test_estado_por_defecto_es_activa(self):
        sesion = self._crear_sesion()
        self.assertEqual(sesion.estado, 'activa')

    def test_estado_finalizada(self):
        sesion = self._crear_sesion(estado='finalizada')
        self.assertEqual(sesion.estado, 'finalizada')

    def test_estado_cancelada(self):
        sesion = self._crear_sesion(estado='cancelada')
        self.assertEqual(sesion.estado, 'cancelada')

    def test_fecha_fin_puede_ser_nula(self):
        sesion = self._crear_sesion()
        self.assertIsNone(sesion.fecha_fin)

    def test_fecha_fin_se_puede_asignar(self):
        sesion = self._crear_sesion()
        sesion.fecha_fin = timezone.now()
        sesion.save()
        self.assertIsNotNone(sesion.fecha_fin)


# ─────────────────────────────────────────────
#  TESTS: ConteoProducto
# ─────────────────────────────────────────────
class ConteoProductoModelTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.sesion = SesionConteo.objects.create(
            responsable=self.usuario
        )

    def test_str_incluye_presentacion_y_cantidad(self):
        conteo = ConteoProducto.objects.create(
            sesion=self.sesion,
            presentacion=self.presentacion,
            cantidad_contada=25
        )
        self.assertIn('25', str(conteo))

    def test_cantidad_contada_por_defecto_es_cero(self):
        conteo = ConteoProducto.objects.create(
            sesion=self.sesion,
            presentacion=self.presentacion
        )
        self.assertEqual(conteo.cantidad_contada, 0)

    def test_unique_together_sesion_presentacion(self):
        """No se puede contar la misma presentación dos veces en la misma sesión."""
        from django.db import IntegrityError
        ConteoProducto.objects.create(
            sesion=self.sesion,
            presentacion=self.presentacion,
            cantidad_contada=10
        )
        with self.assertRaises(IntegrityError):
            ConteoProducto.objects.create(
                sesion=self.sesion,
                presentacion=self.presentacion,
                cantidad_contada=20
            )


# ─────────────────────────────────────────────
#  TESTS: ResultadoInventario
# ─────────────────────────────────────────────
class ResultadoInventarioModelTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.sesion = SesionConteo.objects.create(
            responsable=self.usuario
        )

    def test_str_incluye_presentacion_y_diferencia(self):
        resultado = ResultadoInventario.objects.create(
            sesion=self.sesion,
            presentacion=self.presentacion,
            cantidad_sistema=100,
            cantidad_fisica=90,
            diferencia=-10
        )
        self.assertIn('-10', str(resultado))

    def test_diferencia_positiva(self):
        """Si hay más físico que en sistema, diferencia es positiva."""
        resultado = ResultadoInventario.objects.create(
            sesion=self.sesion,
            presentacion=self.presentacion,
            cantidad_sistema=80,
            cantidad_fisica=100,
            diferencia=20
        )
        self.assertEqual(resultado.diferencia, 20)

    def test_diferencia_negativa(self):
        """Si hay menos físico que en sistema, diferencia es negativa."""
        resultado = ResultadoInventario.objects.create(
            sesion=self.sesion,
            presentacion=self.presentacion,
            cantidad_sistema=100,
            cantidad_fisica=80,
            diferencia=-20
        )
        self.assertEqual(resultado.diferencia, -20)

    def test_diferencia_cero(self):
        """Si coinciden, diferencia es cero."""
        resultado = ResultadoInventario.objects.create(
            sesion=self.sesion,
            presentacion=self.presentacion,
            cantidad_sistema=50,
            cantidad_fisica=50,
            diferencia=0
        )
        self.assertEqual(resultado.diferencia, 0)


# ─────────────────────────────────────────────
#  TESTS: AgendaInventario
# ─────────────────────────────────────────────
class AgendaInventarioModelTest(BaseTestCase):

    def _crear_agenda(self, estado='pendiente'):
        return AgendaInventario.objects.create(
            titulo='Conteo mensual',
            fecha_programada=timezone.now() + timedelta(days=7),
            estado=estado,
            creado_por=self.usuario,
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
        agenda = self._crear_agenda()
        self.assertIsNone(agenda.descripcion)

    def test_ordering_por_fecha_programada_ascendente(self):
        """La agenda más próxima debe aparecer primero."""
        agenda1 = AgendaInventario.objects.create(
            titulo='Segunda',
            fecha_programada=timezone.now() + timedelta(days=14),
            creado_por=self.usuario,
            responsable=self.usuario
        )
        agenda2 = AgendaInventario.objects.create(
            titulo='Primera',
            fecha_programada=timezone.now() + timedelta(days=3),
            creado_por=self.usuario,
            responsable=self.usuario
        )
        primera = AgendaInventario.objects.first()
        self.assertEqual(primera, agenda2)