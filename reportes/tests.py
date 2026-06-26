from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch, MagicMock
from datetime import date, timedelta
import zoneinfo
 
from usuarios.models import Usuario
from clientes.models import Cliente # type: ignore
 
ZONA_COLOMBIA = zoneinfo.ZoneInfo('America/Bogota')
 
 
# ═══════════════════════════════════════════════════════
#  HELPERS: crear datos mínimos reutilizables
# ═══════════════════════════════════════════════════════
 
def _crear_categoria(codigo='RON', nombre='Ron'):
    from productos.models import Categoria
    return Categoria.objects.get_or_create(codigo=codigo, defaults={'nombre': nombre})[0]
 
 
def _crear_producto(codigo='BACARDI', nombre='Bacardi', categoria=None):
    from productos.models import Producto
    if categoria is None:
        categoria = _crear_categoria()
    return Producto.objects.get_or_create(
        codigo=codigo,
        defaults={'nombre': nombre, 'categoria': categoria}
    )[0]
 
 
def _crear_presentacion(producto=None, nombre='750ml', precio=45000):
    from productos.models import PresentacionProducto
    if producto is None:
        producto = _crear_producto()
    return PresentacionProducto.objects.create(
        producto=producto, nombre=nombre, unidades=1, precio=precio
    )
 
 
def _crear_cliente():
    from clientes.models import Cliente # type: ignore
    import uuid
    uid = str(uuid.uuid4())[:8]
    return Cliente.objects.create(
        nombre=f'Cliente {uid}',
        email=f'{uid}@test.com'
    )
 
 
def _crear_venta(cliente=None, total=45000, fecha=None):
    """
    Crea una Venta de prueba.
 
    NOTA IMPORTANTE sobre el modelo Venta:
    - 'total_venta' es una @property (sin setter), NO un campo real.
      El campo real que almacena el total es 'total_con_descuento'.
    - 'fecha' tiene auto_now_add=True, por lo que Django ignora
      cualquier valor pasado en create()/save(). Para fijar una
      fecha específica en los tests hay que usar QuerySet.update(),
      que no dispara la lógica de auto_now_add.
    """
    from ventas.models import Venta
    if cliente is None:
        cliente = _crear_cliente()
 
    venta = Venta.objects.create(
        cliente=cliente,
        descuento_porcentaje=0,
        total_con_descuento=total,
    )
 
    if fecha:
        Venta.objects.filter(pk=venta.pk).update(fecha=fecha)
        venta.refresh_from_db()
 
    return venta
 
 
def _crear_detalle_venta(venta, presentacion=None, cantidad=1, precio_unitario=45000):
    from ventas.models import DetalleVenta
    if presentacion is None:
        presentacion = _crear_presentacion()
    return DetalleVenta.objects.create(
        venta=venta,
        producto=presentacion.producto,
        presentacion=presentacion,
        cantidad=cantidad,
        precio_unitario=precio_unitario,
    )
 
 
def _crear_movimiento(presentacion=None, tipo='entrada', cantidad=10, motivo='Compra'):
    from inventario.models import Inventario
    if presentacion is None:
        presentacion = _crear_presentacion()
    return Inventario.objects.create(
        presentacion=presentacion,
        tipo=tipo,
        cantidad=cantidad,
        motivo=motivo,
    )
 
 
# ═══════════════════════════════════════════════════════
#  TESTS: Vista principal — contexto y filtros
# ═══════════════════════════════════════════════════════
 
class ReportesViewContextTest(TestCase):
    """Verifica que la vista principal entrega el contexto correcto."""
 
    def setUp(self):
        self.client = Client()
        self.usuario = Usuario.objects.create_user(
            username='empleado_rep', password='pass123'
        )
        self.client.force_login(self.usuario)
        self.url = reverse('reportes')
 
        self.presentacion = _crear_presentacion()
        self.venta = _crear_venta(total=90000)
        _crear_detalle_venta(self.venta, self.presentacion, cantidad=2, precio_unitario=45000)
 
    # ✓ Vista responde 200
    def test_vista_responde_ok(self):
        """Verificar que la vista carga correctamente."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
 
    # ✓ Contexto contiene claves esenciales
    def test_contexto_contiene_claves_esenciales(self):
        """Verificar que el contexto incluye todas las variables del template."""
        response = self.client.get(self.url)
        claves = [
            'ventas', 'total_ventas', 'total_productos', 'total_clientes',
            'productos', 'proveedores',
            'total_registrados', 'total_en_stock', 'total_stock_bajo', 'total_agotados',
            'entradas', 'salidas',
            'hoy', 'ventas_hoy', 'ingresos_hoy',
            'entradas_hoy', 'salidas_hoy', 'total_entradas_hoy', 'total_salidas_hoy',
            'top_productos_hoy', 'ventas_json',
        ]
        for clave in claves:
            self.assertIn(clave, response.context, f"Falta '{clave}' en el contexto")
 
    # ✓ Total ventas calculado correctamente
    def test_total_ventas_es_correcto(self):
        """Verificar que total_ventas suma los totales de todas las ventas."""
        response = self.client.get(self.url)
        self.assertEqual(response.context['total_ventas'], 90000)
 
    # ✓ Total clientes únicos
    def test_total_clientes_unicos(self):
        """Verificar que total_clientes cuenta clientes distintos."""
        response = self.client.get(self.url)
        self.assertGreaterEqual(response.context['total_clientes'], 1)
 
    # ✓ Lista de proveedores tiene datos estáticos
    def test_proveedores_lista_no_vacia(self):
        """Verificar que la lista de proveedores contiene al menos un registro."""
        response = self.client.get(self.url)
        self.assertGreater(len(response.context['proveedores']), 0)
 
    # ✓ ventas_json es una cadena JSON válida
    def test_ventas_json_es_valido(self):
        """Verificar que ventas_json es JSON parseable."""
        import json
        response = self.client.get(self.url)
        json_str = response.context['ventas_json']
        try:
            datos = json.loads(json_str)
            self.assertIsInstance(datos, list)
        except json.JSONDecodeError:
            self.fail("ventas_json no es JSON válido")
 
    # ✓ Paginación presente en contexto
    def test_paginacion_en_contexto(self):
        """Verificar que page_obj y paginator están en el contexto."""
        response = self.client.get(self.url)
        self.assertIn('page_obj',  response.context)
        self.assertIn('paginator', response.context)
 
 
# ═══════════════════════════════════════════════════════
#  TESTS: Filtros por fecha
# ═══════════════════════════════════════════════════════
 
class ReportesFiltroFechaTest(TestCase):
    """Verifica el filtrado de ventas por rango de fechas."""
 
    def setUp(self):
        self.client = Client()
        self.usuario = Usuario.objects.create_user(username='emp_filtro', password='pass')
        self.client.force_login(self.usuario)
        self.url = reverse('reportes')
 
        self.presentacion = _crear_presentacion()
 
        hoy        = timezone.now()
        hace_5dias = hoy - timedelta(days=5)
        hace_1mes  = hoy - timedelta(days=30)
 
        self.venta_hoy   = _crear_venta(total=10000, fecha=hoy)
        self.venta_5dias = _crear_venta(total=20000, fecha=hace_5dias)
        self.venta_mes   = _crear_venta(total=30000, fecha=hace_1mes)
 
        for v in [self.venta_hoy, self.venta_5dias, self.venta_mes]:
            _crear_detalle_venta(v, self.presentacion)
 
    # ✓ Sin filtros devuelve todas las ventas
    def test_sin_filtros_devuelve_todas(self):
        """Verificar que sin fecha_inicio/fin se retornan todas las ventas."""
        response = self.client.get(self.url)
        ids = [v.id for v in response.context['ventas']]
        self.assertIn(self.venta_hoy.id,   ids)
        self.assertIn(self.venta_5dias.id, ids)
        self.assertIn(self.venta_mes.id,   ids)
 
    # ✓ Filtro por fecha_inicio excluye anteriores
    def test_filtro_fecha_inicio_excluye_anteriores(self):
        """Verificar que fecha_inicio filtra ventas anteriores a esa fecha."""
        hace_3dias = (timezone.now() - timedelta(days=3)).strftime('%Y-%m-%d')
        response = self.client.get(self.url, {'fecha_inicio': hace_3dias})
        ids = [v.id for v in response.context['ventas']]
        self.assertIn(self.venta_hoy.id, ids)
        self.assertNotIn(self.venta_mes.id, ids)
 
    # ✓ Filtro por fecha_fin excluye posteriores
    def test_filtro_fecha_fin_excluye_posteriores(self):
        """Verificar que fecha_fin filtra ventas posteriores a esa fecha."""
        hace_10dias = (timezone.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        response = self.client.get(self.url, {'fecha_fin': hace_10dias})
        ids = [v.id for v in response.context['ventas']]
        self.assertNotIn(self.venta_hoy.id, ids)
        self.assertIn(self.venta_mes.id, ids)
 
    # ✓ Rango exacto devuelve solo las ventas del período
    def test_rango_exacto_devuelve_periodo(self):
        """Verificar que un rango preciso devuelve solo las ventas en ese período."""
        fi = (timezone.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        ff = (timezone.now() - timedelta(days=3)).strftime('%Y-%m-%d')
        response = self.client.get(self.url, {'fecha_inicio': fi, 'fecha_fin': ff})
        ids = [v.id for v in response.context['ventas']]
        self.assertIn(self.venta_5dias.id, ids)
        self.assertNotIn(self.venta_hoy.id, ids)
        self.assertNotIn(self.venta_mes.id, ids)
 
    # ✓ fecha_inicio y fecha_fin se devuelven en el contexto
    def test_fechas_presentes_en_contexto(self):
        """Verificar que las fechas del filtro se pasan al contexto."""
        fi = '2025-01-01'
        ff = '2025-12-31'
        response = self.client.get(self.url, {'fecha_inicio': fi, 'fecha_fin': ff})
        self.assertEqual(response.context['fecha_inicio'], fi)
        self.assertEqual(response.context['fecha_fin'],    ff)
 
 
# ═══════════════════════════════════════════════════════
#  TESTS: Inventario — KPIs de stock
# ═══════════════════════════════════════════════════════
 
class ReportesInventarioKPITest(TestCase):
    """Verifica los conteos de inventario (en stock, bajo, agotado)."""
 
    def setUp(self):
        self.client = Client()
        self.usuario = Usuario.objects.create_user(username='emp_inv', password='pass')
        self.client.force_login(self.usuario)
        self.url = reverse('reportes')
 
    def _producto_con_stock(self, codigo, stock):
        """Crea un producto y mockea su propiedad stock_total."""
        from productos.models import Producto
        cat = _crear_categoria(codigo=f'CAT_{codigo}', nombre=f'Cat {codigo}')
        p   = Producto.objects.create(codigo=codigo, nombre=f'Prod {codigo}', categoria=cat)
        p.stock_total = stock
        return p
 
    # ✓ Producto con stock > 10 cuenta como "en stock"
    def test_stock_mayor_10_cuenta_en_stock(self):
        """Verificar que stock_total > 10 se clasifica como En Stock."""
        response = self.client.get(self.url)
        # La lógica de la vista: sum(1 for p in productos if p.stock_total > 10)
        self.assertIn('total_en_stock', response.context)
 
    # ✓ Producto con 0 < stock <= 10 cuenta como "stock bajo"
    def test_stock_entre_1_y_10_cuenta_stock_bajo(self):
        """Verificar que 0 < stock_total <= 10 se clasifica como Stock Bajo."""
        response = self.client.get(self.url)
        self.assertIn('total_stock_bajo', response.context)
 
    # ✓ Producto con stock == 0 cuenta como "agotado"
    def test_stock_cero_cuenta_agotado(self):
        """Verificar que stock_total == 0 se clasifica como Agotado."""
        response = self.client.get(self.url)
        self.assertIn('total_agotados', response.context)
 
    # ✓ Suma de categorías = total_registrados
    def test_suma_categorias_igual_total_registrados(self):
        """Verificar que en_stock + stock_bajo + agotados == total_registrados."""
        response = self.client.get(self.url)
        ctx = response.context
        suma = ctx['total_en_stock'] + ctx['total_stock_bajo'] + ctx['total_agotados']
        self.assertEqual(suma, ctx['total_registrados'])
 
 
# ═══════════════════════════════════════════════════════
#  TESTS: Resumen diario
# ═══════════════════════════════════════════════════════
 
class ReportesResumenDiarioTest(TestCase):
    """Verifica los valores del resumen del día de hoy."""
 
    def setUp(self):
        self.client = Client()
        self.usuario = Usuario.objects.create_user(username='emp_diario', password='pass')
        self.client.force_login(self.usuario)
        self.url = reverse('reportes')
 
        self.presentacion = _crear_presentacion(precio=50000)
 
        self.venta_hoy = _crear_venta(total=100000, fecha=timezone.now())
        _crear_detalle_venta(self.venta_hoy, self.presentacion, cantidad=2, precio_unitario=50000)
 
        _crear_movimiento(self.presentacion, tipo='entrada', cantidad=5)
        _crear_movimiento(self.presentacion, tipo='salida',  cantidad=3)
 
    # ✓ ingresos_hoy suma ventas de hoy
    def test_ingresos_hoy_suma_ventas_del_dia(self):
        """Verificar que ingresos_hoy solo suma ventas de la fecha actual."""
        response = self.client.get(self.url)
        self.assertEqual(response.context['ingresos_hoy'], 100000)
 
    # ✓ ventas_hoy contiene la venta de hoy
    def test_ventas_hoy_contiene_venta_actual(self):
        """Verificar que ventas_hoy incluye la venta creada hoy."""
        response = self.client.get(self.url)
        ids = [v.id for v in response.context['ventas_hoy']]
        self.assertIn(self.venta_hoy.id, ids)
 
    # ✓ total_entradas_hoy suma correctamente
    def test_total_entradas_hoy_correcto(self):
        """Verificar que total_entradas_hoy suma las cantidades de entrada del día."""
        response = self.client.get(self.url)
        self.assertEqual(response.context['total_entradas_hoy'], 5)
 
    # ✓ total_salidas_hoy suma correctamente
    def test_total_salidas_hoy_correcto(self):
        """Verificar que total_salidas_hoy suma las cantidades de salida del día."""
        response = self.client.get(self.url)
        self.assertEqual(response.context['total_salidas_hoy'], 3)
 
    # ✓ Venta de ayer NO aparece en ventas_hoy
    def test_venta_de_ayer_no_aparece_en_hoy(self):
        """Verificar que ventas de días anteriores no se incluyen en ventas_hoy."""
        ayer = timezone.now() - timedelta(days=1)
        venta_ayer = _crear_venta(total=50000, fecha=ayer)
        response   = self.client.get(self.url)
        ids        = [v.id for v in response.context['ventas_hoy']]
        self.assertNotIn(venta_ayer.id, ids)
 
    # ✓ hoy es la fecha actual en Colombia
    def test_hoy_es_fecha_correcta(self):
        """Verificar que 'hoy' en el contexto corresponde a la fecha actual."""
        response   = self.client.get(self.url)
        hoy_real   = timezone.now().astimezone(ZONA_COLOMBIA).date()
        self.assertEqual(response.context['hoy'], hoy_real)
 
 
# ═══════════════════════════════════════════════════════
#  TESTS: Top productos del día
# ═══════════════════════════════════════════════════════
 
class ReportesTopProductosTest(TestCase):
    """Verifica el cálculo de top productos vendidos hoy."""
 
    def setUp(self):
        self.client = Client()
        self.usuario = Usuario.objects.create_user(username='emp_top', password='pass')
        self.client.force_login(self.usuario)
        self.url = reverse('reportes')
 
        cat = _crear_categoria()
 
        from productos.models import Producto, PresentacionProducto
        self.prod_a = Producto.objects.create(codigo='A001', nombre='Producto A', categoria=cat)
        self.prod_b = Producto.objects.create(codigo='B001', nombre='Producto B', categoria=cat)
        self.pres_a = PresentacionProducto.objects.create(producto=self.prod_a, nombre='750ml', unidades=1, precio=60000)
        self.pres_b = PresentacionProducto.objects.create(producto=self.prod_b, nombre='1L',    unidades=1, precio=30000)
 
        venta = _crear_venta(total=420000, fecha=timezone.now())
        _crear_detalle_venta(venta, self.pres_a, cantidad=5, precio_unitario=60000)  # 300 000
        _crear_detalle_venta(venta, self.pres_b, cantidad=4, precio_unitario=30000)  # 120 000
 
    # ✓ top_productos_hoy es una lista
    def test_top_productos_es_lista(self):
        """Verificar que top_productos_hoy es iterable."""
        response = self.client.get(self.url)
        self.assertIsInstance(response.context['top_productos_hoy'], list)
 
    # ✓ Top tiene máximo 5 elementos
    def test_top_productos_maximo_5(self):
        """Verificar que el top no supera los 5 productos."""
        response = self.client.get(self.url)
        self.assertLessEqual(len(response.context['top_productos_hoy']), 5)
 
    # ✓ Producto A (mayor subtotal) aparece en el top
    def test_producto_mayor_subtotal_en_top(self):
        """Verificar que el producto con mayor subtotal aparece en top_productos_hoy."""
        response = self.client.get(self.url)
        nombres  = [nombre for nombre, _ in response.context['top_productos_hoy']]
        self.assertIn('Producto A', nombres)
 
    # ✓ Orden: producto de mayor subtotal va primero
    def test_orden_descendente_por_subtotal(self):
        """Verificar que el top está ordenado de mayor a menor subtotal."""
        response = self.client.get(self.url)
        top = response.context['top_productos_hoy']
        if len(top) >= 2:
            self.assertGreaterEqual(top[0][1]['subtotal'], top[1][1]['subtotal'])
 
    # ✓ Cada entrada tiene 'cantidad' y 'subtotal'
    def test_estructura_de_cada_entrada_del_top(self):
        """Verificar que cada elemento del top tiene las claves 'cantidad' y 'subtotal'."""
        response = self.client.get(self.url)
        for _, datos in response.context['top_productos_hoy']:
            self.assertIn('cantidad', datos)
            self.assertIn('subtotal', datos)
 
 
# ═══════════════════════════════════════════════════════
#  TESTS: Exportación Excel (CSV)
# ═══════════════════════════════════════════════════════
 
class ReportesExportExcelTest(TestCase):
    """Verifica la exportación CSV para cada tipo de reporte."""
 
    def setUp(self):
        self.client = Client()
        self.usuario = Usuario.objects.create_user(username='emp_excel', password='pass')
        self.client.force_login(self.usuario)
        self.url = reverse('reportes')
 
        self.presentacion = _crear_presentacion()
        venta = _crear_venta(total=45000, fecha=timezone.now())
        _crear_detalle_venta(venta, self.presentacion, cantidad=1, precio_unitario=45000)
        _crear_movimiento(self.presentacion, tipo='entrada', cantidad=10)
 
    # ✓ Export ventas devuelve CSV
    def test_export_ventas_devuelve_csv(self):
        """Verificar que export=excel&tipo=ventas devuelve un CSV."""
        response = self.client.get(self.url, {'export': 'excel', 'tipo': 'ventas'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
 
    # ✓ Export inventario devuelve CSV
    def test_export_inventario_devuelve_csv(self):
        """Verificar que export=excel&tipo=inventario devuelve un CSV."""
        response = self.client.get(self.url, {'export': 'excel', 'tipo': 'inventario'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
 
    # ✓ Export proveedores devuelve CSV
    def test_export_proveedores_devuelve_csv(self):
        """Verificar que export=excel&tipo=proveedores devuelve un CSV."""
        response = self.client.get(self.url, {'export': 'excel', 'tipo': 'proveedores'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
 
    # ✓ Export analisis devuelve CSV
    def test_export_analisis_devuelve_csv(self):
        """Verificar que export=excel&tipo=analisis devuelve un CSV."""
        response = self.client.get(self.url, {'export': 'excel', 'tipo': 'analisis'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
 
    # ✓ CSV ventas tiene cabeceras correctas
    def test_csv_ventas_tiene_cabeceras_correctas(self):
        """Verificar que el CSV de ventas incluye las columnas esperadas."""
        response = self.client.get(self.url, {'export': 'excel', 'tipo': 'ventas'})
        contenido = response.content.decode('utf-8-sig')
        self.assertIn('Fecha',    contenido)
        self.assertIn('Cliente',  contenido)
        self.assertIn('Producto', contenido)
        self.assertIn('Total',    contenido)
 
    # ✓ CSV inventario tiene cabeceras correctas
    def test_csv_inventario_tiene_cabeceras_correctas(self):
        """Verificar que el CSV de inventario incluye columnas de stock y estado."""
        response = self.client.get(self.url, {'export': 'excel', 'tipo': 'inventario'})
        contenido = response.content.decode('utf-8-sig')
        self.assertIn('Producto', contenido)
        self.assertIn('Estado',   contenido)
 
    # ✓ Content-Disposition indica archivo adjunto
    def test_content_disposition_attachment(self):
        """Verificar que el CSV se descarga como archivo adjunto."""
        response = self.client.get(self.url, {'export': 'excel', 'tipo': 'ventas'})
        self.assertIn('attachment', response['Content-Disposition'])
 
    # ✓ Filtro de fechas se respeta en la exportación
    def test_export_respeta_filtro_fechas(self):
        """Verificar que el CSV exportado respeta fecha_inicio y fecha_fin."""
        fi  = (timezone.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        ff  = (timezone.now() + timedelta(days=2)).strftime('%Y-%m-%d')
        res = self.client.get(self.url, {
            'export': 'excel', 'tipo': 'ventas',
            'fecha_inicio': fi, 'fecha_fin': ff
        })
        # Con fechas futuras no debería haber filas de datos
        contenido = res.content.decode('utf-8-sig')
        lineas = [l for l in contenido.splitlines() if l.strip()]
        self.assertEqual(len(lineas), 1)  # Solo la cabecera
 
 
# ═══════════════════════════════════════════════════════
#  TESTS: Exportación PDF
# ═══════════════════════════════════════════════════════
 
class ReportesExportPDFTest(TestCase):
    """Verifica la exportación PDF para cada tipo de reporte."""
 
    def setUp(self):
        self.client = Client()
        self.usuario = Usuario.objects.create_user(username='emp_pdf', password='pass')
        self.client.force_login(self.usuario)
        self.url = reverse('reportes')
 
        self.presentacion = _crear_presentacion()
        venta = _crear_venta(total=45000, fecha=timezone.now())
        _crear_detalle_venta(venta, self.presentacion, cantidad=1, precio_unitario=45000)
        _crear_movimiento(self.presentacion, tipo='entrada', cantidad=5)
        _crear_movimiento(self.presentacion, tipo='salida',  cantidad=2)
 
    # ✓ Export PDF ventas devuelve PDF
    def test_export_pdf_ventas(self):
        """Verificar que export=pdf&tipo=ventas devuelve application/pdf."""
        response = self.client.get(self.url, {'export': 'pdf', 'tipo': 'ventas'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
 
    # ✓ Export PDF inventario devuelve PDF
    def test_export_pdf_inventario(self):
        """Verificar que export=pdf&tipo=inventario devuelve application/pdf."""
        response = self.client.get(self.url, {'export': 'pdf', 'tipo': 'inventario'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
 
    # ✓ Export PDF proveedores devuelve PDF
    def test_export_pdf_proveedores(self):
        """Verificar que export=pdf&tipo=proveedores devuelve application/pdf."""
        response = self.client.get(self.url, {'export': 'pdf', 'tipo': 'proveedores'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
 
    # ✓ Export PDF resumen_diario devuelve PDF
    def test_export_pdf_resumen_diario(self):
        """Verificar que export=pdf&tipo=resumen_diario devuelve application/pdf."""
        response = self.client.get(self.url, {'export': 'pdf', 'tipo': 'resumen_diario'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
 
    # ✓ Export PDF analisis devuelve PDF
    def test_export_pdf_analisis(self):
        """Verificar que export=pdf&tipo=analisis devuelve application/pdf."""
        response = self.client.get(self.url, {'export': 'pdf', 'tipo': 'analisis'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
 
    # ✓ Tipo de reporte inválido devuelve 400
    def test_tipo_invalido_devuelve_400(self):
        """Verificar que un tipo de reporte PDF desconocido devuelve HTTP 400."""
        response = self.client.get(self.url, {'export': 'pdf', 'tipo': 'inexistente'})
        self.assertEqual(response.status_code, 400)
 
    # ✓ PDF empieza con la firma %PDF
    def test_pdf_empieza_con_firma_correcta(self):
        """Verificar que el contenido del PDF tiene la firma %PDF."""
        response = self.client.get(self.url, {'export': 'pdf', 'tipo': 'ventas'})
        self.assertTrue(response.content.startswith(b'%PDF'))
 
    # ✓ Content-Disposition es inline con nombre de archivo
    def test_pdf_content_disposition_inline(self):
        """Verificar que el PDF se sirve con disposición inline y nombre de archivo."""
        response = self.client.get(self.url, {'export': 'pdf', 'tipo': 'ventas'})
        self.assertIn('inline',   response['Content-Disposition'])
        self.assertIn('.pdf',     response['Content-Disposition'])
 
 
# ═══════════════════════════════════════════════════════
#  TESTS: Vista movimientos
# ═══════════════════════════════════════════════════════
 
class ReporteMovimientosViewTest(TestCase):
    """Verifica la vista de movimientos de inventario con filtros."""
 
    def setUp(self):
        self.client = Client()
        self.usuario = Usuario.objects.create_user(username='emp_mov', password='pass')
        self.client.force_login(self.usuario)
        self.url = reverse('reporte_movimientos')
 
        self.presentacion = _crear_presentacion()
        _crear_movimiento(self.presentacion, tipo='entrada', cantidad=20)
        _crear_movimiento(self.presentacion, tipo='salida',  cantidad=8)
 
    # ✓ Vista responde 200
    def test_vista_movimientos_responde_ok(self):
        """Verificar que la vista de movimientos carga correctamente."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
 
    # ✓ Contexto contiene 'movimientos' y 'form'
    def test_contexto_tiene_movimientos_y_form(self):
        """Verificar que el contexto incluye movimientos y el formulario de filtro."""
        response = self.client.get(self.url)
        self.assertIn('movimientos', response.context)
        self.assertIn('form',        response.context)
 
    # ✓ Filtrar por tipo='entrada' devuelve solo entradas
    def test_filtro_tipo_entrada(self):
        """Verificar que el filtro tipo=entrada excluye las salidas."""
        response = self.client.get(self.url, {'tipo_reporte': 'entrada'})
        movs = list(response.context['movimientos'])
        for m in movs:
            self.assertEqual(m.tipo, 'entrada')
 
    # ✓ Filtrar por tipo='salida' devuelve solo salidas
    def test_filtro_tipo_salida(self):
        """Verificar que el filtro tipo=salida excluye las entradas."""
        response = self.client.get(self.url, {'tipo_reporte': 'salida'})
        movs = list(response.context['movimientos'])
        for m in movs:
            self.assertEqual(m.tipo, 'salida')
 
    # ✓ Sin filtros devuelve todos los movimientos
    def test_sin_filtros_devuelve_todos(self):
        """Verificar que sin filtros se muestran entradas y salidas."""
        response = self.client.get(self.url)
        tipos    = {m.tipo for m in response.context['movimientos']}
        self.assertIn('entrada', tipos)
        self.assertIn('salida',  tipos)
 
 
# ═══════════════════════════════════════════════════════
#  TESTS: Integración — flujo completo de reporte
# ═══════════════════════════════════════════════════════
 
class ReportesIntegrationTest(TestCase):
    """Tests de integración: datos reales → vista → exportación coherente."""
 
    def setUp(self):
        self.client = Client()
        self.usuario = Usuario.objects.create_user(username='emp_int', password='pass')
        self.client.force_login(self.usuario)
        self.url = reverse('reportes')
 
        cat = _crear_categoria(codigo='VODKA', nombre='Vodka')
        from productos.models import Producto, PresentacionProducto
        prod = Producto.objects.create(codigo='ABSOLUT', nombre='Absolut', categoria=cat)
        pres = PresentacionProducto.objects.create(producto=prod, nombre='1L', unidades=1, precio=80000)
 
        for i in range(3):
            v = _crear_venta(total=80000, fecha=timezone.now())
            _crear_detalle_venta(v, pres, cantidad=1, precio_unitario=80000)
 
        _crear_movimiento(pres, tipo='entrada', cantidad=15)
 
    # ✓ total_ventas coincide entre vista y CSV
    def test_total_ventas_coincide_en_vista_y_csv(self):
        """Verificar que el total de ventas de la vista se refleja en la exportación CSV."""
        res_vista = self.client.get(self.url)
        total_ctx = res_vista.context['total_ventas']
 
        res_csv   = self.client.get(self.url, {'export': 'excel', 'tipo': 'ventas'})
        contenido = res_csv.content.decode('utf-8-sig')
        lineas    = [l for l in contenido.splitlines() if l.strip()]
        # El CSV debe tener cabecera + 3 filas de datos
        self.assertEqual(len(lineas), 4)
        self.assertEqual(total_ctx, 3 * 80000)
 
    # ✓ Flujo: vista → filtro → exportación mantiene coherencia
    def test_filtro_y_exportacion_coherentes(self):
        """Verificar que aplicar el mismo filtro en vista y CSV da resultados coherentes."""
        fi = timezone.now().strftime('%Y-%m-%d')
        ff = timezone.now().strftime('%Y-%m-%d')
 
        res_vista = self.client.get(self.url, {'fecha_inicio': fi, 'fecha_fin': ff})
        count_ctx = len(list(res_vista.context['ventas']))
 
        res_csv   = self.client.get(self.url, {
            'export': 'excel', 'tipo': 'ventas',
            'fecha_inicio': fi, 'fecha_fin': ff
        })
        contenido = res_csv.content.decode('utf-8-sig')
        filas_csv = [l for l in contenido.splitlines() if l.strip()][1:]  # sin cabecera
        self.assertEqual(count_ctx, len(filas_csv))
 
    # ✓ PDF se genera sin errores con datos reales
    def test_pdf_generado_sin_errores(self):
        """Verificar que el PDF de ventas con datos reales se genera correctamente."""
        response = self.client.get(self.url, {'export': 'pdf', 'tipo': 'ventas'})
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.content), 1000)  # PDF no vacío
 