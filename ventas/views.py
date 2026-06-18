from django.shortcuts import render, redirect, get_object_or_404 # type: ignore
from django.contrib import messages # type: ignore
from django.http import JsonResponse # type: ignore
from django.db import transaction # type: ignore
from django.utils import timezone # type: ignore
from django.views.decorators.http import require_POST # type: ignore
from decimal import Decimal, InvalidOperation
from functools import wraps
import json

from .models import Venta, DetalleVenta, AperturaCaja, CierreCaja, Devolucion, DetalleDevolucion, Cliente
from .forms import VentaForm, DetalleVentaForm
from productos.models import Producto, Categoria, PresentacionProducto
from inventario.models import Inventario, Lote
from usuarios.models import Usuario

BILLETES_DENOM = [100000, 50000, 20000, 10000, 5000, 2000, 1000]
MONEDAS_DENOM  = [500, 200, 100, 50]


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
# HELPERS FEFO
# ════════════════════════════════════════

def _descontar_stock_fefo(presentacion, cantidad_a_descontar, vendedor):
    """
    Descuenta `cantidad_a_descontar` unidades de `presentacion` usando FEFO
    (First Expired, First Out) sobre Lote.stock_actual.

    Retorna lista de dicts con los lotes tocados:
        [{'lote': <Lote>, 'cantidad': <int>}, ...]

    Lanza ValueError si el stock real es insuficiente.
    """
    # ① Validar contra stock_real de la presentación (no presentacion.cantidad)
    if presentacion.stock_real < cantidad_a_descontar:
        raise ValueError(
            f"Stock insuficiente para '{presentacion.nombre}': "
            f"hay {presentacion.stock_real} unidad(es), se pidieron {cantidad_a_descontar}."
        )

    # ② Lotes vigentes ordenados por fecha de vencimiento (FEFO)
    lotes = (
        Lote.objects
        .filter(presentacion=presentacion, stock_actual__gt=0)
        .order_by('fecha_vencimiento')   # el que vence antes primero
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
        # No debería ocurrir si stock_real estaba bien, pero por seguridad:
        raise ValueError("No se pudo completar el descuento FEFO; revisa la consistencia de lotes.")

    return tocados


def _restaurar_stock_fefo(presentacion, lotes_info, vendedor):
    """
    Devuelve stock a cada lote individualmente (inverso de _descontar_stock_fefo).
    `lotes_info` es una lista de dicts {'lote_id': int, 'cantidad': int}.
    """
    for info in lotes_info:
        lote = Lote.objects.get(pk=info['lote_id'])
        lote.stock_actual += info['cantidad']
        lote.save()


# ════════════════════════════════════════
# VENTAS
# ════════════════════════════════════════

@session_required
def ventas_lista(request):
    ventas     = Venta.objects.prefetch_related('detalles__producto', 'detalles__presentacion').order_by('-fecha')
    form       = VentaForm()
    categorias = Categoria.objects.prefetch_related('productos__presentaciones').all()
    clientes   = Cliente.objects.all().order_by('nombre')
    hoy        = timezone.localdate()
    total_dia  = int(sum(v.total_venta for v in Venta.objects.filter(fecha__date=hoy)))

    caja_abierta  = AperturaCaja.objects.filter(fecha=hoy).first()
    ultimo_cierre = CierreCaja.objects.filter(fecha=hoy).first()

    return render(request, 'ventas/ventas.html', {
        'ventas':          ventas,
        'form':            form,
        'categorias':      categorias,
        'clientes':        clientes,
        'total_dia':       total_dia,
        'hoy':             hoy,
        'caja_abierta':    caja_abierta,
        'ultimo_cierre':   ultimo_cierre,
        'billetes_denom':  BILLETES_DENOM,
        'monedas_denom':   MONEDAS_DENOM,
    })


@session_required
@transaction.atomic
def nueva_venta(request):
    if request.method != 'POST':
        return redirect('ventas:ventas_lista')

    producto_ids     = request.POST.getlist('producto_id[]')
    presentacion_ids = request.POST.getlist('presentacion_id[]')
    cantidades       = request.POST.getlist('cantidad[]')
    precios          = request.POST.getlist('precio[]')

    def to_decimal(key, default='0'):
        try:
            return Decimal(request.POST.get(key, default) or default)
        except (InvalidOperation, TypeError):
            return Decimal('0')

    descuento_pct      = to_decimal('descuento_porcentaje')
    pago_efectivo      = to_decimal('pago_efectivo')
    pago_tarjeta       = to_decimal('pago_tarjeta')
    pago_transferencia = to_decimal('pago_transferencia')
    pago_nequi         = to_decimal('pago_nequi')
    pago_daviplata     = to_decimal('pago_daviplata')

    if not producto_ids:
        messages.error(request, "El carrito está vacío.")
        return redirect('ventas:ventas_lista')

    cliente_id     = request.POST.get('cliente_id', '').strip()
    cliente_nombre = request.POST.get('cliente_nombre', 'Consumidor final').strip() or 'Consumidor final'

    if cliente_id:
        cliente = get_object_or_404(Cliente, pk=cliente_id)
    else:
        cliente, _ = Cliente.objects.get_or_create(nombre=cliente_nombre)

    vendedor    = None
    vendedor_id = request.session.get('usuario_id')
    if vendedor_id:
        vendedor = Usuario.objects.filter(pk=vendedor_id).first()

    # ── Fase 1: validación ───────────────────────────────────────────────────
    items_validados = []
    subtotal_venta  = Decimal('0')

    for i, prod_id in enumerate(producto_ids):
        try:
            cantidad = int(cantidades[i])
            precio   = Decimal(precios[i])
            if cantidad <= 0 or precio < 0:
                raise ValueError
        except (ValueError, TypeError, InvalidOperation, IndexError):
            messages.error(request, f"Datos inválidos en el ítem {i+1}.")
            return redirect('ventas:ventas_lista')

        try:
            producto = Producto.objects.prefetch_related('presentaciones').get(pk=prod_id)
        except Producto.DoesNotExist:
            messages.error(request, f"Producto {i+1} no encontrado.")
            return redirect('ventas:ventas_lista')

        pres_id      = presentacion_ids[i] if i < len(presentacion_ids) else ''
        presentacion = None

        if pres_id:
            try:
                presentacion = PresentacionProducto.objects.get(pk=pres_id, producto=producto)
            except PresentacionProducto.DoesNotExist:
                messages.error(request, f"Presentación inválida para {producto.nombre}.")
                return redirect('ventas:ventas_lista')

            # ① Validar contra stock_real (suma de Lote.stock_actual), no presentacion.cantidad
            if cantidad > presentacion.stock_real:
                messages.error(
                    request,
                    f"Stock insuficiente: solo hay {presentacion.stock_real} de '{presentacion.nombre}'."
                )
                return redirect('ventas:ventas_lista')
        else:
            if cantidad > producto.stock_total:
                messages.error(
                    request,
                    f"Stock insuficiente: solo hay {producto.stock_total} unidades de {producto.nombre}."
                )
                return redirect('ventas:ventas_lista')

        items_validados.append({
            'producto':     producto,
            'presentacion': presentacion,
            'cantidad':     cantidad,
            'precio':       precio,
        })
        subtotal_venta += precio * cantidad

    monto_descuento = (subtotal_venta * descuento_pct) / Decimal('100')
    total_final     = subtotal_venta - monto_descuento
    total_pagado    = pago_efectivo + pago_tarjeta + pago_transferencia + pago_nequi + pago_daviplata

    if total_pagado < total_final:
        messages.error(
            request,
            f"El total pagado (${total_pagado:,.0f}) no cubre el total (${total_final:,.0f}).".replace(',', '.')
        )
        return redirect('ventas:ventas_lista')

    # ── Fase 2: guardar venta ────────────────────────────────────────────────
    venta = Venta.objects.create(
        cliente=cliente,
        vendedor=vendedor,
        descuento_porcentaje=descuento_pct,
        total_con_descuento=total_final,
        pago_efectivo=pago_efectivo,
        pago_tarjeta=pago_tarjeta,
        pago_transferencia=pago_transferencia,
        pago_nequi=pago_nequi,
        pago_daviplata=pago_daviplata,
    )

    for item in items_validados:
        producto     = item['producto']
        presentacion = item['presentacion']
        cantidad     = item['cantidad']
        precio       = item['precio']

        detalle = DetalleVenta.objects.create(
            venta=venta,
            producto=producto,
            presentacion=presentacion,
            cantidad=cantidad,
            precio_unitario=precio,
        )

        if presentacion:
            # ② Descontar stock vía FEFO sobre Lote.stock_actual
            try:
                lotes_tocados = _descontar_stock_fefo(presentacion, cantidad, vendedor)
            except ValueError as e:
                messages.error(request, str(e))
                raise  # el @transaction.atomic hace rollback automático

            # ③ Un Inventario por cada lote tocado
            #    sin producto=, sin ubicacion=
            for lt in lotes_tocados:
                Inventario.objects.create(
                    presentacion=presentacion,
                    lote=lt['lote'],
                    registrado_por=vendedor,
                    vendedor=vendedor,
                    tipo='salida',
                    cantidad=lt['cantidad'],
                    motivo='Venta registrada',
                )
        else:
            # Producto sin presentación: comportamiento anterior intacto
            producto.cantidad_disponible -= cantidad
            producto.save()
            Inventario.objects.create(
                producto=producto,
                registrado_por=vendedor,
                tipo='salida',
                cantidad=cantidad,
                motivo='Venta registrada',
            )

    messages.success(request, f"Venta registrada — Total: ${total_final:,.0f}".replace(',', '.'))
    return redirect('ventas:ventas_lista')


@session_required
@transaction.atomic
def eliminar_venta(request, pk):
    venta = get_object_or_404(Venta, pk=pk)
    if request.method != 'POST':
        return redirect('ventas:ventas_lista')

    for det in venta.detalles.select_related('producto', 'presentacion').all():
        if det.presentacion:
            # ⑤ Restaurar stock a los lotes que generó esta venta (movimientos tipo 'salida')
            movimientos_salida = Inventario.objects.filter(
                presentacion=det.presentacion,
                tipo='salida',
                motivo='Venta registrada',
                # Filtramos por los movimientos asociados a este detalle a través de la venta
                # usando la fecha de la venta como ventana (o puedes agregar FK detalle si lo tienes)
            ).filter(
                # Si tu modelo Inventario tiene FK a DetalleVenta úsala aquí;
                # si no, filtramos por lotes que tienen stock y pertenecen a esta presentación.
                # La forma más robusta es guardar la FK al detalle en Inventario.
                # Por ahora reconstruimos desde los movimientos de la presentación en la venta.
                lote__presentacion=det.presentacion,
            ).filter(
                # Acotamos al momento de la venta (mismo segundo no es posible, usamos el día)
                fecha__date=venta.fecha.date(),
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

                # Movimiento de entrada granular por lote
                Inventario.objects.create(
                    presentacion=det.presentacion,
                    lote=lote,
                    tipo='entrada',
                    cantidad=info['cantidad'],
                    motivo='Anulación de venta',
                )
        else:
            det.producto.cantidad_disponible += det.cantidad
            det.producto.save()
            Inventario.objects.create(
                producto=det.producto,
                tipo='entrada',
                cantidad=det.cantidad,
                motivo='Anulación de venta',
            )

    venta.delete()
    messages.success(request, "Venta eliminada y stock restaurado.")
    return redirect('ventas:ventas_lista')


# ④ producto_stock_json devuelve stock_total y stock_real
def producto_stock_json(request, pk):
    producto = get_object_or_404(
        Producto.objects.prefetch_related('presentaciones'),
        pk=pk,
    )
    return JsonResponse({
        'stock':  producto.stock_total,   # propiedad/campo del modelo Producto
        'precio': float(producto.precio_unitario),
        'unidad': producto.unidad,
        'presentaciones': [
            {
                'id':         p.id,
                'nombre':     p.nombre,
                'unidades':   p.unidades,
                'cantidad':   p.stock_real,   # stock real desde lotes
                'precio':     float(p.precio),
            }
            for p in producto.presentaciones.all()
        ],
    })


# ════════════════════════════════════════
# VENTAS DEL DÍA
# ════════════════════════════════════════

@session_required
def ventas_dia(request):
    hoy = timezone.localdate()

    ventas = Venta.objects.prefetch_related(
        'detalles__producto', 'detalles__presentacion',
    ).filter(fecha__date=hoy).order_by('-fecha')

    ventas_list     = list(ventas)
    total_dia       = sum(v.total_venta for v in ventas_list)
    total_productos = sum(det.cantidad for v in ventas_list for det in v.detalles.all())

    caja_abierta  = AperturaCaja.objects.filter(fecha=hoy).first()
    ultimo_cierre = CierreCaja.objects.filter(fecha=hoy).first()

    return render(request, 'ventas/ventas_dia.html', {
        'ventas':          ventas,
        'total_dia':       total_dia,
        'total_productos': total_productos,
        'hoy':             hoy,
        'caja_abierta':    caja_abierta,
        'ultimo_cierre':   ultimo_cierre,
    })


# ════════════════════════════════════════
# CAJA — APERTURA Y CIERRE
# ════════════════════════════════════════

@require_POST
@session_required
def apertura_caja(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'JSON inválido.'}, status=400)

    hoy = timezone.localdate()

    if AperturaCaja.objects.filter(fecha=hoy).exists():
        return JsonResponse({'ok': False, 'error': 'Ya existe una apertura para hoy.'}, status=400)

    try:
        monto_base = float(data.get('monto_base', 0))
        if monto_base < 0:
            raise ValueError
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'Monto base inválido.'}, status=400)

    usuario = Usuario.objects.filter(pk=request.session.get('usuario_id')).first()

    AperturaCaja.objects.create(
        fecha=hoy,
        monto_base=monto_base,
        usuario=usuario,
        observacion=data.get('observacion', ''),
        denominaciones=data.get('denominaciones', {}),
    )
    return JsonResponse({'ok': True})


@require_POST
@session_required
def cierre_caja(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'JSON inválido.'}, status=400)

    hoy      = timezone.localdate()
    apertura = AperturaCaja.objects.filter(fecha=hoy).first()

    if not apertura:
        return JsonResponse({'ok': False, 'error': 'No hay apertura de caja para hoy.'}, status=400)

    if CierreCaja.objects.filter(fecha=hoy).exists():
        return JsonResponse({'ok': False, 'error': 'La caja ya fue cerrada hoy.'}, status=400)

    try:
        total_contado  = float(data.get('total_contado', 0))
        monto_base_sig = float(data.get('monto_base_siguiente', 0))
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'Valores numéricos inválidos.'}, status=400)

    # El "total a retirar" se calcula aquí en el servidor (contado - base para
    # mañana) en vez de confiar en un valor que mande el cliente: el front no
    # lo estaba enviando, así que siempre quedaba guardado como 0.
    total_retirado = max(0.0, total_contado - monto_base_sig)

    CierreCaja.objects.create(
        fecha=hoy,
        apertura=apertura,
        total_contado=total_contado,
        monto_base_siguiente=monto_base_sig,
        total_retirado=total_retirado,
        denominaciones=data.get('denominaciones', {}),
    )
    return JsonResponse({'ok': True})


# ════════════════════════════════════════
# CONTEO DE APERTURA
# ════════════════════════════════════════

@require_POST
@session_required
def registrar_conteo(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'JSON inválido.'}, status=400)

    hoy = timezone.localdate()

    if AperturaCaja.objects.filter(fecha=hoy).exists():
        return JsonResponse({'ok': False, 'error': 'Ya existe un conteo de apertura para hoy.'}, status=400)

    try:
        monto_contado = float(data.get('monto_contado', 0))
        if monto_contado < 0:
            raise ValueError
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'Monto inválido.'}, status=400)

    usuario = Usuario.objects.filter(pk=request.session.get('usuario_id')).first()

    AperturaCaja.objects.create(
        fecha=hoy,
        monto_base=monto_contado,
        usuario=usuario,
        observacion=data.get('observacion', ''),
        denominaciones=data.get('denominaciones', {}),
    )
    return JsonResponse({'ok': True})


# ════════════════════════════════════════
# DEVOLUCIONES
# ════════════════════════════════════════

@session_required
def lista_devoluciones(request):
    devoluciones = Devolucion.objects.select_related('venta').prefetch_related(
        'detalles__producto', 'detalles__presentacion'
    )
    return render(request, 'ventas/devoluciones.html', {'devoluciones': devoluciones})


@session_required
def buscar_venta_devolucion(request):
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse({'ventas': []})

    ventas = Venta.objects.filter(cliente__nombre__icontains=q).order_by('-fecha')[:10]
    if q.isdigit():
        ventas = (Venta.objects.filter(pk=int(q)) | ventas).distinct()

    return JsonResponse({'ventas': [
        {'id': v.pk, 'cliente': v.cliente.nombre,
         'fecha': v.fecha.strftime('%d/%m/%Y %H:%M'), 'total': float(v.total_venta)}
        for v in ventas
    ]})


@session_required
def detalle_venta_devolucion(request, venta_id):
    venta = get_object_or_404(Venta, pk=venta_id)
    return JsonResponse({
        'venta_id':  venta.pk,
        'cliente':   venta.cliente.nombre,
        'fecha':     venta.fecha.strftime('%d/%m/%Y %H:%M'),
        'total':     float(venta.total_venta),
        'descuento': float(venta.descuento_porcentaje),
        'detalles': [
            {
                'detalle_id':      d.pk,
                'producto_id':     d.producto.pk,
                'producto':        d.producto.nombre,
                'presentacion_id': d.presentacion.pk if d.presentacion else None,
                'presentacion':    d.presentacion.nombre if d.presentacion else '',
                'cantidad':        d.cantidad,
                'precio':          float(d.precio_unitario),
                'subtotal':        float(d.subtotal()),
            }
            for d in venta.detalles.select_related('producto', 'presentacion').all()
        ],
    })


@session_required
@transaction.atomic
def registrar_devolucion(request):
    if request.method != 'POST':
        return redirect('ventas:lista_devoluciones')

    venta_id          = request.POST.get('venta_id')
    tiene_comprobante = request.POST.get('tiene_comprobante') == '1'
    restaurar_stock   = request.POST.get('restaurar_stock') == '1'
    motivo            = request.POST.get('motivo', 'otro')
    observaciones     = request.POST.get('observaciones', '')
    producto_ids      = request.POST.getlist('producto_id[]')
    presentacion_ids  = request.POST.getlist('presentacion_id[]')
    cantidades        = request.POST.getlist('cantidad[]')
    precios           = request.POST.getlist('precio[]')

    if not tiene_comprobante:
        messages.warning(request, 'No se puede registrar la devolución sin comprobante de compra.')
        return redirect('ventas:lista_devoluciones')

    venta          = get_object_or_404(Venta, pk=venta_id)
    total_devuelto = sum(int(cantidades[i]) * float(precios[i]) for i in range(len(producto_ids)))

    devolucion = Devolucion.objects.create(
        venta=venta, motivo=motivo, observaciones=observaciones,
        restaurar_stock=restaurar_stock, tiene_comprobante=tiene_comprobante,
        total_devuelto=total_devuelto,
    )

    for i in range(len(producto_ids)):
        producto     = get_object_or_404(Producto, pk=producto_ids[i])
        presentacion = None
        if presentacion_ids[i] and presentacion_ids[i] != 'null':
            presentacion = PresentacionProducto.objects.filter(pk=presentacion_ids[i]).first()

        cantidad = int(cantidades[i])
        precio   = float(precios[i])

        DetalleDevolucion.objects.create(
            devolucion=devolucion, producto=producto, presentacion=presentacion,
            cantidad=cantidad, precio_unitario=precio,
        )
        if restaurar_stock and presentacion:
            presentacion.cantidad += cantidad
            presentacion.save()

    messages.success(request, f'Devolución {devolucion.numero} registrada correctamente.')
    return redirect('ventas:comprobante_devolucion', pk=devolucion.pk)


@session_required
def comprobante_devolucion(request, pk):
    devolucion = get_object_or_404(
        Devolucion.objects.select_related('venta').prefetch_related(
            'detalles__producto', 'detalles__presentacion'
        ), pk=pk,
    )
    return render(request, 'ventas/comprobante_devolucion.html', {'devolucion': devolucion})