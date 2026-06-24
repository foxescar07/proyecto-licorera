from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction 
from django.db.models import Sum
from django.utils import timezone
from django.views.decorators.http import require_POST
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

    usuario_id    = request.session.get('usuario_id')
    caja_abierta  = AperturaCaja.objects.filter(fecha=hoy, usuario_id=usuario_id).first()
    ultimo_cierre = CierreCaja.objects.filter(fecha=hoy, usuario_id=usuario_id).first()

    # Catálogo serializado para el TPV
    catalogo = []
    for cat in categorias:
        productos_list = []
        for prod in cat.productos.all():
            presentaciones_list = []
            for pr in prod.presentaciones.all():
                presentaciones_list.append({
                    'id':       pr.id,
                    'nombre':   pr.nombre,
                    'precio':   float(pr.precio),
                    'unidades': pr.unidades,
                    'stock':    pr.stock_real,
                })
            productos_list.append({
                'id':             prod.id,
                'nombre':         prod.nombre,
                'stock':          prod.stock_total,
                'presentaciones': presentaciones_list,
            })
        catalogo.append({
            'id':       cat.id,
            'nombre':   cat.nombre,
            'productos': productos_list,
        })

    import json as _json
    catalogo_json = _json.dumps(catalogo, ensure_ascii=False)

    context = {
        'ventas':         ventas,
        'form':           form,
        'categorias':     categorias,
        'clientes':       clientes,
        'total_dia':      total_dia,
        'hoy':            hoy,
        'caja_abierta':   caja_abierta,
        'ultimo_cierre':  ultimo_cierre,
        'billetes_denom': BILLETES_DENOM,
        'monedas_denom':  MONEDAS_DENOM,
        'catalogo_json':  catalogo_json,
    }
    return render(request, 'ventas/ventas.html', context)


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
    pago_nequi        = to_decimal('pago_nequi')
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

            if cantidad > presentacion.stock_real:
                messages.error(request, f"Stock insuficiente: solo hay {presentacion.stock_real} de '{presentacion.nombre}'.")
                return redirect('ventas:ventas_lista')
        else:
            if cantidad > producto.stock_total:
                messages.error(request, f"Stock insuficiente: solo hay {producto.stock_total} unidades de {producto.nombre}.")
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
        messages.error(request, f"El total pagado (${total_pagado:,.0f}) no cubre el total (${total_final:,.0f}).".replace(',', '.'))
        return redirect('ventas:ventas_lista')

    venta = Venta.objects.create(
        cliente=cliente, vendedor=vendedor, descuento_porcentaje=descuento_pct,
        total_con_descuento=total_final, pago_efectivo=pago_efectivo, pago_tarjeta=pago_tarjeta,
        pago_transferencia=pago_transferencia, pago_nequi=pago_nequi, pago_daviplata=pago_daviplata,
    )

    for item in items_validados:
        producto     = item['producto']
        presentacion = item['presentacion']
        cantidad     = item['cantidad']
        precio       = item['precio']

        DetalleVenta.objects.create(
            venta=venta, producto=producto, presentacion=presentacion,
            cantidad=cantidad, precio_unitario=precio,
        )

        if presentacion:
            try:
                lotes_tocados = _descontar_stock_fefo(presentacion, cantidad, vendedor)
            except ValueError as e:
                messages.error(request, str(e))
                raise

            for lt in lotes_tocados:
                Inventario.objects.create(
                    presentacion=presentacion, lote=lt['lote'], registrado_por=vendedor,
                    tipo='salida', cantidad=lt['cantidad'], motivo='Venta registrada',
                )
        else:
            producto.cantidad_disponible -= cantidad
            producto.save()
            Inventario.objects.create(
                producto=producto, registrado_por=vendedor,
                tipo='salida', cantidad=cantidad, motivo='Venta registrada',
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
            movimientos_salida = Inventario.objects.filter(
                presentacion=det.presentacion, tipo='salida', motivo='Venta registrada',
                lote__presentacion=det.presentacion, fecha__date=venta.fecha.date(),
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
                    presentacion=det.presentacion, lote=lote, tipo='entrada',
                    cantidad=info['cantidad'], motivo='Anulación de venta',
                )
        else:
            det.producto.cantidad_disponible += det.cantidad
            det.producto.save()
            Inventario.objects.create(
                producto=det.producto, tipo='entrada', cantidad=det.cantidad, motivo='Anulación de venta',
            )

    venta.delete()
    messages.success(request, "Venta eliminada y stock restaurado.")
    return redirect('ventas:ventas_lista')


def producto_stock_json(request, pk):
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
        'detalles__producto', 'detalles__presentacion'
    ).order_by('-fecha')

    total_dia       = int(sum(v.total_con_descuento for v in ventas))
    total_productos = sum(
        det.cantidad
        for v in ventas
        for det in v.detalles.all()
    )

    context = {
        'ventas':          ventas,
        'hoy':             hoy,
        'total_dia':       total_dia,
        'total_productos': total_productos,
    }
    return render(request, 'ventas/ventas_dia.html', context)


# ════════════════════════════════════════
# CONTROL DE CAJA
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

        if AperturaCaja.objects.filter(fecha=hoy, usuario_id=usuario_id).exists():
            return JsonResponse({'ok': False, 'error': 'Ya hay una caja abierta hoy.'})

        AperturaCaja.objects.create(
            fecha=hoy,
            usuario_id=usuario_id,
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

        apertura = AperturaCaja.objects.filter(fecha=hoy, usuario_id=usuario_id).first()
        if not apertura:
            return JsonResponse({'ok': False, 'error': 'No hay caja abierta.'})

        if hasattr(apertura, 'cierre'):
            return JsonResponse({'ok': False, 'error': 'La caja ya fue cerrada hoy.'})

        total_retirado = max(0, float(total_contado) - float(monto_base_siguiente))

        CierreCaja.objects.create(
            fecha=hoy,
            apertura=apertura,
            usuario_id=usuario_id,
            total_contado=total_contado,
            monto_base_siguiente=monto_base_siguiente,
            total_retirado=total_retirado,
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
    """Lista principal de devoluciones con flujo integrado"""
    try:
        # Reiniciar flujo si viene desde el botón "Nueva devolución"
        if request.GET.get('nuevo'):
            request.session['dev_paso'] = 1
            # Limpiar todas las variables de devolución previas
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
def seleccionar_venta_devolucion(request, venta_id):
    """Selecciona venta y muestra formulario de devolución"""
    venta = get_object_or_404(Venta, pk=venta_id)
    form = DevolucionForm() if request.method == 'GET' else DevolucionForm(request.POST)

    context = {
        'venta': venta,
        'detalles_venta': venta.detalles.select_related('producto', 'presentacion'),
        'form': form,
        'devoluciones': Devolucion.objects.select_related('venta'),
    }

    return render(request, 'ventas/devoluciones.html', context)


@session_required
@transaction.atomic
def registrar_devolucion(request, venta_id):
    """Registra la devolución con los productos y detalles seleccionados"""
    if request.method != 'POST':
        return redirect('ventas:lista_devoluciones')

    venta = get_object_or_404(Venta, pk=venta_id)
    form = DevolucionForm(request.POST)

    # Obtener detalles seleccionados
    detalles_seleccionados = request.POST.getlist('detalle_id')

    if not detalles_seleccionados:
        messages.error(request, '⚠️ Debes seleccionar al menos un producto para devolver.')
        return redirect('ventas:seleccionar_venta_devolucion', venta_id=venta_id)

    if not form.is_valid():
        messages.error(request, '⚠️ Debes completar todos los campos obligatorios.')
        return redirect('ventas:seleccionar_venta_devolucion', venta_id=venta_id)

    # Calcular total devuelto
    total_devuelto = Decimal('0')
    detalles_venta = venta.detalles.filter(pk__in=detalles_seleccionados)

    for detalle in detalles_venta:
        total_devuelto += detalle.subtotal()

    # Crear devolución
    devolucion = Devolucion.objects.create(
        venta=venta,
        motivo=form.cleaned_data['motivo'],
        tipo_reembolso=form.cleaned_data['tipo_reembolso'],
        observaciones=form.cleaned_data['observaciones'],
        total_devuelto=total_devuelto,
        tiene_comprobante=True,
        restaurar_stock=True,
    )

    # Crear detalles de devolución
    for detalle_venta in detalles_venta:
        DetalleDevolucion.objects.create(
            devolucion=devolucion,
            producto=detalle_venta.producto,
            presentacion=detalle_venta.presentacion,
            cantidad=detalle_venta.cantidad,
            precio_unitario=detalle_venta.precio_unitario,
        )

        # Restaurar stock
        if detalle_venta.presentacion:
            detalle_venta.presentacion.cantidad += detalle_venta.cantidad
            detalle_venta.presentacion.save()

    messages.success(request, f'✅ Devolución {devolucion.numero} registrada correctamente.')
    return redirect('ventas:comprobante_devolucion', pk=devolucion.pk)


@session_required
def comprobante_devolucion(request, pk):
    devolucion = get_object_or_404(
        Devolucion.objects.select_related('venta').prefetch_related(
            'detalles__producto', 'detalles__presentacion'
        ), pk=pk,
    )
    return render(request, 'ventas/comprobante_devolucion.html', {'devolucion': devolucion})


# FLUJO DE DEVOLUCIONES - 100% SERVER-SIDE SIN JAVASCRIPT
@session_required
def devoluciones_flujo(request):
    """Maneja TODO el flujo de devoluciones en un único HTML - Sin JavaScript"""
    paso = request.session.get('dev_paso', 1)
    venta_id = request.session.get('dev_venta_id')

    # PASO 1: Seleccionar venta
    if request.method == 'POST' and paso == 1:
        venta_id_post = request.POST.get('venta_id', '').strip()

        if venta_id_post:
            try:
                venta = Venta.objects.get(pk=int(venta_id_post))
                request.session['dev_venta_id'] = int(venta_id_post)
                request.session['dev_paso'] = 2
                request.session.modified = True
                messages.success(request, f'✅ Venta seleccionada: {venta.cliente.nombre}')
                return redirect('ventas:lista_devoluciones')
            except (Venta.DoesNotExist, ValueError) as e:
                messages.error(request, '⚠️ Venta no válida. Intenta nuevamente.')
        else:
            messages.error(request, '⚠️ Debes seleccionar una venta.')

    # PASO 2: Seleccionar productos y cantidades
    elif request.method == 'POST' and paso == 2:
        if not venta_id:
            messages.error(request, '⚠️ Primero debes seleccionar una venta.')
            request.session['dev_paso'] = 1
            request.session.modified = True
            return redirect('ventas:lista_devoluciones')

        productos_ids = request.POST.getlist('producto_id')
        if not productos_ids:
            messages.error(request, '⚠️ Debes seleccionar al menos un producto para devolver.')
            return redirect('ventas:lista_devoluciones')

        # Procesar cantidades de devolución
        productos_con_cantidad = {}
        venta_actual = Venta.objects.get(pk=venta_id)

        for detalle_id in productos_ids:
            try:
                detalle_id_int = int(detalle_id)
                cantidad_str = request.POST.get(f'cantidad_devolucion_{detalle_id_int}', '0')
                cantidad = int(cantidad_str)

                # Validar cantidad
                detalle = venta_actual.detalles.get(pk=detalle_id_int)
                if cantidad <= 0 or cantidad > detalle.cantidad:
                    messages.error(request, f'⚠️ Cantidad inválida para {detalle.producto.nombre}. Debe ser entre 1 y {detalle.cantidad}.')
                    return redirect('ventas:lista_devoluciones')

                productos_con_cantidad[detalle_id_int] = cantidad

            except (ValueError, TypeError, DetalleVenta.DoesNotExist):
                messages.error(request, '⚠️ Error al procesar las cantidades. Intenta nuevamente.')
                return redirect('ventas:lista_devoluciones')

        if productos_con_cantidad:
            request.session['dev_productos'] = productos_con_cantidad
            request.session['dev_paso'] = 3
            request.session.modified = True
            return redirect('ventas:lista_devoluciones')
        else:
            messages.error(request, '⚠️ Debes especificar al menos 1 unidad para devolver.')

    # PASO 3: Motivo de devolución
    elif request.method == 'POST' and paso == 3:
        motivo = request.POST.get('motivo', '').strip()
        observaciones = request.POST.get('observaciones', '').strip()

        motivos_validos = [choice[0] for choice in Devolucion.MOTIVO_CHOICES]
        if motivo in motivos_validos:
            request.session['dev_motivo'] = motivo
            request.session['dev_observaciones'] = observaciones
            request.session['dev_paso'] = 4
            request.session.modified = True
            return redirect('ventas:lista_devoluciones')
        else:
            messages.error(request, '⚠️ Selecciona un motivo válido.')

    # PASO 4: Tipo de reembolso
    elif request.method == 'POST' and paso == 4:
        tipo_reembolso = request.POST.get('tipo_reembolso', '').strip()

        tipos_validos = [choice[0] for choice in Devolucion.REEMBOLSO_CHOICES]
        if tipo_reembolso in tipos_validos:
            request.session['dev_tipo_reembolso'] = tipo_reembolso
            # Pasos adicionales según tipo
            if tipo_reembolso == 'cambio':
                request.session['dev_paso'] = 5
            elif tipo_reembolso == 'reembolso':
                request.session['dev_paso'] = 5
            else:  # nota_credito
                request.session['dev_paso'] = 6  # Ir a evidencia fotográfica
            request.session.modified = True
            return redirect('ventas:lista_devoluciones')
        else:
            messages.error(request, '⚠️ Selecciona un tipo de reembolso válido.')

    # PASO 5: Detalles específicos según tipo (Cambio o Reembolso)
    elif request.method == 'POST' and paso == 5:
        tipo_reembolso = request.session.get('dev_tipo_reembolso')

        if tipo_reembolso == 'cambio':
            producto_cambio_id = request.POST.get('producto_cambio', '').strip()
            cantidad_cambio = request.POST.get('cantidad_cambio', '').strip()

            if producto_cambio_id and cantidad_cambio:
                try:
                    request.session['dev_producto_cambio_id'] = int(producto_cambio_id)
                    request.session['dev_cantidad_cambio'] = int(cantidad_cambio)
                    request.session['dev_paso'] = 6
                    request.session.modified = True
                    return redirect('ventas:lista_devoluciones')
                except (ValueError, TypeError):
                    messages.error(request, '⚠️ Datos inválidos. Intenta nuevamente.')
            else:
                messages.error(request, '⚠️ Debes seleccionar un producto de reemplazo y cantidad.')

        elif tipo_reembolso == 'reembolso':
            metodo_devolucion = request.POST.get('metodo_pago_devolucion', '').strip()

            metodos_validos = [choice[0] for choice in Devolucion._meta.get_field('metodo_pago_devolucion').choices]
            if metodo_devolucion in metodos_validos:
                request.session['dev_metodo_devolucion'] = metodo_devolucion
                request.session['dev_paso'] = 6
                request.session.modified = True
                return redirect('ventas:lista_devoluciones')
            else:
                messages.error(request, '⚠️ Selecciona un método de devolución válido.')

    # PASO 6: Evidencia fotográfica
    elif request.method == 'POST' and paso == 6:
        # Procesar archivos de evidencia si existen
        request.session['dev_paso'] = 7
        request.session.modified = True
        return redirect('ventas:lista_devoluciones')

    # PASO 7: Confirmación y crear devolución
    elif request.method == 'POST' and paso == 7:
        try:
            venta = Venta.objects.get(pk=venta_id)
            productos_data = request.session.get('dev_productos', {})
            motivo = request.session.get('dev_motivo')
            tipo_reembolso = request.session.get('dev_tipo_reembolso')
            observaciones = request.session.get('dev_observaciones', '')

            # Convertir lista antigua a diccionario si es necesario
            if isinstance(productos_data, list):
                productos_con_cantidad = {pid: venta.detalles.get(pk=pid).cantidad if venta.detalles.filter(pk=pid).exists() else 1 for pid in productos_data}
            else:
                productos_con_cantidad = productos_data

            if not (venta and productos_con_cantidad and motivo and tipo_reembolso):
                messages.error(request, '⚠️ Error: Datos incompletos. Reinicia el proceso.')
                request.session['dev_paso'] = 1
                request.session.modified = True
                return redirect('ventas:lista_devoluciones')

            # Convertir claves de string a int si es necesario
            if productos_con_cantidad:
                keys_list = list(productos_con_cantidad.keys())
                if keys_list and isinstance(keys_list[0], str):
                    productos_con_cantidad = {int(k): v for k, v in productos_con_cantidad.items()}

            # Calcular total devuelto
            total_devuelto = Decimal('0')
            detalles_venta = venta.detalles.filter(pk__in=productos_con_cantidad.keys())

            if not detalles_venta.exists():
                messages.error(request, '⚠️ Los productos seleccionados no están disponibles.')
                request.session['dev_paso'] = 2
                request.session.modified = True
                return redirect('ventas:lista_devoluciones')

            for detalle in detalles_venta:
                cantidad_devolucion = productos_con_cantidad.get(detalle.pk, detalle.cantidad)
                subtotal = Decimal(str(cantidad_devolucion)) * detalle.precio_unitario
                total_devuelto += subtotal

            # Crear devolución con datos base
            devolucion = Devolucion.objects.create(
                venta=venta,
                motivo=motivo,
                tipo_reembolso=tipo_reembolso,
                observaciones=observaciones,
                total_devuelto=total_devuelto,
                tiene_comprobante=True,
                restaurar_stock=True,
            )

            # Procesar según tipo de reembolso
            if tipo_reembolso == 'cambio':
                producto_cambio_id = request.session.get('dev_producto_cambio_id')
                cantidad_cambio = request.session.get('dev_cantidad_cambio')

                if producto_cambio_id:
                    try:
                        producto_cambio = Producto.objects.get(pk=producto_cambio_id)
                        devolucion.producto_cambio = producto_cambio
                        devolucion.cantidad_cambio = cantidad_cambio or 1
                        devolucion.save()
                        messages.info(request, f'📦 Cambio programado: {producto_cambio.nombre} x{devolucion.cantidad_cambio}')
                    except Producto.DoesNotExist:
                        pass

            elif tipo_reembolso == 'nota_credito':
                devolucion.saldo_credito = total_devuelto
                devolucion.save()
                messages.info(request, f'💳 Nota de crédito por ${total_devuelto:,.0f} generada'.replace(',', '.'))

            elif tipo_reembolso == 'reembolso':
                metodo_devolucion = request.session.get('dev_metodo_devolucion')
                devolucion.metodo_pago_devolucion = metodo_devolucion
                devolucion.save()
                messages.info(request, f'💰 Reembolso programado: ${total_devuelto:,.0f} a {metodo_devolucion}'.replace(',', '.'))

            # Crear detalles de devolución con cantidades especificadas
            for detalle_venta in detalles_venta:
                cantidad_devolucion = productos_con_cantidad.get(detalle_venta.pk, detalle_venta.cantidad)
                DetalleDevolucion.objects.create(
                    devolucion=devolucion,
                    producto=detalle_venta.producto,
                    presentacion=detalle_venta.presentacion,
                    cantidad=cantidad_devolucion,
                    precio_unitario=detalle_venta.precio_unitario,
                )

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
            request.session.modified = True
            return redirect('ventas:lista_devoluciones')

    # Botón atrás
    if request.method == 'POST' and request.POST.get('action') == 'atras':
        nuevo_paso = max(1, paso - 1)
        request.session['dev_paso'] = nuevo_paso
        request.session.modified = True
        return redirect('ventas:lista_devoluciones')

    # Obtener datos para renderizar
    ventas = Venta.objects.select_related('cliente').prefetch_related('detalles').order_by('-fecha')
    devoluciones = Devolucion.objects.select_related('venta').prefetch_related('detalles').order_by('-fecha')

    venta = None
    detalles_venta = []
    detalles_con_estado = []  # Detalles con información de devoluciones

    if venta_id:
        try:
            venta = Venta.objects.prefetch_related(
                'detalles__producto',
                'detalles__presentacion'
            ).get(pk=venta_id)

            detalles_venta = venta.detalles.select_related('producto', 'presentacion').all()

            # Calcular cantidades devueltas para cada detalle
            from django.db.models import Sum # type: ignore
            for detalle in detalles_venta:
                cantidad_devuelta = DetalleDevolucion.objects.filter(
                    devolucion__venta=venta,
                    presentacion=detalle.presentacion
                ).aggregate(total=Sum('cantidad'))['total'] or 0

                cantidad_pendiente = detalle.cantidad - cantidad_devuelta
                puede_devolver = cantidad_pendiente > 0

                detalles_con_estado.append({
                    'detalle': detalle,
                    'cantidad_devuelta': cantidad_devuelta,
                    'cantidad_pendiente': cantidad_pendiente,
                    'puede_devolver': puede_devolver,
                })
        except (Venta.DoesNotExist, ValueError, TypeError):
            venta = None
            # Reiniciar si hay error
            request.session['dev_paso'] = 1
            request.session.modified = True

    # Obtener nombres de motivos y tipos para mostrar
    motivo_dict = dict(Devolucion.MOTIVO_CHOICES)
    tipo_dict = dict(Devolucion.REEMBOLSO_CHOICES)
    metodos_dict = dict(Devolucion._meta.get_field('metodo_pago_devolucion').choices)

    # Para paso 5 y 6: obtener productos disponibles
    productos = Producto.objects.all() if paso >= 5 else []

    # Calcular total a devolver para mostrar en paso 5-6
    total_devolver = Decimal('0')
    if venta_id:
        productos_data = request.session.get('dev_productos', {})

        # Convertir lista antigua a diccionario si es necesario
        if isinstance(productos_data, list):
            productos_con_cantidad = {pid: venta.detalles.get(pk=pid).cantidad if venta.detalles.filter(pk=pid).exists() else 1 for pid in productos_data}
        else:
            productos_con_cantidad = productos_data

        if productos_con_cantidad and len(productos_con_cantidad) > 0:
            # Convertir claves de string a int si es necesario
            keys_list = list(productos_con_cantidad.keys())
            if keys_list and isinstance(keys_list[0], str):
                productos_con_cantidad = {int(k): v for k, v in productos_con_cantidad.items()}

            detalles = venta.detalles.filter(pk__in=productos_con_cantidad.keys())
            for d in detalles:
                cantidad = productos_con_cantidad.get(d.pk, d.cantidad)
                total_devolver += Decimal(str(cantidad)) * d.precio_unitario

    context = {
        'ventas': ventas,
        'venta': venta,
        'detalles_venta': detalles_venta,
        'detalles_con_estado': detalles_con_estado,
        'devoluciones': devoluciones,
        'paso': paso,
        'motivo_seleccionado': motivo_dict.get(request.session.get('dev_motivo'), ''),
        'tipo_reembolso_seleccionado': tipo_dict.get(request.session.get('dev_tipo_reembolso'), ''),
        'observaciones': request.session.get('dev_observaciones', ''),
        'productos': productos,
        'total_devolver': total_devolver,
        'metodo_pago_original': request.session.get('dev_metodo_original', ''),
    }

    return render(request, 'ventas/devoluciones.html', context)