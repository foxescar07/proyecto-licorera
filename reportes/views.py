from django.shortcuts import render
from django.utils import timezone
from django.core.paginator import Paginator
from ventas.models import Venta, DetalleVenta
from productos.models import Producto
from productos.models import Inventario
from .forms import FiltroReporteForm
import json
import zoneinfo
from django.core.serializers.json import DjangoJSONEncoder
ZONA_COLOMBIA = zoneinfo.ZoneInfo('America/Bogota')


def index_reportes(request):
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin    = request.GET.get('fecha_fin')
    cliente_q    = request.GET.get('cliente')
    producto_q   = request.GET.get('producto')

    ventas_qs = Venta.objects.prefetch_related(
        'detalles__producto',
        'detalles__presentacion'
    ).all().order_by('-fecha')

    if fecha_inicio:
        ventas_qs = ventas_qs.filter(fecha__date__gte=fecha_inicio)
    if fecha_fin:
        ventas_qs = ventas_qs.filter(fecha__date__lte=fecha_fin)
    if cliente_q:
        ventas_qs = ventas_qs.filter(cliente__icontains=cliente_q).distinct()
    if producto_q:
        ventas_qs = ventas_qs.filter(
            detalles__producto__nombre__icontains=producto_q
        ).distinct()

    paginator   = Paginator(ventas_qs, 10)
    page_number = request.GET.get('page', 1)
    page_obj    = paginator.get_page(page_number)

    ventas_todas = ventas_qs

    productos   = Producto.objects.all().order_by('nombre')
    proveedores = [
        {"nombre_contacto": "Carlos Mendoza", "nombre_empresa": "Licores del Caribe S.A.S.", "telefono": "300 456 7890", "email": "carlos.mendoza@licorescaribe.com"},
        {"nombre_contacto": "Ana María Gómez", "nombre_empresa": "Distribuidora El Brindis", "telefono": "315 987 6543", "email": "contacto@elbrindis.com"},
        {"nombre_contacto": "Juan Fernando Ruiz", "nombre_empresa": "Cervecerías Unidas", "telefono": "310 456 1234", "email": "jruiz@cerveceriasunidas.co"},
        {"nombre_contacto": "Patricia Lara", "nombre_empresa": "Importaciones Premium Ltda.", "telefono": "312 789 4561", "email": "plara@premiumimports.com"},
        {"nombre_contacto": "Roberto Díaz", "nombre_empresa": "Bodegas de la Sabana", "telefono": "320 123 7894", "email": "rdiaz@bodegassabana.com"}
    ]

    total_ventas    = sum(v.total_venta for v in ventas_todas)
    total_productos = sum(det.cantidad for v in ventas_todas for det in v.detalles.all())
    total_clientes  = ventas_todas.values('cliente').distinct().count()

    total_registrados = productos.count()
    total_en_stock    = sum(1 for p in productos if getattr(p, 'cantidad_disponible', 0) > 10)
    total_stock_bajo  = sum(1 for p in productos if 0 < getattr(p, 'cantidad_disponible', 0) <= 10)
    total_agotados    = sum(1 for p in productos if getattr(p, 'cantidad_disponible', 0) == 0)

    entradas = (
        Inventario.objects
        .filter(tipo='entrada')
        .select_related('producto')
        .order_by('-fecha_actualizada')
    )
    salidas = (
        Inventario.objects
        .filter(tipo='salida')
        .select_related('producto')
        .order_by('-fecha_actualizada')
    )

    hoy = timezone.now().astimezone(ZONA_COLOMBIA).date()

    ventas_hoy = Venta.objects.prefetch_related(
        'detalles__producto',
        'detalles__presentacion'
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
        'ventas':             page_obj,
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
        'cliente_q':          cliente_q or '',
        'producto_q':         producto_q or '',
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


def reporte_movimientos(request):
    form = FiltroReporteForm(request.GET or None)
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
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'reportes/movimientos.html', {
        'form': form,
        'movimientos': page_obj,
    })