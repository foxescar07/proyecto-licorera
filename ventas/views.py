from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone
from django.views.decorators.http import require_POST
from decimal import Decimal, InvalidOperation
from functools import wraps
import json

from .models import Venta, DetalleVenta, AperturaCaja, CierreCaja, Devolucion, DetalleDevolucion, Cliente
from .forms import VentaForm, DetalleVentaForm, DevolucionForm
from productos.models import Producto, Categoria, PresentacionProducto
from inventario.models import Inventario
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
            if cantidad > presentacion.cantidad:
                messages.error(request, f"Stock insuficiente: solo hay {presentacion.cantidad} de {producto.nombre}.")
                return redirect('ventas:ventas_lista')
        else:
            if cantidad > producto.cantidad_disponible:
                messages.error(request, f"Stock insuficiente: solo hay {producto.cantidad_disponible} unidades de {producto.nombre}.")
                return redirect('ventas:ventas_lista')

        items_validados.append({
            'producto': producto, 'presentacion': presentacion,
            'cantidad': cantidad, 'precio': precio,
        })
        subtotal_venta += precio * cantidad

    monto_descuento = (subtotal_venta * descuento_pct) / Decimal('100')
    total_final     = subtotal_venta - monto_descuento
    total_pagado    = pago_efectivo + pago_tarjeta + pago_transferencia + pago_nequi + pago_daviplata

    if total_pagado < total_final:
        messages.error(request, f"El total pagado (${total_pagado:,.0f}) no cubre el total (${total_final:,.0f}).".replace(',', '.'))
        return redirect('ventas:ventas_lista')

    venta = Venta(
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
    venta.save()

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
            presentacion.cantidad -= cantidad
            presentacion.save()
            unidades = cantidad * presentacion.unidades
        else:
            producto.cantidad_disponible -= cantidad
            producto.save()
            unidades = cantidad

        Inventario.objects.create(
            producto=producto, tipo='salida', cantidad=unidades,
            motivo='Venta registrada', ubicacion='Venta',
        )

    messages.success(request, f"Venta registrada — Total: ${total_final:,.0f}".replace(',', '.'))
    return redirect('ventas:ventas_lista')


@session_required
def eliminar_venta(request, pk):
    venta = get_object_or_404(Venta, pk=pk)
    if request.method == 'POST':
        for det in venta.detalles.all():
            if det.presentacion:
                det.presentacion.cantidad += det.cantidad
                det.presentacion.save()
                unidades = det.cantidad * det.presentacion.unidades
            else:
                det.producto.cantidad_disponible += det.cantidad
                det.producto.save()
                unidades = det.cantidad

            Inventario.objects.create(
                producto=det.producto, tipo='entrada', cantidad=unidades,
                motivo='Anulación de venta', ubicacion='Devolución',
            )
        venta.delete()
        messages.success(request, "Venta eliminada y stock restaurado.")
    return redirect('ventas:ventas_lista')


def producto_stock_json(request, pk):
    producto = get_object_or_404(Producto.objects.prefetch_related('presentaciones'), pk=pk)
    return JsonResponse({
        'stock':  producto.cantidad_disponible,
        'precio': float(producto.precio_unitario),
        'unidad': producto.unidad,
        'presentaciones': [
            {'id': p.id, 'nombre': p.nombre, 'unidades': p.unidades,
             'cantidad': p.cantidad, 'precio': float(p.precio)}
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

    total_dia       = sum(v.total_venta for v in ventas)
    total_productos = sum(det.cantidad for v in ventas for det in v.detalles.all())

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
        total_retirado = float(data.get('total_retirado', 0))
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'Valores numéricos inválidos.'}, status=400)

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
    """Lista principal de devoluciones con flujo integrado"""
    # Reiniciar flujo si viene desde el botón "Nueva devolución"
    if request.GET.get('nuevo'):
        request.session['dev_paso'] = 1
        for key in list(request.session.keys()):
            if key.startswith('dev_'):
                del request.session[key]

    return devoluciones_flujo(request)


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
                request.session['dev_venta_id'] = venta.pk
                request.session['dev_paso'] = 2
                request.session.modified = True
                return redirect('ventas:lista_devoluciones')
            except (Venta.DoesNotExist, ValueError):
                messages.error(request, '⚠️ Selecciona una venta válida.')
        else:
            messages.error(request, '⚠️ Debes seleccionar una venta.')

    # PASO 2: Seleccionar productos
    elif request.method == 'POST' and paso == 2:
        if not venta_id:
            messages.error(request, '⚠️ Primero debes seleccionar una venta.')
            request.session['dev_paso'] = 1
            request.session.modified = True
            return redirect('ventas:lista_devoluciones')

        productos_ids = request.POST.getlist('producto_id')
        if productos_ids:
            request.session['dev_productos'] = [int(pid) for pid in productos_ids]
            request.session['dev_paso'] = 3
            request.session.modified = True
            return redirect('ventas:lista_devoluciones')
        else:
            messages.error(request, '⚠️ Debes seleccionar al menos un producto para devolver.')

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
            request.session['dev_paso'] = 5
            request.session.modified = True
            return redirect('ventas:lista_devoluciones')
        else:
            messages.error(request, '⚠️ Selecciona un tipo de reembolso válido.')

    # PASO 5: Confirmar y crear devolución
    elif request.method == 'POST' and paso == 5:
        try:
            venta = Venta.objects.get(pk=venta_id)
            productos_ids = request.session.get('dev_productos', [])
            motivo = request.session.get('dev_motivo')
            tipo_reembolso = request.session.get('dev_tipo_reembolso')
            observaciones = request.session.get('dev_observaciones', '')

            if not (venta and productos_ids and motivo and tipo_reembolso):
                messages.error(request, '⚠️ Error: Datos incompletos. Reinicia el proceso.')
                request.session['dev_paso'] = 1
                request.session.modified = True
                return redirect('ventas:lista_devoluciones')

            # Calcular total devuelto
            total_devuelto = Decimal('0')
            detalles_venta = venta.detalles.filter(pk__in=productos_ids)

            if not detalles_venta.exists():
                messages.error(request, '⚠️ Los productos seleccionados no están disponibles.')
                request.session['dev_paso'] = 2
                request.session.modified = True
                return redirect('ventas:lista_devoluciones')

            for detalle in detalles_venta:
                total_devuelto += detalle.subtotal()

            # Crear devolución
            devolucion = Devolucion.objects.create(
                venta=venta,
                motivo=motivo,
                tipo_reembolso=tipo_reembolso,
                observaciones=observaciones,
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
    if venta_id:
        try:
            venta = Venta.objects.get(pk=venta_id)
            detalles_venta = venta.detalles.select_related('producto', 'presentacion').all()
        except Venta.DoesNotExist:
            venta = None

    # Obtener nombres de motivos y tipos para mostrar
    motivo_dict = dict(Devolucion.MOTIVO_CHOICES)
    tipo_dict = dict(Devolucion.REEMBOLSO_CHOICES)

    context = {
        'ventas': ventas,
        'venta': venta,
        'detalles_venta': detalles_venta,
        'devoluciones': devoluciones,
        'paso': paso,
        'motivo_seleccionado': motivo_dict.get(request.session.get('dev_motivo'), ''),
        'tipo_reembolso_seleccionado': tipo_dict.get(request.session.get('dev_tipo_reembolso'), ''),
        'observaciones': request.session.get('dev_observaciones', ''),
    }

    return render(request, 'ventas/devoluciones.html', context)


