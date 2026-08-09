from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Sum, Q, Min, Max
from django.utils import timezone
from django.views.decorators.http import require_POST
from decimal import Decimal, InvalidOperation
from functools import wraps
import json
from django.urls import reverse

from .models import (
    Venta, DetalleVenta, AperturaCaja, CierreCaja,
    Devolucion, DetalleDevolucion, Cliente,
)
from .forms import VentaForm, DetalleVentaForm, DevolucionForm
from productos.models import Producto, Categoria, PresentacionProducto
from inventario.models import Inventario, Lote
from usuarios.models import Usuario

BILLETES_DENOM = [100000, 50000, 20000, 10000, 5000, 2000, 1000]
MONEDAS_DENOM  = [500, 200, 100, 50]
TODAS_DENOM    = BILLETES_DENOM + MONEDAS_DENOM

META_VENTA_DIARIA = 500000


# ════════════════════════════════════════
# DECORADOR
# ════════════════════════════════════════

def session_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('usuario_id'):
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


# ════════════════════════════════════════
# HELPERS GENERALES
# ════════════════════════════════════════

def _descontar_stock_fefo(presentacion, cantidad_a_descontar, vendedor):
    if presentacion.stock_real < cantidad_a_descontar:
        raise ValueError(
            f"Stock insuficiente para '{presentacion.nombre}': "
            f"hay {presentacion.stock_real} unidad(es), se pidieron {cantidad_a_descontar}."
        )

    lotes = (
        Lote.objects
        .filter(presentacion=presentacion, stock_actual__gt=0)
        .order_by('fecha_vencimiento')
    )

    pendiente = cantidad_a_descontar
    tocados   = []

    for lote in lotes:
        if pendiente <= 0:
            break
        tomar = min(lote.stock_actual, pendiente)
        lote.stock_actual -= tomar
        lote.save()
        tocados.append({'lote': lote, 'cantidad': tomar})
        pendiente -= tomar

    if pendiente > 0:
        raise ValueError("No se pudo completar el descuento FEFO; revisa la consistencia de lotes.")

    return tocados


def _to_decimal(valor, default='0'):
    try:
        return Decimal(str(valor))
    except (InvalidOperation, TypeError):
        return Decimal(default)


def _nombre_usuario(usuario):
    """Devuelve un nombre legible para un usuario."""
    if not usuario:
        return 'N/A'
    nombre = getattr(usuario, 'nombre', None)
    if nombre:
        return nombre
    get_full_name = getattr(usuario, 'get_full_name', None)
    if callable(get_full_name):
        nombre_completo = get_full_name()
        if nombre_completo:
            return nombre_completo
    return str(usuario)


def _historial_caja(limite=30):
    """
    Devuelve el historial de aperturas/cierres de caja de TODOS los usuarios,
    del más reciente al más antiguo.
    """
    aperturas = (
        AperturaCaja.objects
        .select_related('documento_usuario')
        .order_by('-fecha', '-creado_en')[:limite]
    )

    historial = []
    for apertura in aperturas:
        cierre = getattr(apertura, 'cierre', None)

        historial.append({
            'fecha':                apertura.fecha,
            'usuario':              _nombre_usuario(apertura.documento_usuario),
            'hora_apertura':        apertura.creado_en,
            'monto_base':           apertura.monto_base,
            'cerrada':              cierre is not None,
            'total_contado':        cierre.total_contado if cierre else None,
            'monto_base_siguiente': cierre.monto_base_siguiente if cierre else None,
            'total_retirado':       cierre.total_retirado if cierre else None,
        })

    return historial


# ════════════════════════════════════════
# CARRITO EN SESIÓN
# ════════════════════════════════════════

def _carrito(request):
    return request.session.setdefault('pv_carrito', [])


def _carrito_detallado(request):
    """Carrito con subtotales ya calculados, listo para el template."""
    items          = []
    subtotal_total = Decimal('0')
    for idx, item in enumerate(_carrito(request)):
        precio   = _to_decimal(item.get('precio', 0))
        cantidad = int(item.get('cantidad', 0))
        subtotal = precio * cantidad
        subtotal_total += subtotal
        items.append({
            'index':           idx,
            'nombre':          item.get('nombre', ''),
            'cantidad':        cantidad,
            'precio':          precio,
            'subtotal':        subtotal,
            'producto_id':     item.get('producto_id'),
            'presentacion_id': item.get('presentacion_id'),
        })
    return items, subtotal_total


def _agregar_item_carrito(request, producto, presentacion, cantidad):
    if cantidad <= 0:
        messages.error(request, 'La cantidad debe ser mayor a 0.')
        return False

    stock_disponible = presentacion.stock_real if presentacion else producto.stock_total
    carrito          = _carrito(request)

    existente = None
    for item in carrito:
        mismo_producto     = item.get('producto_id') == producto.pk
        misma_presentacion = item.get('presentacion_id') == (presentacion.pk if presentacion else None)
        if mismo_producto and misma_presentacion:
            existente = item
            break

    cantidad_previa = existente['cantidad'] if existente else 0
    cantidad_total  = cantidad_previa + cantidad

    if cantidad_total > stock_disponible:
        messages.error(request, f'Stock insuficiente: solo hay {stock_disponible} disponibles.')
        return False

    nombre = producto.nombre + (f' ({presentacion.nombre})' if presentacion else '')
    precio = float(presentacion.precio) if presentacion else float(producto.precio_unitario)

    if existente:
        existente['cantidad'] = cantidad_total
    else:
        carrito.append({
            'producto_id':     producto.pk,
            'presentacion_id': presentacion.pk if presentacion else None,
            'nombre':          nombre,
            'cantidad':        cantidad_total,
            'precio':          precio,
        })

    request.session.modified = True
    messages.success(request, f'{nombre} agregado al carrito.')
    return True


# ════════════════════════════════════════
# RENDER PRINCIPAL DEL PUNTO DE VENTA
# ════════════════════════════════════════

def _render_pos(request, sticky=None, error_apertura=None, error_cierre=None):
    sticky     = sticky or {}
    hoy        = timezone.localdate()
    usuario_id = request.session.get('usuario_id')

    form     = VentaForm()
    clientes = Cliente.objects.all().order_by('nombre')
    total_dia = int(sum(v.total_venta for v in Venta.objects.filter(fecha__date=hoy)))

    caja_abierta  = AperturaCaja.objects.filter(fecha=hoy, documento_usuario_id=usuario_id).first()
    ultimo_cierre = CierreCaja.objects.filter(fecha=hoy, documento_usuario_id=usuario_id).first()

    cierre_anterior = (
        CierreCaja.objects
        .filter(documento_usuario_id=usuario_id)
        .exclude(fecha=hoy)
        .order_by('-fecha')
        .first()
    )
    base_esperada = cierre_anterior.monto_base_siguiente if cierre_anterior else None

    historial_caja = _historial_caja()

    # ── Navegación del catálogo (categorías → productos → presentaciones) ──
    vista            = request.session.get('pv_vista', 'categorias')
    categoria_actual = None
    producto_actual  = None

    if vista in ('productos', 'presentaciones'):
        cat_id = request.session.get('pv_categoria_id')
        if cat_id:
            categoria_actual = (
                Categoria.objects
                .prefetch_related('productos__presentaciones')
                .filter(pk=cat_id)
                .first()
            )
        if not categoria_actual:
            vista = 'categorias'

    if vista == 'presentaciones':
        prod_id = request.session.get('pv_producto_id')
        if prod_id:
            producto_actual = (
                Producto.objects
                .prefetch_related('presentaciones')
                .filter(pk=prod_id)
                .first()
            )
        if not producto_actual:
            vista = 'productos'

    categorias = Categoria.objects.prefetch_related('productos__presentaciones').all()

    carrito_items, subtotal = _carrito_detallado(request)

    descuento_pct   = _to_decimal(sticky.get('descuento_porcentaje', '0'))
    monto_descuento = (subtotal * descuento_pct) / Decimal('100')
    total_final     = subtotal - monto_descuento

    # ── Historial: solo ventas del turno actual ──
    ventas_qs = (
        Venta.objects
        .prefetch_related(
            'detalles__codigo_producto',
            'detalles__codigo_presentacion',
        )
        .annotate(
            cantidad_total=Sum('detalles__cantidad'),
            producto_principal=Min('detalles__codigo_producto__nombre'),
            precio_max=Max('detalles__precio_unitario'),
        )
    )

    if caja_abierta:
        ventas_qs = ventas_qs.filter(fecha__gte=caja_abierta.creado_en)
        if ultimo_cierre:
            ventas_qs = ventas_qs.filter(fecha__lte=ultimo_cierre.creado_en)
    else:
        ventas_qs = ventas_qs.none()

    q = request.GET.get('q', '').strip()
    if q:
        ventas_qs = ventas_qs.filter(
            Q(codigo_cliente__nombre__icontains=q) |
            Q(detalles__codigo_producto__nombre__icontains=q)
        ).distinct()

    metodo = request.GET.get('metodo', 'todos')
    if metodo != 'todos':
        ventas_qs = ventas_qs.filter(metodo_pago=metodo)

    orden     = request.GET.get('orden', 'fecha_desc')
    orden_map = {
        'producto_asc':  'producto_principal',
        'producto_desc': '-producto_principal',
        'cantidad_asc':  'cantidad_total',
        'cantidad_desc': '-cantidad_total',
        'precio_asc':    'precio_max',
        'precio_desc':   '-precio_max',
        'total_asc':     'total_venta',
        'total_desc':    '-total_venta',
        'fecha_asc':     'fecha',
        'fecha_desc':    '-fecha',
        'cliente_asc':   'codigo_cliente__nombre',
        'cliente_desc':  '-codigo_cliente__nombre',
    }
    ventas_qs = ventas_qs.order_by(orden_map.get(orden, '-fecha'))

    def _opuesto(campo):
        return f'{campo}_asc' if orden != f'{campo}_asc' else f'{campo}_desc'

    columnas_orden = ['cliente', 'producto', 'cantidad', 'precio', 'total', 'fecha']
    orden_links    = {c: _opuesto(c) for c in columnas_orden}
    orden_estado   = {}
    for c in columnas_orden:
        if orden == f'{c}_asc':
            orden_estado[c] = 'asc'
        elif orden == f'{c}_desc':
            orden_estado[c] = 'desc'
        else:
            orden_estado[c] = None

    # ── Denominaciones para apertura/cierre ──
    valores_ap = request.session.get('pv_apertura_valores', {})
    valores_ci = request.session.get('pv_cierre_valores', {})

    apertura_billetes = [{'valor': v, 'cantidad': valores_ap.get(str(v), 0)} for v in BILLETES_DENOM]
    apertura_monedas  = [{'valor': v, 'cantidad': valores_ap.get(str(v), 0)} for v in MONEDAS_DENOM]
    cierre_billetes   = [{'valor': v, 'cantidad': valores_ci.get(str(v), 0)} for v in BILLETES_DENOM]
    cierre_monedas    = [{'valor': v, 'cantidad': valores_ci.get(str(v), 0)} for v in MONEDAS_DENOM]

    context = {
        'ventas':            ventas_qs,
        'form':              form,
        'categorias':        categorias,
        'clientes':          clientes,
        'total_dia':         total_dia,
        'hoy':               hoy,
        'caja_abierta':      caja_abierta,
        'ultimo_cierre':     ultimo_cierre,
        'base_esperada':     base_esperada,
        'historial_caja':    historial_caja,
        'vista':             vista,
        'categoria_actual':  categoria_actual,
        'producto_actual':   producto_actual,
        'carrito_items':     carrito_items,
        'subtotal':          subtotal,
        'descuento_pct':     descuento_pct,
        'monto_descuento':   monto_descuento,
        'total_final':       total_final,
        'metodo_pago_choices': Venta.METODO_PAGO_CHOICES,
        'sticky_metodo':     sticky.get('metodo_pago', 'efectivo'),
        'cliente_sticky':    sticky.get('cliente_nombre', ''),
        'apertura_billetes': apertura_billetes,
        'apertura_monedas':  apertura_monedas,
        'cierre_billetes':   cierre_billetes,
        'cierre_monedas':    cierre_monedas,
        'error_apertura':    error_apertura,
        'error_cierre':      error_cierre,
        'q_historial':       q,
        'metodo_historial':  metodo,
        'orden_historial':   orden,
        'orden_links':       orden_links,
        'orden_estado':      orden_estado,
        'breadcrumb_items': [
            {'nombre': 'Ventas', 'url': None},
        ],
    }
    return render(request, 'ventas/ventas.html', context)


# ════════════════════════════════════════
# ACCIONES DEL CATÁLOGO / CARRITO
# ════════════════════════════════════════

def _accion_ver_categoria(request):
    request.session['pv_categoria_id'] = request.POST.get('categoria_id')
    request.session['pv_vista'] = 'productos'
    request.session.pop('pv_producto_id', None)
    return redirect('ventas:ventas_lista')


def _accion_volver_categorias(request):
    request.session['pv_vista'] = 'categorias'
    request.session.pop('pv_categoria_id', None)
    request.session.pop('pv_producto_id', None)
    return redirect('ventas:ventas_lista')


def _accion_ver_producto(request):
    request.session['pv_producto_id'] = request.POST.get('producto_id')
    request.session['pv_vista'] = 'presentaciones'
    return redirect('ventas:ventas_lista')


def _accion_volver_productos(request):
    request.session['pv_vista'] = 'productos'
    request.session.pop('pv_producto_id', None)
    return redirect('ventas:ventas_lista')


def _accion_agregar_carrito(request):
    hoy        = timezone.localdate()
    usuario_id = request.session.get('usuario_id')
    caja_abierta = AperturaCaja.objects.filter(fecha=hoy, documento_usuario_id=usuario_id).exists()

    if not caja_abierta:
        messages.error(request, 'Debes abrir la caja antes de agregar productos.')
        raise

    producto_id     = request.POST.get('producto_id')
    presentacion_id = request.POST.get('presentacion_id', '').strip()
    cantidad_str    = request.POST.get('cantidad', '1').strip()
    cantidad        = int(cantidad_str) if cantidad_str.isdigit() else 1

    producto     = get_object_or_404(Producto, pk=producto_id)
    presentacion = None
    if presentacion_id:
        presentacion = get_object_or_404(PresentacionProducto, pk=presentacion_id, producto=producto)

    _agregar_item_carrito(request, producto, presentacion, cantidad)

    request.session['pv_vista'] = 'categorias'
    request.session.pop('pv_categoria_id', None)
    request.session.pop('pv_producto_id', None)
    return redirect('ventas:ventas_lista')


def _accion_quitar_item(request):
    try:
        index   = int(request.POST.get('index'))
        carrito = _carrito(request)
        if 0 <= index < len(carrito):
            carrito.pop(index)
            request.session.modified = True
    except (TypeError, ValueError):
        pass
    return redirect('ventas:ventas_lista')


def _accion_vaciar_carrito(request):
    request.session['pv_carrito'] = []
    return redirect('ventas:ventas_lista')


@transaction.atomic
def _accion_confirmar_venta(request):
    hoy        = timezone.localdate()
    usuario_id = request.session.get('usuario_id')
    caja_abierta = AperturaCaja.objects.filter(fecha=hoy, documento_usuario_id=usuario_id).exists()

    if not caja_abierta:
        messages.error(request, 'Debes abrir la caja antes de registrar una venta.')
        return redirect('ventas:ventas_lista')

    carrito = _carrito(request)
    if not carrito:
        messages.error(request, 'El carrito está vacío.')
        return redirect('ventas:ventas_lista')

    cliente_nombre   = request.POST.get('cliente_nombre', 'Consumidor final').strip() or 'Consumidor final'
    descuento_pct    = _to_decimal(request.POST.get('descuento_porcentaje', '0'))
    metodo_pago      = request.POST.get('metodo_pago', 'efectivo')
    comprobante_pago = request.FILES.get('comprobante_pago')

    sticky = {
        'cliente_nombre':       cliente_nombre,
        'descuento_porcentaje': str(descuento_pct),
        'metodo_pago':          metodo_pago,
    }

    # Obtener o crear cliente
    usuario_actual = None
    if usuario_id:
        usuario_actual = Usuario.objects.filter(pk=usuario_id).first()

    # Buscar cliente por nombre (solo nombre, ya que apellido puede estar vacío)
    cliente, _creado = Cliente.objects.get_or_create(
        nombre=cliente_nombre,
        defaults={'documento_usuario': usuario_actual},
    )

    vendedor = usuario_actual

    # Revalidar stock al confirmar
    items_validados = []
    subtotal_venta  = Decimal('0')

    for item in carrito:
        producto = Producto.objects.filter(pk=item['producto_id']).first()
        if not producto:
            messages.error(request, 'Uno de los productos del carrito ya no existe.')
            return _render_pos(request, sticky=sticky)

        presentacion = None
        if item.get('presentacion_id'):
            presentacion = PresentacionProducto.objects.filter(
                pk=item['presentacion_id'], producto=producto
            ).first()

        cantidad   = int(item['cantidad'])
        precio     = _to_decimal(item['precio'])
        disponible = presentacion.stock_real if presentacion else producto.stock_total

        if cantidad > disponible:
            messages.error(request, f"Stock insuficiente para {item['nombre']}: solo hay {disponible}.")
            return _render_pos(request, sticky=sticky)

        items_validados.append({
            'producto': producto, 'presentacion': presentacion,
            'cantidad': cantidad, 'precio': precio,
        })
        subtotal_venta += precio * cantidad

    monto_descuento = (subtotal_venta * descuento_pct) / Decimal('100')
    total_final     = subtotal_venta - monto_descuento

    # Validar que el método de pago sea válido
    metodos_validos = [m[0] for m in Venta.METODO_PAGO_CHOICES]
    if metodo_pago not in metodos_validos:
        metodo_pago = 'efectivo'

    venta = Venta.objects.create(
        codigo_cliente=cliente,
        documento_usuario=vendedor,
        descuento_porcentaje=descuento_pct,
        total_venta=total_final,
        metodo_pago=metodo_pago,
        comprobante_pago=comprobante_pago,
    )

    for item in items_validados:
        producto     = item['producto']
        presentacion = item['presentacion']
        cantidad     = item['cantidad']
        precio       = item['precio']
        descuento    = Decimal('0')
        subtotal_det = precio * cantidad
        total_det    = subtotal_det - descuento

        DetalleVenta.objects.create(
            codigo_venta=venta,
            codigo_producto=producto,
            codigo_presentacion=presentacion,
            cantidad=cantidad,
            precio_unitario=precio,
            valor_descuento=descuento,
            subtotal=subtotal_det,
            total=total_det,
        )

        if presentacion:
            lotes_tocados = _descontar_stock_fefo(presentacion, cantidad, vendedor)
            for lt in lotes_tocados:
                Inventario.objects.create(
                    presentacion=presentacion,
                    lote=lt['lote'],
                    registrado_por=vendedor,
                    tipo='salida',
                    cantidad=lt['cantidad'],
                    motivo='Venta registrada',
                )
        else:
            producto.cantidad_disponible -= cantidad
            producto.save()
            Inventario.objects.create(
                presentacion=presentacion or PresentacionProducto.objects.filter(producto=producto).first(),
                lote=Lote.objects.filter(presentacion__producto=producto).first(),
                registrado_por=vendedor,
                tipo='salida',
                cantidad=cantidad,
                motivo='Venta registrada',
            )

    request.session['pv_carrito'] = []
    messages.success(request, f"Venta registrada — Total: ${total_final:,.0f}".replace(',', '.'))
    return redirect('ventas:ventas_lista')


# ════════════════════════════════════════
# CAJA — APERTURA / CIERRE
# ════════════════════════════════════════

def _accion_confirmar_apertura(request):
    hoy        = timezone.localdate()
    usuario_id = request.session.get('usuario_id')

    if AperturaCaja.objects.filter(fecha=hoy, documento_usuario_id=usuario_id).exists():
        messages.error(request, 'Ya hay una caja abierta hoy.')
        return redirect('ventas:ventas_lista')

    valores = {}
    total   = Decimal('0')
    for valor in TODAS_DENOM:
        cantidad_str = request.POST.get(f'apertura_{valor}', '0').strip()
        cantidad     = int(cantidad_str) if cantidad_str.isdigit() else 0
        valores[str(valor)] = cantidad
        total += Decimal(valor) * cantidad

    observacion = request.POST.get('ct_observacion', '').strip()
    request.session['pv_apertura_valores'] = valores

    cierre_anterior = (
        CierreCaja.objects
        .filter(documento_usuario_id=usuario_id)
        .exclude(fecha=hoy)
        .order_by('-fecha')
        .first()
    )

    if cierre_anterior:
        base_esperada = cierre_anterior.monto_base_siguiente
        diferencia    = total - base_esperada
        if diferencia != 0:
            texto = (
                f"El total contado (${total:,.0f}) no coincide con la base dejada en el cierre "
                f"anterior (${base_esperada:,.0f}). Diferencia: ${abs(diferencia):,.0f}. "
                f"Corrige el conteo antes de abrir la caja."
            ).replace(',', '.')
            messages.error(request, texto)
            return _render_pos(request, error_apertura={'total': total, 'texto': texto})

    AperturaCaja.objects.create(
        fecha=hoy,
        documento_usuario_id=usuario_id,
        monto_base=total,
        observacion=observacion,
        denominaciones=valores,
    )
    request.session.pop('pv_apertura_valores', None)
    messages.success(request, f"Caja abierta con ${total:,.0f}.".replace(',', '.'))
    return redirect('ventas:ventas_lista')


def _accion_confirmar_cierre(request):
    hoy        = timezone.localdate()
    usuario_id = request.session.get('usuario_id')

    apertura = AperturaCaja.objects.filter(fecha=hoy, documento_usuario_id=usuario_id).first()
    if not apertura:
        messages.error(request, 'No hay caja abierta.')
        return redirect('ventas:ventas_lista')
    if hasattr(apertura, 'cierre'):
        messages.error(request, 'La caja ya fue cerrada hoy.')
        return redirect('ventas:ventas_lista')

    valores = {}
    total   = Decimal('0')
    for valor in TODAS_DENOM:
        cantidad_str = request.POST.get(f'cierre_{valor}', '0').strip()
        cantidad     = int(cantidad_str) if cantidad_str.isdigit() else 0
        valores[str(valor)] = cantidad
        total += Decimal(valor) * cantidad

    request.session['pv_cierre_valores'] = valores

    base_siguiente = _to_decimal(request.POST.get('base_siguiente', '0'))
    total_retirado = max(Decimal('0'), total - base_siguiente)

    CierreCaja.objects.create(
        fecha=hoy,
        apertura=apertura,
        documento_usuario_id=usuario_id,
        total_contado=total,
        monto_base_siguiente=base_siguiente,
        total_retirado=total_retirado,
        total_en_efectivo=total,
        total_transferencias=Decimal('0'),
        total_retirado_efectivo=total_retirado,
        monto_base=base_siguiente,
        denominaciones=valores,
    )
    request.session.pop('pv_cierre_valores', None)
    messages.success(request, f"Caja cerrada. Total contado: ${total:,.0f}.".replace(',', '.'))
    return redirect('ventas:ventas_lista')


# ════════════════════════════════════════
# DISPATCHER DE ACCIONES + VISTA PRINCIPAL
# ════════════════════════════════════════

_ACCIONES_POS = {
    'ver_categoria':      _accion_ver_categoria,
    'volver_categorias':  _accion_volver_categorias,
    'ver_producto':       _accion_ver_producto,
    'volver_productos':   _accion_volver_productos,
    'agregar_carrito':    _accion_agregar_carrito,
    'quitar_item':        _accion_quitar_item,
    'vaciar_carrito':     _accion_vaciar_carrito,
    'confirmar_venta':    _accion_confirmar_venta,
    'confirmar_apertura': _accion_confirmar_apertura,
    'confirmar_cierre':   _accion_confirmar_cierre,
}


@session_required
def ventas_lista(request):
    if request.method == 'POST':
        accion  = request.POST.get('accion', '')
        handler = _ACCIONES_POS.get(accion)
        if handler:
            return handler(request)
        messages.error(request, 'Acción no reconocida.')
        return redirect('ventas:ventas_lista')

    return _render_pos(request)


@session_required
@transaction.atomic
def eliminar_venta(request, pk):
    venta = get_object_or_404(Venta, pk=pk)
    if request.method != 'POST':
        return redirect('ventas:ventas_lista')

    for det in venta.detalles.select_related('codigo_producto', 'codigo_presentacion').all():
        if det.codigo_presentacion:
            movimientos_salida = Inventario.objects.filter(
                presentacion=det.codigo_presentacion,
                tipo='salida',
                motivo='Venta registrada',
                lote__presentacion=det.codigo_presentacion,
                fecha_actualizada__date=venta.fecha.date(),
            )

            lotes_a_restaurar = {}
            for mov in movimientos_salida:
                if mov.lote_id not in lotes_a_restaurar:
                    lotes_a_restaurar[mov.lote_id] = {'lote': mov.lote, 'cantidad': 0}
                lotes_a_restaurar[mov.lote_id]['cantidad'] += mov.cantidad

            for info in lotes_a_restaurar.values():
                lote = info['lote']
                lote.stock_actual += info['cantidad']
                lote.save()

                Inventario.objects.create(
                    presentacion=det.codigo_presentacion,
                    lote=lote,
                    tipo='entrada',
                    cantidad=info['cantidad'],
                    motivo='Anulación de venta',
                )
        elif det.codigo_producto:
            det.codigo_producto.cantidad_disponible += det.cantidad
            det.codigo_producto.save()

    venta.delete()
    messages.success(request, "Venta eliminada y stock restaurado.")
    return redirect('ventas:ventas_lista')


def producto_stock_json(request, pk):
    """Endpoint JSON de stock de un producto."""
    producto = get_object_or_404(Producto.objects.prefetch_related('presentaciones'), pk=pk)
    return JsonResponse({
        'stock':  producto.stock_total,
        'precio': float(producto.precio_unitario),
        'unid':   producto.unidad,
        'presentaciones': [
            {
                'id':       p.id,
                'nombre':   p.nombre,
                'unidades': p.unidades,
                'cantidad': p.stock_real,
                'precio':   float(p.precio),
            }
            for p in producto.presentaciones.all()
        ],
    })


@session_required
def ventas_del_dia(request):
    hoy    = timezone.localdate()
    ventas = Venta.objects.filter(fecha__date=hoy).prefetch_related(
        'detalles__codigo_producto', 'detalles__codigo_presentacion'
    ).order_by('-fecha')

    total_dia       = int(sum(v.total_venta for v in ventas))
    total_productos = sum(
        det.cantidad
        for v in ventas
        for det in v.detalles.all()
    )

    producto_top = (
        DetalleVenta.objects
        .filter(codigo_venta__in=ventas)
        .values('codigo_producto__nombre')
        .annotate(total_unidades=Sum('cantidad'))
        .order_by('-total_unidades')
        .first()
    )

    productos_top_qs = (
        DetalleVenta.objects
        .filter(codigo_venta__in=ventas)
        .values('codigo_producto__nombre')
        .annotate(total_unidades=Sum('cantidad'))
        .order_by('-total_unidades')[:5]
    )
    max_unidades = productos_top_qs[0]['total_unidades'] if productos_top_qs else 0
    productos_top = [
        {
            'nombre':     p['codigo_producto__nombre'],
            'unidades':   p['total_unidades'],
            'porcentaje': round((p['total_unidades'] / max_unidades) * 100, 1) if max_unidades else 0,
        }
        for p in productos_top_qs
    ]

    ventas_top_qs = sorted(ventas, key=lambda v: v.total_venta, reverse=True)[:2]
    ventas_top = [
        {
            'id':         v.pk,
            'total':      int(v.total_venta),
            'porcentaje': round((float(v.total_venta) / total_dia) * 100, 1) if total_dia else 0,
        }
        for v in ventas_top_qs
    ]

    meta_diaria    = META_VENTA_DIARIA
    porcentaje_meta = 0
    if meta_diaria:
        porcentaje_meta = round(min((total_dia / meta_diaria) * 100, 100), 1) if total_dia else 0

    context = {
        'ventas':          ventas,
        'hoy':             hoy,
        'total_dia':       total_dia,
        'total_productos': total_productos,
        'producto_top':    producto_top,
        'productos_top':   productos_top,
        'ventas_top':      ventas_top,
        'meta_diaria':     meta_diaria,
        'porcentaje_meta': porcentaje_meta,
        'breadcrumb_items': [
            {'nombre': 'Ventas', 'url': reverse('ventas:ventas_lista')},
            {'nombre': 'Ventas del Día', 'url': None},
        ],
    }
    return render(request, 'ventas/ventas_dia.html', context)


# ════════════════════════════════════════
# CONTROL DE CAJA — AJAX (compatibilidad)
# ════════════════════════════════════════

@session_required
@require_POST
def registrar_conteo(request):
    try:
        data           = json.loads(request.body)
        monto_contado  = data.get('monto_contado', 0)
        observacion    = data.get('observacion', '')
        denominaciones = data.get('denominaciones', {})

        hoy        = timezone.localdate()
        usuario_id = request.session.get('usuario_id')

        if AperturaCaja.objects.filter(fecha=hoy, documento_usuario_id=usuario_id).exists():
            return JsonResponse({'ok': False, 'error': 'Ya hay una caja abierta hoy.'})

        AperturaCaja.objects.create(
            fecha=hoy,
            documento_usuario_id=usuario_id,
            monto_base=monto_contado,
            observacion=observacion,
            denominaciones=denominaciones,
        )
        return JsonResponse({'ok': True})

    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})


@session_required
@require_POST
def cierre_caja(request):
    try:
        data                 = json.loads(request.body)
        total_contado        = data.get('total_contado', 0)
        monto_base_siguiente = data.get('monto_base_siguiente', 0)
        denominaciones       = data.get('denominaciones', {})

        hoy        = timezone.localdate()
        usuario_id = request.session.get('usuario_id')

        apertura = AperturaCaja.objects.filter(fecha=hoy, documento_usuario_id=usuario_id).first()
        if not apertura:
            return JsonResponse({'ok': False, 'error': 'No hay caja abierta.'})

        if hasattr(apertura, 'cierre'):
            return JsonResponse({'ok': False, 'error': 'La caja ya fue cerrada hoy.'})

        total_retirado = max(0, float(total_contado) - float(monto_base_siguiente))

        CierreCaja.objects.create(
            fecha=hoy,
            apertura=apertura,
            documento_usuario_id=usuario_id,
            total_contado=total_contado,
            monto_base_siguiente=monto_base_siguiente,
            total_retirado=total_retirado,
            total_en_efectivo=total_contado,
            total_transferencias=0,
            total_retirado_efectivo=total_retirado,
            monto_base=monto_base_siguiente,
            denominaciones=denominaciones,
        )
        return JsonResponse({'ok': True})

    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})


# ════════════════════════════════════════
# DEVOLUCIONES
# ════════════════════════════════════════

@session_required
def lista_devoluciones(request):
    """Lista principal de devoluciones con flujo integrado."""
    try:
        if request.GET.get('nuevo'):
            request.session['dev_paso'] = 1
            for key in list(request.session.keys()):
                if key.startswith('dev_'):
                    del request.session[key]
            request.session.modified = True

        return devoluciones_flujo(request)
    except Exception as e:
        messages.error(request, f'❌ Error: {str(e)}')
        return redirect('ventas:ventas_lista')


@session_required
def buscar_venta_devolucion(request):
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse({'ventas': []})

    ventas = Venta.objects.filter(codigo_cliente__nombre__icontains=q).order_by('-fecha')[:10]
    if q.isdigit():
        ventas = (Venta.objects.filter(pk=int(q)) | ventas).distinct()

    return JsonResponse({'ventas': [
        {
            'id':      v.pk,
            'cliente': v.codigo_cliente.nombre,
            'fecha':   v.fecha.strftime('%d/%m/%Y %H:%M'),
            'total':   float(v.total_venta),
        }
        for v in ventas
    ]})


@session_required
def detalle_venta_devolucion(request, venta_id):
    venta = get_object_or_404(Venta, pk=venta_id)
    return JsonResponse({
        'venta_id':  venta.pk,
        'cliente':   venta.codigo_cliente.nombre,
        'fecha':     venta.fecha.strftime('%d/%m/%Y %H:%M'),
        'total':     float(venta.total_venta),
        'descuento': float(venta.descuento_porcentaje),
        'detalles': [
            {
                'detalle_id':      d.pk,
                'producto_id':     d.codigo_producto.pk if d.codigo_producto else None,
                'producto':        d.codigo_producto.nombre if d.codigo_producto else '',
                'presentacion_id': d.codigo_presentacion.pk if d.codigo_presentacion else None,
                'presentacion':    d.codigo_presentacion.nombre if d.codigo_presentacion else '',
                'cantidad':        d.cantidad,
                'precio':          float(d.precio_unitario),
                'subtotal':        float(d.subtotal),
            }
            for d in venta.detalles.select_related(
                'codigo_producto', 'codigo_presentacion'
            ).all()
        ],
    })


@session_required
def seleccionar_venta_devolucion(request, venta_id):
    """Selecciona venta y muestra formulario de devolución."""
    venta = get_object_or_404(Venta, pk=venta_id)
    form  = DevolucionForm() if request.method == 'GET' else DevolucionForm(request.POST)

    context = {
        'venta':          venta,
        'detalles_venta': venta.detalles.select_related(
            'codigo_producto', 'codigo_presentacion'
        ),
        'form':           form,
        'devoluciones':   Devolucion.objects.select_related('codigo_venta'),
        'breadcrumb_items': [
            {'nombre': 'Ventas',       'url': reverse('ventas:ventas_lista')},
            {'nombre': 'Devoluciones', 'url': reverse('ventas:lista_devoluciones')},
            {'nombre': f'Devolución — Venta #{venta.pk}', 'url': None},
        ],
    }

    return render(request, 'ventas/devoluciones.html', context)


@session_required
@transaction.atomic
def registrar_devolucion(request, venta_id):
    """Registra la devolución con los productos y detalles seleccionados."""
    if request.method != 'POST':
        return redirect('ventas:lista_devoluciones')

    venta = get_object_or_404(Venta, pk=venta_id)
    form  = DevolucionForm(request.POST)

    detalles_seleccionados = request.POST.getlist('detalle_id')

    if not detalles_seleccionados:
        messages.error(request, '⚠️ Debes seleccionar al menos un producto para devolver.')
        return redirect('ventas:seleccionar_venta_devolucion', venta_id=venta_id)

    if not form.is_valid():
        messages.error(request, '⚠️ Debes completar todos los campos obligatorios.')
        return redirect('ventas:seleccionar_venta_devolucion', venta_id=venta_id)

    total_devuelto = Decimal('0')
    detalles_venta = venta.detalles.filter(pk__in=detalles_seleccionados)

    for detalle in detalles_venta:
        total_devuelto += detalle.subtotal

    # Tomar el primer detalle seleccionado como referencia principal (MER)
    detalle_principal = detalles_venta.first()

    usuario_id      = request.session.get('usuario_id')
    usuario_actual  = Usuario.objects.filter(pk=usuario_id).first() if usuario_id else None

    devolucion = Devolucion.objects.create(
        codigo_venta=venta,
        codigo_detalle_venta=detalle_principal,
        documento_usuario=usuario_actual,
        motivo=form.cleaned_data['motivo'],
        tipo_devolucion=form.cleaned_data['tipo_devolucion'],
        observaciones=form.cleaned_data['observaciones'],
        total_devuelto=total_devuelto,
        presenta_comprobante=True,
        restaurar_stock=True,
    )

    for detalle_venta in detalles_venta:
        DetalleDevolucion.objects.create(
            devolucion=devolucion,
            presentacion=detalle_venta.codigo_presentacion,
            cantidad=detalle_venta.cantidad,
            precio_unitario=detalle_venta.precio_unitario,
        )

        if detalle_venta.codigo_presentacion:
            detalle_venta.codigo_presentacion.cantidad += detalle_venta.cantidad
            detalle_venta.codigo_presentacion.save()

    messages.success(request, f'✅ Devolución {devolucion.numero} registrada correctamente.')
    return redirect('ventas:comprobante_devolucion', pk=devolucion.pk)


@session_required
def comprobante_devolucion(request, pk):
    devolucion = get_object_or_404(
        Devolucion.objects.select_related('codigo_venta').prefetch_related(
            'detalles__presentacion'
        ), pk=pk,
    )
    return render(request, 'ventas/comprobante_devolucion.html', {
        'devolucion': devolucion,
        'breadcrumb_items': [
            {'nombre': 'Ventas',       'url': reverse('ventas:ventas_lista')},
            {'nombre': 'Devoluciones', 'url': reverse('ventas:lista_devoluciones')},
            {'nombre': f'Comprobante {devolucion.numero}', 'url': None},
        ],
    })


@session_required
def devoluciones_flujo(request):
    paso     = request.session.get('dev_paso', 1)
    venta_id = request.session.get('dev_venta_id')

    # Limpiar sesiones antiguas en paso inválido
    if paso == 7:
        for key in list(request.session.keys()):
            if key.startswith('dev_'):
                del request.session[key]
        request.session['dev_paso'] = 1
        request.session.modified    = True
        return redirect(reverse('ventas:lista_devoluciones'))

    if paso > 1 and not venta_id:
        request.session['dev_paso'] = 1
        request.session.modified    = True
        return redirect(reverse('ventas:lista_devoluciones') + '#formDevoluciones')

    usuario_id     = request.session.get('usuario_id')
    usuario_actual = Usuario.objects.filter(pk=usuario_id).first() if usuario_id else None

    # PASO 1: Seleccionar venta
    if request.method == 'POST' and paso == 1:
        venta_id_post = request.POST.get('venta_id', '').strip()

        if venta_id_post:
            try:
                venta = Venta.objects.get(pk=int(venta_id_post))
                request.session['dev_venta_id'] = int(venta_id_post)
                request.session['dev_paso']     = 2
                request.session.modified        = True
                messages.success(request, f'✅ Venta seleccionada: {venta.codigo_cliente.nombre}')
                return redirect(reverse('ventas:lista_devoluciones') + '#formDevoluciones')
            except (Venta.DoesNotExist, ValueError):
                messages.error(request, '⚠️ Venta no válida. Intenta nuevamente.')
        else:
            messages.error(request, '⚠️ Debes seleccionar una venta.')

    elif request.method == 'POST' and paso == 2:
        if not venta_id:
            messages.error(request, '⚠️ Primero debes seleccionar una venta.')
            request.session['dev_paso'] = 1
            request.session.modified    = True
            return redirect(reverse('ventas:lista_devoluciones') + '#formDevoluciones')

        action = request.POST.get('action', 'continuar')

        if action == 'atras':
            request.session['dev_paso'] = 1
            request.session.modified    = True
            return redirect(reverse('ventas:lista_devoluciones') + '#formDevoluciones')

        productos_ids = request.POST.getlist('producto_id')
        if not productos_ids:
            messages.error(request, '⚠️ Debes seleccionar al menos un producto para devolver.')
            return redirect(reverse('ventas:lista_devoluciones') + '#formDevoluciones')

        productos_con_cantidad = {}
        venta_actual           = Venta.objects.get(pk=venta_id)

        for detalle_id in productos_ids:
            try:
                detalle_id_int = int(detalle_id)
                cantidad_str   = request.POST.get(f'cantidad_devolucion_{detalle_id_int}', '0')
                cantidad       = int(cantidad_str)

                detalle = venta_actual.detalles.get(pk=detalle_id_int)
                if cantidad <= 0 or cantidad > detalle.cantidad:
                    messages.error(
                        request,
                        f'⚠️ Cantidad inválida para {detalle.codigo_producto.nombre if detalle.codigo_producto else "producto"}. '
                        f'Debe ser entre 1 y {detalle.cantidad}.'
                    )
                    return redirect(reverse('ventas:lista_devoluciones') + '#formDevoluciones')

                productos_con_cantidad[detalle_id_int] = cantidad

            except (ValueError, TypeError, DetalleVenta.DoesNotExist):
                messages.error(request, '⚠️ Error al procesar las cantidades. Intenta nuevamente.')
                return redirect(reverse('ventas:lista_devoluciones') + '#formDevoluciones')

        if productos_con_cantidad:
            request.session['dev_productos'] = productos_con_cantidad
            request.session['dev_paso']      = 3
            request.session.modified         = True
            return redirect(reverse('ventas:lista_devoluciones') + '#formDevoluciones')
        else:
            messages.error(request, '⚠️ Debes especificar al menos 1 unidad para devolver.')

    elif request.method == 'POST' and paso == 3:
        action = request.POST.get('action', 'continuar')
        if action == 'atras':
            request.session['dev_paso'] = 2
            request.session.modified    = True
            return redirect(reverse('ventas:lista_devoluciones') + '#formDevoluciones')

        motivo        = request.POST.get('motivo', '').strip()
        observaciones = request.POST.get('observaciones', '').strip()

        motivos_validos = [choice[0] for choice in Devolucion.MOTIVO_CHOICES]
        if motivo in motivos_validos:
            request.session['dev_motivo']        = motivo
            request.session['dev_observaciones'] = observaciones
            request.session['dev_paso']          = 4
            request.session.modified             = True
            return redirect(reverse('ventas:lista_devoluciones') + '#formDevoluciones')
        else:
            messages.error(request, '⚠️ Selecciona un motivo válido.')

    elif request.method == 'POST' and paso == 4:
        action = request.POST.get('action', 'continuar')
        if action == 'atras':
            request.session['dev_paso'] = 3
            request.session.modified    = True
            return redirect(reverse('ventas:lista_devoluciones') + '#formDevoluciones')

        tipo_devolucion = request.POST.get('tipo_devolucion', '').strip()

        tipos_validos = [choice[0] for choice in Devolucion.TIPO_DEVOLUCION_CHOICES]
        if tipo_devolucion in tipos_validos:
            request.session['dev_tipo_devolucion'] = tipo_devolucion
            if tipo_devolucion in ('cambio', 'reembolso'):
                request.session['dev_paso'] = 5
            else:
                request.session['dev_paso'] = 6
            request.session.modified = True
            return redirect(reverse('ventas:lista_devoluciones') + '#formDevoluciones')
        else:
            messages.error(request, '⚠️ Selecciona un tipo de devolución válido.')

    elif request.method == 'POST' and paso == 5:
        tipo_devolucion = request.session.get('dev_tipo_devolucion')

        if request.POST.get('action') == 'atras':
            request.session['dev_paso'] = 4
            request.session.modified    = True
            return redirect(reverse('ventas:lista_devoluciones') + '#formDevoluciones')

        if tipo_devolucion == 'cambio':
            producto_cambio_id = request.POST.get('producto_cambio', '').strip()
            cantidad_cambio    = request.POST.get('cantidad_cambio', '').strip()

            if producto_cambio_id and cantidad_cambio:
                try:
                    producto_cambio_id = int(producto_cambio_id)
                    cantidad_cambio    = int(cantidad_cambio)
                    if cantidad_cambio < 1:
                        raise ValueError
                    Producto.objects.get(pk=producto_cambio_id)
                    request.session['dev_producto_cambio_id'] = producto_cambio_id
                    request.session['dev_cantidad_cambio']    = cantidad_cambio
                    request.session['dev_paso']               = 6
                    request.session.modified                  = True
                    return redirect(reverse('ventas:lista_devoluciones') + '#formDevoluciones')
                except (Producto.DoesNotExist, ValueError, TypeError):
                    messages.error(request, '⚠️ Datos inválidos. Intenta nuevamente.')
            else:
                messages.error(request, '⚠️ Debes seleccionar un producto de reemplazo y cantidad.')

        elif tipo_devolucion == 'reembolso':
            metodo_devolucion = request.POST.get('metodo_pago_devolucion', '').strip()
            metodos_validos   = [choice[0] for choice in Devolucion.METODO_PAGO_CHOICES]
            if metodo_devolucion in metodos_validos:
                request.session['dev_metodo_devolucion'] = metodo_devolucion
                request.session['dev_paso']              = 6
                request.session.modified                 = True
                return redirect(reverse('ventas:lista_devoluciones') + '#formDevoluciones')
            else:
                messages.error(request, '⚠️ Selecciona un método de devolución válido.')

    elif request.method == 'POST' and paso == 6:
        try:
            if request.POST.get('action') == 'atras':
                tipo_devolucion = request.session.get('dev_tipo_devolucion')
                request.session['dev_paso'] = 5 if tipo_devolucion in ('cambio', 'reembolso') else 4
                request.session.modified    = True
                return redirect(reverse('ventas:lista_devoluciones') + '#formDevoluciones')

            venta          = Venta.objects.get(pk=venta_id)
            productos_data = request.session.get('dev_productos', {})
            motivo         = request.session.get('dev_motivo')
            tipo_devolucion = request.session.get('dev_tipo_devolucion')
            observaciones  = request.session.get('dev_observaciones', '')

            if isinstance(productos_data, list):
                productos_con_cantidad = {
                    pid: venta.detalles.get(pk=pid).cantidad
                    if venta.detalles.filter(pk=pid).exists() else 1
                    for pid in productos_data
                }
            else:
                productos_con_cantidad = productos_data

            if not (venta and productos_con_cantidad and motivo and tipo_devolucion):
                messages.error(request, '⚠️ Error: Datos incompletos. Reinicia el proceso.')
                request.session['dev_paso'] = 1
                request.session.modified    = True
                return redirect(reverse('ventas:lista_devoluciones') + '#formDevoluciones')

            if productos_con_cantidad:
                keys_list = list(productos_con_cantidad.keys())
                if keys_list and isinstance(keys_list[0], str):
                    productos_con_cantidad = {int(k): v for k, v in productos_con_cantidad.items()}

            total_devuelto = Decimal('0')
            detalles_venta = venta.detalles.filter(pk__in=productos_con_cantidad.keys())

            if not detalles_venta.exists():
                messages.error(request, '⚠️ Los productos seleccionados no están disponibles.')
                request.session['dev_paso'] = 2
                request.session.modified    = True
                return redirect(reverse('ventas:lista_devoluciones') + '#formDevoluciones')

            for detalle in detalles_venta:
                cantidad_devolucion = productos_con_cantidad.get(detalle.pk, detalle.cantidad)
                subtotal = Decimal(str(cantidad_devolucion)) * detalle.precio_unitario
                total_devuelto += subtotal

            # Detalle principal de referencia (MER: codigo_detalle_venta)
            detalle_principal = detalles_venta.first()

            devolucion = Devolucion.objects.create(
                codigo_venta=venta,
                codigo_detalle_venta=detalle_principal,
                documento_usuario=usuario_actual,
                motivo=motivo,
                tipo_devolucion=tipo_devolucion,
                observaciones=observaciones,
                total_devuelto=total_devuelto,
                presenta_comprobante=True,
                restaurar_stock=True,
            )

            if tipo_devolucion == 'cambio':
                producto_cambio_id = request.session.get('dev_producto_cambio_id')
                cantidad_cambio    = request.session.get('dev_cantidad_cambio')

                if producto_cambio_id:
                    try:
                        producto_cambio          = Producto.objects.get(pk=producto_cambio_id)
                        devolucion.producto_cambio  = producto_cambio
                        devolucion.cantidad_cambio  = cantidad_cambio or 1
                        devolucion.save()
                        messages.info(
                            request,
                            f'📦 Cambio programado: {producto_cambio.nombre} x{devolucion.cantidad_cambio}'
                        )
                    except Producto.DoesNotExist:
                        pass

            elif tipo_devolucion == 'nota_credito':
                devolucion.saldo_credito = total_devuelto
                devolucion.save()
                messages.info(
                    request,
                    f'💳 Nota de crédito por ${total_devuelto:,.0f} generada'.replace(',', '.')
                )

            elif tipo_devolucion == 'reembolso':
                metodo_devolucion              = request.session.get('dev_metodo_devolucion')
                devolucion.metodo_pago_devolucion = metodo_devolucion
                devolucion.save()
                messages.info(
                    request,
                    f'💰 Reembolso programado: ${total_devuelto:,.0f} a {metodo_devolucion}'.replace(',', '.')
                )

            # Crear detalles de devolución con cantidades especificadas y restaurar stock
            for detalle_venta_item in detalles_venta:
                cantidad_devolucion = productos_con_cantidad.get(detalle_venta_item.pk, detalle_venta_item.cantidad)
                DetalleDevolucion.objects.create(
                    devolucion=devolucion,
                    presentacion=detalle_venta_item.codigo_presentacion,
                    cantidad=cantidad_devolucion,
                    precio_unitario=detalle_venta_item.precio_unitario,
                )

                if devolucion.restaurar_stock:
                    if detalle_venta_item.codigo_lote:
                        detalle_venta_item.codigo_lote.stock_actual += cantidad_devolucion
                        detalle_venta_item.codigo_lote.save()
                    if detalle_venta_item.codigo_presentacion:
                        detalle_venta_item.codigo_presentacion.cantidad += cantidad_devolucion
                        detalle_venta_item.codigo_presentacion.save()

            # Limpiar sesión
            for key in list(request.session.keys()):
                if key.startswith('dev_'):
                    del request.session[key]
            request.session.modified = True

            messages.success(request, f'✅ Devolución {devolucion.numero} registrada correctamente.')
            return redirect('ventas:comprobante_devolucion', pk=devolucion.pk)

        except Exception as e:
            messages.error(request, f'⚠️ Error al registrar devolución: {str(e)}')
            request.session['dev_paso'] = 1
            request.session.modified    = True
            return redirect(reverse('ventas:lista_devoluciones') + '#formDevoluciones')

    if request.method == 'POST' and request.POST.get('action') == 'atras':
        nuevo_paso = max(1, paso - 1)
        request.session['dev_paso'] = nuevo_paso
        request.session.modified    = True
        return redirect('ventas:lista_devoluciones')

    ventas       = Venta.objects.select_related('codigo_cliente').prefetch_related('detalles').order_by('-fecha')
    devoluciones = Devolucion.objects.select_related('codigo_venta').prefetch_related('detalles').order_by('-fecha')

    venta                = None
    detalles_venta       = []
    detalles_con_estado  = []

    if venta_id:
        try:
            venta = Venta.objects.prefetch_related(
                'detalles__codigo_producto',
                'detalles__codigo_presentacion',
            ).get(pk=venta_id)

            detalles_venta = venta.detalles.select_related(
                'codigo_producto', 'codigo_presentacion'
            ).all()

            for detalle in detalles_venta:
                cantidad_devuelta = DetalleDevolucion.objects.filter(
                    devolucion__codigo_venta=venta,
                    presentacion=detalle.codigo_presentacion,
                ).aggregate(total=Sum('cantidad'))['total'] or 0

                cantidad_pendiente = detalle.cantidad - cantidad_devuelta
                puede_devolver     = cantidad_pendiente > 0

                detalles_con_estado.append({
                    'detalle':            detalle,
                    'cantidad_devuelta':  cantidad_devuelta,
                    'cantidad_pendiente': cantidad_pendiente,
                    'puede_devolver':     puede_devolver,
                })
        except (Venta.DoesNotExist, ValueError, TypeError):
            venta = None
            request.session['dev_paso'] = 1
            request.session.modified    = True

    motivo_dict  = dict(Devolucion.MOTIVO_CHOICES)
    tipo_dict    = dict(Devolucion.TIPO_DEVOLUCION_CHOICES)
    metodos_dict = dict(Devolucion.METODO_PAGO_CHOICES)
    motivo_choices = Devolucion.MOTIVO_CHOICES

    productos = Producto.objects.all() if paso >= 5 else []

    total_devolver = Decimal('0')
    if venta_id:
        productos_data = request.session.get('dev_productos', {})

        if isinstance(productos_data, list):
            productos_con_cantidad = {
                pid: venta.detalles.get(pk=pid).cantidad
                if venta and venta.detalles.filter(pk=pid).exists() else 1
                for pid in productos_data
            }
        else:
            productos_con_cantidad = productos_data

        if productos_con_cantidad:
            keys_list = list(productos_con_cantidad.keys())
            if keys_list and isinstance(keys_list[0], str):
                productos_con_cantidad = {int(k): v for k, v in productos_con_cantidad.items()}

            if venta:
                detalles = venta.detalles.filter(pk__in=productos_con_cantidad.keys())
                for d in detalles:
                    cantidad = productos_con_cantidad.get(d.pk, d.cantidad)
                    total_devolver += Decimal(str(cantidad)) * d.precio_unitario

    if paso == 2 and venta and not detalles_con_estado:
        messages.warning(
            request,
            f'ℹ️ Venta: {venta.codigo_cliente.nombre} - Productos: {detalles_venta.count()}'
        )

    context = {
        'ventas':                        ventas,
        'venta':                         venta,
        'detalles_venta':                detalles_venta,
        'detalles_con_estado':           detalles_con_estado,
        'devoluciones':                  devoluciones,
        'paso':                          paso,
        'venta_id':                      venta_id,
        'motivo_choices':                motivo_choices,
        'motivo_seleccionado':           motivo_dict.get(request.session.get('dev_motivo'), ''),
        'tipo_devolucion_seleccionado':  tipo_dict.get(request.session.get('dev_tipo_devolucion'), ''),
        'observaciones':                 request.session.get('dev_observaciones', ''),
        'productos':                     productos,
        'metodos_pago':                  Devolucion.METODO_PAGO_CHOICES,
        'total_devolver':                total_devolver,
        'breadcrumb_items': [
            {'nombre': 'Ventas',       'url': reverse('ventas:ventas_lista')},
            {'nombre': 'Devoluciones', 'url': None},
        ],
    }

    return render(request, 'ventas/devoluciones.html', context)