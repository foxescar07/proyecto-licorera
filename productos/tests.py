# productos/tests.py

from django.test import TestCase
from django.db import IntegrityError
from decimal import Decimal
from unittest.mock import patch, MagicMock

from productos.models import Categoria, Producto, PresentacionProducto


# ─────────────────────────────────────────────
#  TESTS: Categoria
# ─────────────────────────────────────────────
class CategoriaModelTest(TestCase):

    def test_str_sin_padre(self):
        """Una categoría raíz muestra solo su nombre."""
        cat = Categoria.objects.create(codigo='C01', nombre='Medicamentos')
        self.assertEqual(str(cat), 'Medicamentos')

    def test_str_con_padre(self):
        """Una subcategoría muestra padre → nombre."""
        padre = Categoria.objects.create(codigo='C01', nombre='Medicamentos')
        hijo = Categoria.objects.create(
            codigo='C02', nombre='Analgésicos', padre=padre
        )
        self.assertEqual(str(hijo), 'Medicamentos → Analgésicos')

    def test_codigo_es_unico(self):
        """No se permiten dos categorías con el mismo código."""
        Categoria.objects.create(codigo='C01', nombre='Medicamentos')
        with self.assertRaises(IntegrityError):
            Categoria.objects.create(codigo='C01', nombre='Otra')

    def test_padre_puede_ser_nulo(self):
        """Una categoría raíz no necesita padre."""
        cat = Categoria.objects.create(codigo='C01', nombre='Raíz')
        self.assertIsNone(cat.padre)

    def test_subcategorias_related_name(self):
        """Se puede acceder a las subcategorías desde el padre."""
        padre = Categoria.objects.create(codigo='C01', nombre='Medicamentos')
        hijo = Categoria.objects.create(
            codigo='C02', nombre='Analgésicos', padre=padre
        )
        self.assertIn(hijo, padre.subcategorias.all())

    def test_ordering_por_nombre(self):
        """Las categorías se ordenan alfabéticamente por nombre."""
        Categoria.objects.create(codigo='C02', nombre='Vitaminas')
        Categoria.objects.create(codigo='C01', nombre='Antibióticos')
        primera = Categoria.objects.first()
        self.assertEqual(primera.nombre, 'Antibióticos')


# ─────────────────────────────────────────────
#  TESTS: Producto
# ─────────────────────────────────────────────
class ProductoModelTest(TestCase):

    def setUp(self):
        self.categoria = Categoria.objects.create(
            codigo='CAT01', nombre='Medicamentos'
        )
        self.producto = Producto.objects.create(
            codigo='PROD01',
            nombre='Ibuprofeno',
            categoria=self.categoria
        )

    def test_str_incluye_nombre_y_codigo(self):
        """__str__ debe mostrar nombre y código."""
        self.assertEqual(str(self.producto), 'Ibuprofeno (PROD01)')

    def test_codigo_es_unico(self):
        """No se permiten dos productos con el mismo código."""
        with self.assertRaises(IntegrityError):
            Producto.objects.create(
                codigo='PROD01',
                nombre='Otro producto',
                categoria=self.categoria
            )

    def test_cantidad_disponible_por_defecto_es_cero(self):
        self.assertEqual(self.producto.cantidad_disponible, 0)

    def test_precio_unitario_por_defecto_es_cero(self):
        self.assertEqual(self.producto.precio_unitario, Decimal('0'))

    def test_unidad_por_defecto_es_und(self):
        self.assertEqual(self.producto.unidad, 'UND')

    def test_stock_critico_cuando_stock_es_cinco_o_menos(self):
        """stock_critico debe ser True cuando el stock total es 5 o menos."""
        with patch.object(
            type(self.producto), 'stock_total',
            new_callable=lambda: property(lambda self: 5)
        ):
            self.assertTrue(self.producto.stock_critico)

    def test_stock_critico_falso_cuando_stock_es_mayor_a_cinco(self):
        with patch.object(
            type(self.producto), 'stock_total',
            new_callable=lambda: property(lambda self: 6)
        ):
            self.assertFalse(self.producto.stock_critico)

    def test_stock_total_sin_lotes_retorna_cero(self):
        """Sin lotes asociados el stock total debe ser 0."""
        self.assertEqual(self.producto.stock_total, 0)

    def test_precio_base_retorna_precio_primera_presentacion(self):
        """precio_base retorna el precio de la presentación con menor unidades."""
        PresentacionProducto.objects.create(
            producto=self.producto,
            nombre='Caja x10',
            unidades=10,
            cantidad=0,
            precio=Decimal('15000.00')
        )
        self.assertEqual(self.producto.precio_base(), Decimal('15000.00'))

    def test_precio_base_sin_presentaciones_retorna_precio_unitario(self):
        """Si no hay presentaciones, retorna precio_unitario."""
        self.producto.precio_unitario = Decimal('5000.00')
        self.producto.save()
        self.assertEqual(self.producto.precio_base(), Decimal('5000.00'))

    def test_ordering_por_nombre(self):
        """Los productos se ordenan alfabéticamente."""
        Producto.objects.create(
            codigo='PROD02', nombre='Acetaminofén', categoria=self.categoria
        )
        primero = Producto.objects.first()
        self.assertEqual(primero.nombre, 'Acetaminofén')


# ─────────────────────────────────────────────
#  TESTS: PresentacionProducto
# ─────────────────────────────────────────────
class PresentacionProductoModelTest(TestCase):

    def setUp(self):
        self.categoria = Categoria.objects.create(
            codigo='CAT01', nombre='Medicamentos'
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

    def test_str_incluye_producto_nombre_y_unidades(self):
        """__str__ debe mostrar producto, presentación y unidades."""
        resultado = str(self.presentacion)
        self.assertIn('Ibuprofeno', resultado)
        self.assertIn('Caja x10', resultado)
        self.assertIn('10', resultado)

    def test_unidades_por_defecto_es_uno(self):
        pres = PresentacionProducto.objects.create(
            producto=self.producto,
            nombre='Unidad',
            cantidad=0,
            precio=Decimal('1500.00')
        )
        self.assertEqual(pres.unidades, 1)

    def test_cantidad_por_defecto_es_cero(self):
        self.assertEqual(self.presentacion.cantidad, 0)

    def test_stock_real_sin_lotes_es_cero(self):
        """Sin lotes, el stock real debe ser 0."""
        self.assertEqual(self.presentacion.stock_real, 0)

    def test_ordering_por_unidades_ascendente(self):
        """La presentación con menos unidades aparece primero."""
        PresentacionProducto.objects.create(
            producto=self.producto,
            nombre='Unidad',
            unidades=1,
            cantidad=0,
            precio=Decimal('1500.00')
        )
        primera = PresentacionProducto.objects.filter(
            producto=self.producto
        ).first()
        self.assertEqual(primera.unidades, 1)

    def test_presentaciones_related_name_desde_producto(self):
        """Se accede a presentaciones desde el producto con .presentaciones."""
        self.assertIn(
            self.presentacion,
            self.producto.presentaciones.all()
        )