from django.shortcuts import render, redirect, get_object_or_404 # type: ignore
from django.contrib import messages # type: ignore
from django.http import JsonResponse # type: ignore
from django.db import transaction # type: ignore
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


def _restaurar_stock_fefo(presentacion, lotes_info, vendedor):
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

    usuario_id    = request.session.get('usuario_id')
    caja_abierta  = AperturaCaja.objects.filter(fecha=hoy, usuario_id=usuario_id).first()
    ultimo_cierre = CierreCaja.objects.filter(fecha=hoy, usuario_id=usuario_id).first()

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
                'id':         p.id,
                'nombre':     p.nombre,
                'unidades':   p.unidades,
                'cantidad':   p.stock_real,
                'precio':     float(p.precio),
            }
            for p in producto.presentaciones.all()
        ],
    })


@session_required
def ventas_del_dia(request):
    hoy       = timezone.localdate()
    ventas    = Venta.objects.filter(fecha__date=hoy).prefetch_related('detalles__producto', 'detalles__presentacion').order_by('-fecha')
    total_dia = int(sum(v.total_con_descuento for v in ventas))

    return render(request, 'ventas/ventas_del_dia.html', {
        'ventas':    ventas,
        'hoy':       hoy,
        'total_dia': total_dia,
    })


# Control de caja y devoluciones (Pendientes de implementar lógicas personalizadas de plantillas)
@session_required
def registrar_conteo(request): return render(request, 'ventas/registrar_conteo.html')
@session_required
def cierre_caja(request): return render(request, 'ventas/cierre_caja.html')
@session_required
def lista_devoluciones(request):
    devoluciones = Devolucion.objects.prefetch_related('detalles__producto').order_by('-fecha')
    return render(request, 'ventas/lista_devoluciones.html', {'devoluciones': devoluciones})
@session_required
@transaction.atomic
def registrar_devolucion(request):
    if request.method == 'POST': pass
    return redirect('ventas:lista_devoluciones')
@session_required
def seleccionar_venta_devolucion(request, venta_id):
    venta = get_object_or_404(Venta.objects.prefetch_related('detalles__producto'), pk=venta_id)
    return render(request, 'ventas/seleccionar_venta_devolucion.html', {'venta': venta})
@session_required
def detalle_devolucion(request, pk):
    devolucion = get_object_or_404(Devolucion, pk=pk)
    return render(request, 'ventas/detalle_devolucion.html', {'devolucion': devolucion})
@session_required
def buscar_venta_devolucion(request):
    query = request.GET.get('q', '')
    ventas = Venta.objects.filter(id__icontains=query).order_by('-fecha')[:10] if query else Venta.objects.none()
    return render(request, 'ventas/buscar_venta_devolucion.html', {'ventas': ventas, 'query': query})
@session_required
def detalle_venta_devolucion(request, venta_id):
    venta = get_object_or_404(Venta.objects.prefetch_related('detalles__producto'), pk=venta_id)
    return render(request, 'ventas/detalle_venta_devolucion.html', {'venta': venta})
@session_required
def comprobante_devolucion(request, pk):
    devolucion = get_object_or_404(Devolucion, pk=pk)
    return render(request, 'ventas/comprobante_devolucion.html', {'devolucion': devolucion})