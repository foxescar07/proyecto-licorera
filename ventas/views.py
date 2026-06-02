from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from decimal import Decimal, InvalidOperation
from functools import wraps
import json
import hashlib
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib.auth import authenticate, get_user_model
Usuario = get_user_model()

from .models import Venta, DetalleVenta, AperturaCaja, CierreCaja, Devolucion, DetalleDevolucion
from .forms import VentaForm, DetalleVentaForm
from productos.models import Producto, Categoria, PresentacionProducto
from inventario.models import Inventario



# ════════════════════════════════════════
# DECORADORES
# ════════════════════════════════════════

def session_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('usuario_id'):
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper

def caja_desbloqueada(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('usuario_id'):
            return redirect('login')
        if not request.session.get('caja_desbloqueada'):
            return redirect('ventas:desbloquear_caja')
        hoy = timezone.localdate()
        if CierreCaja.objects.filter(fecha=hoy).exists():
            request.session.pop('caja_desbloqueada', None)
            request.session.pop('caja_usuario', None)
            return redirect('ventas:desbloquear_caja')
        return view_func(request, *args, **kwargs)
    return wrapper


# ════════════════════════════════════════
# DESBLOQUEO / BLOQUEO DE CAJA
# ════════════════════════════════════════

@session_required
def desbloquear_caja(request):
    hoy = timezone.localdate()

    if request.session.get('caja_desbloqueada'):
        return redirect('ventas:ventas_lista')

    ultimo_cierre  = CierreCaja.objects.filter(fecha=hoy).first()
    hay_cierre_hoy = ultimo_cierre is not None

    if hay_cierre_hoy:
        return render(request, 'ventas/caja.html', {
            'error':          None,
            'hay_cierre_hoy': True,
            'ultimo_cierre':  ultimo_cierre,
        })

    error = None
    if request.method == 'POST':
        password = request.POST.get('password', '').strip()
        if not password:
            error = 'Ingresa la contraseña.'
        else:
            # Buscar usuario activo cuyo Perfil esté activo
            usuario_id = request.session.get('usuario_id')
            user = None
            if usuario_id:
                try:
                    user = Usuario.objects.get(pk=usuario_id)
                except Usuario.DoesNotExist:
                    pass

            if user and user.check_password(password) and user.activo:
                request.session['caja_desbloqueada'] = True
                request.session['caja_usuario'] = (
                    f'{user.first_name} {user.last_name}'.strip()
                    or user.username
                )
                return redirect('ventas:ventas_lista')
            else:
                error = 'Contraseña incorrecta.'

    return render(request, 'ventas/caja.html', {
        'error':          error,
        'hay_cierre_hoy': False,
        'ultimo_cierre':  ultimo_cierre,
    })

@session_required
def bloquear_caja(request):
    request.session.pop('caja_desbloqueada', None)
    request.session.pop('caja_usuario', None)
    return redirect('ventas:desbloquear_caja')


# ════════════════════════════════════════
# VENTAS
# ════════════════════════════════════════

@caja_desbloqueada
def ventas_lista(request):
    ventas     = Venta.objects.prefetch_related('detalles__producto', 'detalles__presentacion').order_by('-fecha')
    form       = VentaForm()
    categorias = Categoria.objects.prefetch_related('productos__presentaciones').all()
    hoy        = timezone.localdate()

    caja_abierta  = AperturaCaja.objects.filter(fecha=hoy).first()
    ultimo_cierre = CierreCaja.objects.filter(fecha=hoy).first()
    total_dia     = int(sum(v.total_venta for v in Venta.objects.filter(fecha__date=hoy)))

    mostrar_conteo_apertura = (not caja_abierta) and (not ultimo_cierre)

    return render(request, 'ventas/ventas.html', {
        'ventas':                  ventas,
        'form':                    form,
        'categorias':              categorias,
        'caja_abierta':            caja_abierta,
        'ultimo_cierre':           ultimo_cierre,
        'total_dia':               total_dia,
        'hoy':                     hoy,
        'caja_usuario':            request.session.get('caja_usuario', ''),
        'mostrar_conteo_apertura': mostrar_conteo_apertura,
    })


@caja_desbloqueada
def nueva_venta(request):
    if request.method != 'POST':
        return redirect('ventas:ventas_lista')

    form             = VentaForm(request.POST)
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

    if not form.is_valid():
        messages.error(request, "Revisa los campos del formulario.")
        return redirect('ventas:ventas_lista')

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

    venta = form.save(commit=False)
    venta.descuento_porcentaje = descuento_pct
    venta.total_con_descuento  = total_final
    venta.pago_efectivo        = pago_efectivo
    venta.pago_tarjeta         = pago_tarjeta
    venta.pago_transferencia   = pago_transferencia
    venta.pago_nequi           = pago_nequi
    venta.pago_daviplata       = pago_daviplata
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


@caja_desbloqueada
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

@caja_desbloqueada
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

def _nombre_usuario_sesion(request):
    """Devuelve el nombre del usuario activo en sesión."""
    nombre = request.session.get('caja_usuario', '')
    if nombre:
        return nombre
    usuario_id = request.session.get('usuario_id')
    if usuario_id:
        try:
            u = Usuario.objects.get(pk=usuario_id)
            return f'{u.first_name} {u.last_name}'.strip() or u.username
        except Usuario.DoesNotExist:
            pass
    return ''


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

    AperturaCaja.objects.create(
        fecha=hoy,
        monto_base=monto_base,
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

    request.session.pop('caja_desbloqueada', None)
    request.session.pop('caja_usuario', None)

    return JsonResponse({'ok': True})


# ════════════════════════════════════════
# CONTEO DE APERTURA (modal automático)
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

    AperturaCaja.objects.create(
        fecha=hoy,
        monto_base=monto_contado,
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

    ventas = Venta.objects.filter(
        cliente__nombre__icontains=q
    ).order_by('-fecha')[:10]

    if q.isdigit():
        ventas = (Venta.objects.filter(pk=int(q)) | ventas).distinct()

    return JsonResponse({'ventas': [
        {
            'id':      v.pk,
            'cliente': v.cliente.nombre,
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