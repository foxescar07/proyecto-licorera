from django.shortcuts import render
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import HttpResponse
from ventas.models import Venta, DetalleVenta
from productos.models import Producto
from productos.models import Inventario
from .forms import FiltroReporteForm
import json
import zoneinfo
import csv
from django.core.serializers.json import DjangoJSONEncoder

# ReportLab
from reportlab.lib.pagesizes import letter, landscape # type: ignore
from reportlab.lib import colors # type: ignore
from reportlab.lib.units import cm # type: ignore
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable # type: ignore
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle # type: ignore
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT # type: ignore
from io import BytesIO

ZONA_COLOMBIA = zoneinfo.ZoneInfo('America/Bogota')

# ─────────────────────────────────────────────
#  COLORES CORPORATIVOS CYS
# ─────────────────────────────────────────────
COLOR_PRIMARIO   = colors.HexColor('#1A2B3C')   # azul oscuro
COLOR_ACENTO     = colors.HexColor('#4DA8DA')   # azul claro
COLOR_VERDE      = colors.HexColor('#2ecc71')
COLOR_AMARILLO   = colors.HexColor('#f1c40f')
COLOR_ROJO       = colors.HexColor('#e74c3c')
COLOR_GRIS_FILA  = colors.HexColor('#F0F4F8')
COLOR_BLANCO     = colors.white
COLOR_TEXTO      = colors.HexColor('#1A2B3C')


# ─────────────────────────────────────────────
#  HELPER: construir PDF con encabezado estándar
# ─────────────────────────────────────────────
def _build_pdf(titulo, subtitulo, elementos, orientacion='portrait'):
    buffer = BytesIO()
    pagesize = landscape(letter) if orientacion == 'landscape' else letter
    doc = SimpleDocTemplate(
        buffer,
        pagesize=pagesize,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=1.5*cm,   bottomMargin=1.5*cm,
    )

    styles = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle(
        'Titulo', parent=styles['Title'],
        fontSize=18, textColor=COLOR_PRIMARIO,
        spaceAfter=2, alignment=TA_LEFT,
    )
    estilo_subtitulo = ParagraphStyle(
        'Sub', parent=styles['Normal'],
        fontSize=9, textColor=colors.HexColor('#6B8CA0'),
        spaceAfter=8, alignment=TA_LEFT,
    )

    historia = []
    historia.append(Paragraph("CYS Ltda.", estilo_titulo))
    historia.append(Paragraph(titulo, ParagraphStyle(
        'T2', parent=styles['Heading1'],
        fontSize=13, textColor=COLOR_ACENTO, spaceAfter=2,
    )))
    historia.append(Paragraph(subtitulo, estilo_subtitulo))
    historia.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_ACENTO, spaceAfter=10))
    historia.extend(elementos)

    doc.build(historia)
    buffer.seek(0)
    return buffer


def _estilo_tabla_base(num_cols, col_cabecera=True):
    """Devuelve un TableStyle estándar CYS."""
    estilo = [
        # Cabecera
        ('BACKGROUND',    (0, 0), (-1, 0), COLOR_PRIMARIO),
        ('TEXTCOLOR',     (0, 0), (-1, 0), COLOR_BLANCO),
        ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, 0), 9),
        ('ALIGN',         (0, 0), (-1, 0), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 7),
        ('TOPPADDING',    (0, 0), (-1, 0), 7),
        # Cuerpo
        ('FONTNAME',      (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE',      (0, 1), (-1, -1), 8),
        ('ALIGN',         (0, 1), (-1, -1), 'LEFT'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [COLOR_BLANCO, COLOR_GRIS_FILA]),
        ('GRID',          (0, 0), (-1, -1), 0.4, colors.HexColor('#D0DCE8')),
        ('BOX',           (0, 0), (-1, -1), 1,   COLOR_ACENTO),
    ]
    return TableStyle(estilo)


def _kpi_table(items):
    """
    items = [('Label', 'Valor', color_hex_str), ...]
    Devuelve una tabla de KPIs horizontal.
    """
    styles = getSampleStyleSheet()
    filas_label = []
    filas_val   = []
    for label, valor, color_hex in items:
        filas_label.append(Paragraph(
            f'<font color="{color_hex}"><b>{valor}</b></font>',
            ParagraphStyle('kv', fontSize=14, alignment=TA_CENTER)
        ))
        filas_val.append(Paragraph(
            label,
            ParagraphStyle('kl', fontSize=7, textColor=colors.HexColor('#6B8CA0'), alignment=TA_CENTER)
        ))

    data = [filas_label, filas_val]
    col_w = [4*cm] * len(items)
    t = Table(data, colWidths=col_w)
    t.setStyle(TableStyle([
        ('BOX',           (0, 0), (-1, -1), 1,   colors.HexColor('#D0DCE8')),
        ('INNERGRID',     (0, 0), (-1, -1), 0.4, colors.HexColor('#D0DCE8')),
        ('BACKGROUND',    (0, 0), (-1, -1), COLOR_GRIS_FILA),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    return t


# ═══════════════════════════════════════════════════════
#  GENERADORES PDF POR TIPO
# ═══════════════════════════════════════════════════════

def _pdf_ventas(ventas_qs, fecha_inicio, fecha_fin):
    styles = getSampleStyleSheet()
    elementos = []

    # KPIs
    total_v = sum(v.total_venta for v in ventas_qs)
    total_u = sum(det.cantidad for v in ventas_qs for det in v.detalles.all())
    total_c = ventas_qs.values('cliente').distinct().count()
    elementos.append(_kpi_table([
        ('Total Ventas',    f'${total_v:,.0f}', '#2ecc71'),
        ('Unidades',        str(total_u),        '#4DA8DA'),
        ('Clientes únicos', str(total_c),        '#f1c40f'),
    ]))
    elementos.append(Spacer(1, 12))

    # Tabla principal
    cabecera = [['#', 'Fecha', 'Cliente', 'Producto', 'Cant.', 'Precio Unit.', 'Total']]
    filas = cabecera
    contador = 1
    for v in ventas_qs:
        for det in v.detalles.all():
            filas.append([
                str(contador),
                v.fecha.astimezone(ZONA_COLOMBIA).strftime("%Y-%m-%d"),
                str(v.cliente),
                det.producto.nombre,
                str(det.cantidad),
                f'${float(det.precio_unitario):,.0f}',
                f'${float(det.subtotal()):,.0f}',
            ])
            contador += 1

    if len(filas) == 1:
        filas.append(['', 'Sin ventas en el período seleccionado', '', '', '', '', ''])

    col_w = [1*cm, 2.5*cm, 4*cm, 5*cm, 1.5*cm, 3*cm, 3*cm]
    t = Table(filas, colWidths=col_w, repeatRows=1)
    estilo = _estilo_tabla_base(7)
    # Columnas numéricas alineadas a la derecha
    estilo.add('ALIGN', (4, 1), (6, -1), 'RIGHT')
    t.setStyle(estilo)
    elementos.append(t)

    subtitulo = f"Período: {fecha_inicio or 'Todo'} → {fecha_fin or 'Todo'}  |  Generado: {timezone.now().astimezone(ZONA_COLOMBIA).strftime('%d/%m/%Y %H:%M')}"
    return _build_pdf("Historial de Ventas", subtitulo, elementos, orientacion='landscape')


def _pdf_inventario(productos_qs, entradas_qs, salidas_qs):
    elementos = []
    styles = getSampleStyleSheet()

    total_reg   = productos_qs.count()
    en_stock    = sum(1 for p in productos_qs if getattr(p, 'cantidad_disponible', 0) > 10)
    stock_bajo  = sum(1 for p in productos_qs if 0 < getattr(p, 'cantidad_disponible', 0) <= 10)
    agotados    = sum(1 for p in productos_qs if getattr(p, 'cantidad_disponible', 0) == 0)

    elementos.append(_kpi_table([
        ('Registrados', str(total_reg),  '#4DA8DA'),
        ('En stock',    str(en_stock),   '#2ecc71'),
        ('Stock bajo',  str(stock_bajo), '#f1c40f'),
        ('Agotados',    str(agotados),   '#e74c3c'),
    ]))
    elementos.append(Spacer(1, 12))

    # ── Tabla Stock ──
    elementos.append(Paragraph("Estado de Stock", ParagraphStyle(
        'sh', fontSize=10, textColor=COLOR_PRIMARIO, fontName='Helvetica-Bold', spaceAfter=4)))

    filas = [['#', 'Producto', 'Stock', 'Estado']]
    for i, p in enumerate(productos_qs, 1):
        qty = getattr(p, 'cantidad_disponible', 0)
        if qty == 0:
            estado, color = 'Agotado',    COLOR_ROJO
        elif qty <= 10:
            estado, color = 'Stock bajo', COLOR_AMARILLO
        else:
            estado, color = 'En stock',   COLOR_VERDE
        filas.append([
            str(i), p.nombre, str(qty),
            Paragraph(f'<font color="{color.hexval()}"><b>{estado}</b></font>',
                      ParagraphStyle('e', fontSize=8)),
        ])

    col_w = [1*cm, 9*cm, 2.5*cm, 3*cm]
    t = Table(filas, colWidths=col_w, repeatRows=1)
    t.setStyle(_estilo_tabla_base(4))
    elementos.append(t)
    elementos.append(Spacer(1, 14))

    # ── Tabla Entradas ──
    elementos.append(Paragraph("Entradas de Inventario", ParagraphStyle(
        'sh2', fontSize=10, textColor=COLOR_VERDE, fontName='Helvetica-Bold', spaceAfter=4)))

    filas_e = [['#', 'Producto', 'Cantidad', 'Motivo', 'Fecha']]
    for i, e in enumerate(entradas_qs, 1):
        filas_e.append([
            str(i), e.producto.nombre, f'+{e.cantidad}',
            e.motivo or '—',
            e.fecha_actualizada.astimezone(ZONA_COLOMBIA).strftime("%d/%m/%Y %H:%M"),
        ])
    if len(filas_e) == 1:
        filas_e.append(['', 'Sin entradas registradas', '', '', ''])

    col_w_e = [1*cm, 7*cm, 2.5*cm, 4*cm, 3.5*cm]
    te = Table(filas_e, colWidths=col_w_e, repeatRows=1)
    estilo_e = _estilo_tabla_base(5)
    estilo_e.add('TEXTCOLOR', (2, 1), (2, -1), COLOR_VERDE)
    estilo_e.add('FONTNAME',  (2, 1), (2, -1), 'Helvetica-Bold')
    te.setStyle(estilo_e)
    elementos.append(te)
    elementos.append(Spacer(1, 14))

    # ── Tabla Salidas ──
    elementos.append(Paragraph("Salidas de Inventario", ParagraphStyle(
        'sh3', fontSize=10, textColor=COLOR_ROJO, fontName='Helvetica-Bold', spaceAfter=4)))

    filas_s = [['#', 'Producto', 'Cantidad', 'Motivo', 'Fecha']]
    for i, s in enumerate(salidas_qs, 1):
        filas_s.append([
            str(i), s.producto.nombre, f'-{s.cantidad}',
            s.motivo or '—',
            s.fecha_actualizada.astimezone(ZONA_COLOMBIA).strftime("%d/%m/%Y %H:%M"),
        ])
    if len(filas_s) == 1:
        filas_s.append(['', 'Sin salidas registradas', '', '', ''])

    col_w_s = [1*cm, 7*cm, 2.5*cm, 4*cm, 3.5*cm]
    ts = Table(filas_s, colWidths=col_w_s, repeatRows=1)
    estilo_s = _estilo_tabla_base(5)
    estilo_s.add('TEXTCOLOR', (2, 1), (2, -1), COLOR_ROJO)
    estilo_s.add('FONTNAME',  (2, 1), (2, -1), 'Helvetica-Bold')
    ts.setStyle(estilo_s)
    elementos.append(ts)

    subtitulo = f"Generado: {timezone.now().astimezone(ZONA_COLOMBIA).strftime('%d/%m/%Y %H:%M')}"
    return _build_pdf("Reporte de Inventario", subtitulo, elementos)


def _pdf_proveedores(proveedores_list):
    elementos = []

    elementos.append(_kpi_table([
        ('Total Proveedores', str(len(proveedores_list)), '#5DCAA5'),
        ('Estado',            'Activos',                  '#4DA8DA'),
    ]))
    elementos.append(Spacer(1, 12))

    filas = [['#', 'Contacto', 'Empresa', 'Teléfono', 'Correo']]
    for i, p in enumerate(proveedores_list, 1):
        filas.append([
            str(i),
            p['nombre_contacto'],
            p['nombre_empresa'],
            p['telefono'],
            p['email'],
        ])

    col_w = [1*cm, 4*cm, 5.5*cm, 3.5*cm, 5.5*cm]
    t = Table(filas, colWidths=col_w, repeatRows=1)
    t.setStyle(_estilo_tabla_base(5))
    elementos.append(t)

    subtitulo = f"Generado: {timezone.now().astimezone(ZONA_COLOMBIA).strftime('%d/%m/%Y %H:%M')}"
    return _build_pdf("Reporte de Proveedores", subtitulo, elementos)


def _pdf_resumen_diario(hoy, ventas_hoy, entradas_hoy, salidas_hoy,
                        ingresos_hoy, total_entradas_hoy, total_salidas_hoy,
                        top_productos_hoy):
    elementos = []
    styles = getSampleStyleSheet()

    elementos.append(_kpi_table([
        ('Ingresos hoy',  f'${ingresos_hoy:,.0f}',    '#2ecc71'),
        ('Ventas hoy',    str(len(ventas_hoy)),         '#4DA8DA'),
        ('Und. Entrada',  str(total_entradas_hoy),      '#f1c40f'),
        ('Und. Salida',   str(total_salidas_hoy),       '#e74c3c'),
    ]))
    elementos.append(Spacer(1, 12))

    def seccion(titulo, color_hex):
        elementos.append(Paragraph(titulo, ParagraphStyle(
            'sec', fontSize=10, textColor=colors.HexColor(color_hex),
            fontName='Helvetica-Bold', spaceAfter=4, spaceBefore=10)))

    # ── Ventas del día ──
    seccion("Ventas del día", '#4DA8DA')
    filas_v = [['#', 'Cliente', 'Producto', 'Cant.', 'Total', 'Hora']]
    cont = 1
    for v in ventas_hoy:
        for det in v.detalles.all():
            filas_v.append([
                str(cont), str(v.cliente), det.producto.nombre,
                str(det.cantidad), f'${float(det.subtotal()):,.0f}',
                v.fecha.astimezone(ZONA_COLOMBIA).strftime("%H:%M"),
            ])
            cont += 1
    if len(filas_v) == 1:
        filas_v.append(['', 'Sin ventas hoy', '', '', '', ''])

    col_v = [1*cm, 4.5*cm, 5*cm, 1.5*cm, 3*cm, 2*cm]
    tv = Table(filas_v, colWidths=col_v, repeatRows=1)
    estilo_v = _estilo_tabla_base(6)
    estilo_v.add('ALIGN', (4, 1), (4, -1), 'RIGHT')
    tv.setStyle(estilo_v)
    elementos.append(tv)

    # ── Entradas del día ──
    seccion("Entradas del día", '#2ecc71')
    filas_e = [['#', 'Producto', 'Cantidad', 'Motivo', 'Fecha']]
    for i, e in enumerate(entradas_hoy, 1):
        filas_e.append([str(i), e.producto.nombre, f'+{e.cantidad}',
                         e.motivo or '—',
                         e.fecha_actualizada.astimezone(ZONA_COLOMBIA).strftime("%d/%m/%Y %H:%M")])
    if len(filas_e) == 1:
        filas_e.append(['', 'Sin entradas hoy', '', '', ''])
    col_e = [1*cm, 6*cm, 2.5*cm, 4*cm, 3.5*cm]
    te = Table(filas_e, colWidths=col_e, repeatRows=1)
    te.setStyle(_estilo_tabla_base(5))
    elementos.append(te)

    # ── Salidas del día ──
    seccion("Salidas del día", '#e74c3c')
    filas_s = [['#', 'Producto', 'Cantidad', 'Motivo', 'Fecha']]
    for i, s in enumerate(salidas_hoy, 1):
        filas_s.append([str(i), s.producto.nombre, f'-{s.cantidad}',
                         s.motivo or '—',
                         s.fecha_actualizada.astimezone(ZONA_COLOMBIA).strftime("%d/%m/%Y %H:%M")])
    if len(filas_s) == 1:
        filas_s.append(['', 'Sin salidas hoy', '', '', ''])
    col_s = [1*cm, 6*cm, 2.5*cm, 4*cm, 3.5*cm]
    ts = Table(filas_s, colWidths=col_s, repeatRows=1)
    ts.setStyle(_estilo_tabla_base(5))
    elementos.append(ts)

    # ── Top productos del día ──
    if top_productos_hoy:
        seccion("Top productos del día", '#7F77DD')
        filas_t = [['#', 'Producto', 'Unidades vendidas', 'Total generado']]
        for i, (nombre, datos) in enumerate(top_productos_hoy, 1):
            filas_t.append([str(i), nombre, str(datos['cantidad']),
                             f'${datos["subtotal"]:,.0f}'])
        col_t = [1*cm, 8*cm, 4*cm, 4*cm]
        tt = Table(filas_t, colWidths=col_t, repeatRows=1)
        tt.setStyle(_estilo_tabla_base(4))
        elementos.append(tt)

    subtitulo = f"Fecha: {hoy.strftime('%d/%m/%Y')}  |  Generado: {timezone.now().astimezone(ZONA_COLOMBIA).strftime('%H:%M')}"
    return _build_pdf("Resumen Diario", subtitulo, elementos)


def _pdf_analisis_ventas(ventas_qs, total_ventas, total_productos, total_clientes, top_productos_hoy):
    elementos = []
    styles = getSampleStyleSheet()

    elementos.append(_kpi_table([
        ('Ventas Totales', f'${total_ventas:,.0f}', '#2ecc71'),
        ('Uds. Vendidas',  str(total_productos),    '#4DA8DA'),
        ('Clientes',       str(total_clientes),     '#f1c40f'),
    ]))
    elementos.append(Spacer(1, 12))

    # ── Ventas por fecha ──
    elementos.append(Paragraph("Ventas por fecha", ParagraphStyle(
        'av1', fontSize=10, textColor=colors.HexColor('#E8834A'),
        fontName='Helvetica-Bold', spaceAfter=4)))

    filas = [['Fecha', 'Cliente', 'Producto', 'Cantidad', 'Total']]
    for v in ventas_qs:
        for det in v.detalles.all():
            filas.append([
                v.fecha.astimezone(ZONA_COLOMBIA).strftime("%d/%m/%Y"),
                str(v.cliente),
                det.producto.nombre,
                str(det.cantidad),
                f'${float(det.subtotal()):,.0f}',
            ])
    if len(filas) == 1:
        filas.append(['Sin ventas registradas', '', '', '', ''])

    col_w = [2.5*cm, 4.5*cm, 6*cm, 2*cm, 3*cm]
    t = Table(filas, colWidths=col_w, repeatRows=1)
    estilo = _estilo_tabla_base(5)
    estilo.add('ALIGN', (4, 1), (4, -1), 'RIGHT')
    t.setStyle(estilo)
    elementos.append(t)
    elementos.append(Spacer(1, 14))

    # ── Top productos del día ──
    elementos.append(Paragraph("Top productos del día más vendidos", ParagraphStyle(
        'av2', fontSize=10, textColor=colors.HexColor('#5DCAA5'),
        fontName='Helvetica-Bold', spaceAfter=4)))

    filas_top = [['#', 'Producto', 'Unidades vendidas', 'Total generado']]
    for i, (nombre, datos) in enumerate(top_productos_hoy, 1):
        filas_top.append([str(i), nombre, str(datos['cantidad']),
                           f'${datos["subtotal"]:,.0f}'])
    if len(filas_top) == 1:
        filas_top.append(['', 'Sin datos de productos hoy', '', ''])

    col_top = [1*cm, 9*cm, 4*cm, 4*cm]
    tt = Table(filas_top, colWidths=col_top, repeatRows=1)
    tt.setStyle(_estilo_tabla_base(4))
    elementos.append(tt)

    subtitulo = f"Generado: {timezone.now().astimezone(ZONA_COLOMBIA).strftime('%d/%m/%Y %H:%M')}"
    return _build_pdf("Análisis de Ventas", subtitulo, elementos, orientacion='landscape')


# ═══════════════════════════════════════════════════════
#  VISTA PRINCIPAL
# ═══════════════════════════════════════════════════════

def index_reportes(request):
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin    = request.GET.get('fecha_fin')
    per_page     = request.GET.get('per_page', '10')

    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 10

    ventas_qs = Venta.objects.prefetch_related(
        'detalles__producto',
        'detalles__presentacion'
    ).all().order_by('-fecha')

    if fecha_inicio:
        ventas_qs = ventas_qs.filter(fecha__date__gte=fecha_inicio)
    if fecha_fin:
        ventas_qs = ventas_qs.filter(fecha__date__lte=fecha_fin)

    paginator   = Paginator(ventas_qs, per_page)
    page_number = request.GET.get('page', 1)
    page_obj    = paginator.get_page(page_number)

    proveedores_data_list = [
        {"nombre_contacto": "Carlos Mendoza",      "nombre_empresa": "Licores del Caribe S.A.S.",    "telefono": "300 456 7890", "email": "carlos.mendoza@licorescaribe.com"},
        {"nombre_contacto": "Ana María Gómez",     "nombre_empresa": "Distribuidora El Brindis",      "telefono": "315 987 6543", "email": "contacto@elbrindis.com"},
        {"nombre_contacto": "Juan Fernando Ruiz",  "nombre_empresa": "Cervecerías Unidas",            "telefono": "310 456 1234", "email": "jruiz@cerveceriasunidas.co"},
        {"nombre_contacto": "Patricia Lara",        "nombre_empresa": "Importaciones Premium Ltda.",  "telefono": "312 789 4561", "email": "plara@premiumimports.com"},
        {"nombre_contacto": "Roberto Díaz",         "nombre_empresa": "Bodegas de la Sabana",         "telefono": "320 123 7894", "email": "rdiaz@bodegassabana.com"},
    ]

    # ─────────────────────────────────────────────────────
    #  EXPORTACIONES
    # ─────────────────────────────────────────────────────
    export_format = request.GET.get('export')

    if export_format in ('excel', 'pdf'):
        tipo = request.GET.get('tipo', 'ventas')

        # ── EXCEL (CSV) ──────────────────────────────────
        if export_format == 'excel':
            response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
            response['Content-Disposition'] = (
                f'attachment; filename="reporte_{tipo}_{timezone.now().strftime("%Y%m%d")}.csv"'
            )
            response.write(u'\ufeff'.encode('utf8'))
            writer = csv.writer(response)

            if tipo == 'ventas':
                writer.writerow(['Fecha', 'Cliente', 'Producto', 'Cantidad', 'Precio Unitario', 'Total'])
                for v in ventas_qs:
                    for det in v.detalles.all():
                        writer.writerow([
                            v.fecha.astimezone(ZONA_COLOMBIA).strftime("%Y-%m-%d %H:%M"),
                            v.cliente,
                            det.producto.nombre,
                            det.cantidad,
                            det.precio_unitario,
                            det.subtotal(),
                        ])

            elif tipo == 'inventario':
                writer.writerow(['Producto', 'Stock Disponible', 'Estado'])
                for p in Producto.objects.all().order_by('nombre'):
                    qty    = getattr(p, 'cantidad_disponible', 0)
                    estado = "En Stock" if qty > 10 else ("Bajo" if qty > 0 else "Agotado")
                    writer.writerow([p.nombre, qty, estado])

            elif tipo == 'proveedores':
                writer.writerow(['Contacto', 'Empresa', 'Teléfono', 'Email'])
                for p in proveedores_data_list:
                    writer.writerow([p['nombre_contacto'], p['nombre_empresa'],
                                     p['telefono'], p['email']])

            elif tipo == 'resumen_diario':
                hoy_exp = timezone.now().astimezone(ZONA_COLOMBIA).date()
                vh = Venta.objects.prefetch_related('detalles__producto').filter(fecha__date=hoy_exp)
                writer.writerow(['Tipo', 'Producto / Cliente', 'Cantidad', 'Total / Motivo', 'Hora'])
                for v in vh:
                    for det in v.detalles.all():
                        writer.writerow([
                            'Venta', f'{v.cliente} — {det.producto.nombre}',
                            det.cantidad, det.subtotal(),
                            v.fecha.astimezone(ZONA_COLOMBIA).strftime("%H:%M"),
                        ])
                mov_hoy = Inventario.objects.filter(fecha_actualizada__date=hoy_exp).select_related('producto')
                for m in mov_hoy:
                    writer.writerow([
                        m.tipo.capitalize(), m.producto.nombre,
                        m.cantidad, m.motivo or '—',
                        m.fecha_actualizada.astimezone(ZONA_COLOMBIA).strftime("%H:%M"),
                    ])

            elif tipo == 'analisis':
                writer.writerow(['Fecha', 'Cliente', 'Producto', 'Cantidad', 'Total'])
                for v in ventas_qs:
                    for det in v.detalles.all():
                        writer.writerow([
                            v.fecha.astimezone(ZONA_COLOMBIA).strftime("%Y-%m-%d"),
                            v.cliente, det.producto.nombre,
                            det.cantidad, det.subtotal(),
                        ])

            return response

        # ── PDF ──────────────────────────────────────────
        elif export_format == 'pdf':
            productos_qs = Producto.objects.all().order_by('nombre')
            hoy_pdf      = timezone.now().astimezone(ZONA_COLOMBIA).date()

            if tipo == 'ventas':
                buffer = _pdf_ventas(ventas_qs, fecha_inicio, fecha_fin)
                nombre = f"reporte_ventas_{timezone.now().strftime('%Y%m%d')}.pdf"

            elif tipo == 'inventario':
                entradas_qs = Inventario.objects.filter(tipo='entrada').select_related('producto').order_by('-fecha_actualizada')
                salidas_qs  = Inventario.objects.filter(tipo='salida').select_related('producto').order_by('-fecha_actualizada')
                buffer = _pdf_inventario(productos_qs, entradas_qs, salidas_qs)
                nombre = f"reporte_inventario_{timezone.now().strftime('%Y%m%d')}.pdf"

            elif tipo == 'proveedores':
                buffer = _pdf_proveedores(proveedores_data_list)
                nombre = f"reporte_proveedores_{timezone.now().strftime('%Y%m%d')}.pdf"

            elif tipo == 'resumen_diario':
                ventas_hoy_pdf    = Venta.objects.prefetch_related('detalles__producto', 'detalles__presentacion').filter(fecha__date=hoy_pdf).order_by('-fecha')
                ingresos_hoy_pdf  = sum(v.total_venta for v in ventas_hoy_pdf)
                mov_hoy           = Inventario.objects.filter(fecha_actualizada__date=hoy_pdf).select_related('producto')
                entradas_hoy_pdf  = mov_hoy.filter(tipo='entrada')
                salidas_hoy_pdf   = mov_hoy.filter(tipo='salida')
                total_ent_pdf     = sum(e.cantidad for e in entradas_hoy_pdf)
                total_sal_pdf     = sum(s.cantidad for s in salidas_hoy_pdf)

                # Top productos del día para PDF
                det_hoy = DetalleVenta.objects.filter(venta__fecha__date=hoy_pdf).select_related('producto')
                top_h   = {}
                for det in det_hoy:
                    n = det.producto.nombre
                    if n not in top_h:
                        top_h[n] = {'cantidad': 0, 'subtotal': 0}
                    top_h[n]['cantidad'] += det.cantidad
                    top_h[n]['subtotal'] += float(det.subtotal())
                top_h = sorted(top_h.items(), key=lambda x: x[1]['subtotal'], reverse=True)[:5]

                buffer = _pdf_resumen_diario(
                    hoy_pdf, ventas_hoy_pdf, entradas_hoy_pdf, salidas_hoy_pdf,
                    ingresos_hoy_pdf, total_ent_pdf, total_sal_pdf, top_h
                )
                nombre = f"resumen_diario_{hoy_pdf.strftime('%Y%m%d')}.pdf"

            elif tipo == 'analisis':
                total_v = sum(v.total_venta for v in ventas_qs)
                total_u = sum(det.cantidad for v in ventas_qs for det in v.detalles.all())
                total_c = ventas_qs.values('cliente').distinct().count()

                det_qs = DetalleVenta.objects.filter(venta__fecha__date=hoy_pdf).select_related('producto')
                top_h  = {}
                for det in det_qs:
                    n = det.producto.nombre
                    if n not in top_h:
                        top_h[n] = {'cantidad': 0, 'subtotal': 0}
                    top_h[n]['cantidad'] += det.cantidad
                    top_h[n]['subtotal'] += float(det.subtotal())
                top_h = sorted(top_h.items(), key=lambda x: x[1]['subtotal'], reverse=True)[:5]

                buffer = _pdf_analisis_ventas(ventas_qs, total_v, total_u, total_c, top_h)
                nombre = f"analisis_ventas_{timezone.now().strftime('%Y%m%d')}.pdf"

            else:
                return HttpResponse("Tipo de reporte PDF no reconocido.", status=400)

            response = HttpResponse(buffer, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{nombre}"'
            return response

    # ─────────────────────────────────────────────────────
    #  RENDER NORMAL
    # ─────────────────────────────────────────────────────
    ventas_todas = ventas_qs

    productos   = Producto.objects.all().order_by('nombre')
    proveedores = proveedores_data_list

    total_ventas    = sum(v.total_venta for v in ventas_todas)
    total_productos = sum(det.cantidad for v in ventas_todas for det in v.detalles.all())
    total_clientes  = ventas_todas.values('cliente').distinct().count()

    total_registrados = productos.count()
    total_en_stock    = sum(1 for p in productos if getattr(p, 'cantidad_disponible', 0) > 10)
    total_stock_bajo  = sum(1 for p in productos if 0 < getattr(p, 'cantidad_disponible', 0) <= 10)
    total_agotados    = sum(1 for p in productos if getattr(p, 'cantidad_disponible', 0) == 0)

    entradas = Inventario.objects.filter(tipo='entrada').select_related('producto').order_by('-fecha_actualizada')
    salidas  = Inventario.objects.filter(tipo='salida').select_related('producto').order_by('-fecha_actualizada')

    hoy = timezone.now().astimezone(ZONA_COLOMBIA).date()

    ventas_hoy = Venta.objects.prefetch_related(
        'detalles__producto', 'detalles__presentacion'
    ).filter(fecha__date=hoy).order_by('-fecha')

    ingresos_hoy = sum(v.total_venta for v in ventas_hoy)

    movimientos_hoy    = Inventario.objects.filter(fecha_actualizada__date=hoy).select_related('producto')
    entradas_hoy       = movimientos_hoy.filter(tipo='entrada')
    salidas_hoy        = movimientos_hoy.filter(tipo='salida')
    total_entradas_hoy = sum(e.cantidad for e in entradas_hoy)
    total_salidas_hoy  = sum(s.cantidad for s in salidas_hoy)

    productos_vendidos_hoy = (
        DetalleVenta.objects
        .filter(venta__fecha__date=hoy)
        .select_related('producto', 'presentacion', 'venta')
        .order_by('producto__nombre')
    )
    top_productos_hoy = {}
    for det in productos_vendidos_hoy:
        nombre = det.producto.nombre
        if nombre not in top_productos_hoy:
            top_productos_hoy[nombre] = {'cantidad': 0, 'subtotal': 0}
        top_productos_hoy[nombre]['cantidad'] += det.cantidad
        top_productos_hoy[nombre]['subtotal'] += float(det.subtotal())
    top_productos_hoy = sorted(
        top_productos_hoy.items(),
        key=lambda x: x[1]['subtotal'],
        reverse=True
    )[:5]

    ventas_data = []
    for v in ventas_todas:
        for det in v.detalles.all():
            ventas_data.append({
                "fecha":           v.fecha.astimezone(ZONA_COLOMBIA).strftime("%Y-%m-%d"),
                "hora":            v.fecha.astimezone(ZONA_COLOMBIA).strftime("%H:%M"),
                "cliente":         str(v.cliente),
                "producto":        det.producto.nombre,
                "presentacion":    det.presentacion.nombre if det.presentacion else "Unidad",
                "cantidad":        det.cantidad,
                "precio_unitario": float(det.precio_unitario),
                "subtotal":        float(det.subtotal()),
                "descuento":       float(v.descuento_porcentaje),
                "total_venta":     float(v.total_venta),
            })

    ventas_json = (
        json.dumps(ventas_data, cls=DjangoJSONEncoder)
        .replace('</script>', r'<\/script>')
        .replace('<!--',      r'<\!--')
    )

    return render(request, 'reportes.html', {
        'ventas':             ventas_todas,
        'page_obj':           page_obj,
        'paginator':          paginator,
        'total_ventas':       total_ventas,
        'total_productos':    total_productos,
        'total_clientes':     total_clientes,
        'productos':          productos,
        'proveedores':        proveedores,
        'total_registrados':  total_registrados,
        'total_en_stock':     total_en_stock,
        'total_stock_bajo':   total_stock_bajo,
        'total_agotados':     total_agotados,
        'entradas':           entradas,
        'salidas':            salidas,
        'fecha_inicio':       fecha_inicio or '',
        'fecha_fin':          fecha_fin or '',
        'per_page':           per_page,
        'hoy':                hoy,
        'ventas_hoy':         ventas_hoy,
        'ingresos_hoy':       ingresos_hoy,
        'entradas_hoy':       entradas_hoy,
        'salidas_hoy':        salidas_hoy,
        'total_entradas_hoy': total_entradas_hoy,
        'total_salidas_hoy':  total_salidas_hoy,
        'top_productos_hoy':  top_productos_hoy,
        'ventas_json':        ventas_json,
    })


# ═══════════════════════════════════════════════════════
#  VISTA MOVIMIENTOS
# ═══════════════════════════════════════════════════════

def reporte_movimientos(request):
    form        = FiltroReporteForm(request.GET or None)
    movimientos = Inventario.objects.select_related('producto').all().order_by('-fecha_actualizada')

    if form.is_valid():
        f_inicio = form.cleaned_data.get('fecha_inicio')
        f_fin    = form.cleaned_data.get('fecha_fin')
        tipo     = form.cleaned_data.get('tipo_reporte')

        if f_inicio:
            movimientos = movimientos.filter(fecha_actualizada__date__gte=f_inicio)
        if f_fin:
            movimientos = movimientos.filter(fecha_actualizada__date__lte=f_fin)
        if tipo and tipo != 'general':
            movimientos = movimientos.filter(tipo=tipo)

    paginator = Paginator(movimientos, 20)
    page_obj  = paginator.get_page(request.GET.get('page'))

    return render(request, 'reportes/movimientos.html', {
        'form':        form,
        'movimientos': page_obj,
    })