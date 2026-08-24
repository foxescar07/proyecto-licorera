# proveedores/views.py
"""
Vistas del módulo de Proveedores y Compras.
"""

import logging
import json
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db import transaction

from .models import Proveedor, Compra, HistorialCompra
from .forms import ProveedorForm, NuevaCompraForm
from .helpers import (
    obtener_compras_proveedor,
    calcular_totales_compra,
    obtener_datos_graficos,
    crear_compra_con_detalles,
    calcular_estadisticas_proveedor,
)
from productos.models import Producto

logger = logging.getLogger(__name__)

@login_required
def lista_proveedores(request):
    from django.db.models import Sum, F, DecimalField, Case, When, Value

    proveedores = Proveedor.objects.all()

    # Calcular total de compras manualmente para cada proveedor
    for proveedor in proveedores:
        try:
            compras = Compra.objects.filter(proveedor=proveedor)
            total = sum(
                (c.cantidad * c.precio_unitario if c.precio_unitario else 0)
                for c in compras
            ) or 0
            proveedor.total_compras = total
            proveedor.total_ordenes = compras.count()
        except Exception:
            proveedor.total_compras = 0
            proveedor.total_ordenes = 0

    # Filtros
    q = request.GET.get('q', '')
    estado = request.GET.get('estado', '')
    tipo = request.GET.get('tipo', '')

    if q:
        proveedores = proveedores.filter(nombre_empresa__icontains=q) | proveedores.filter(email__icontains=q)

    if estado:
        proveedores = proveedores.filter(estado=estado)

    if tipo:
        proveedores = proveedores.filter(tipo_proveedor=tipo)

    # Estadísticas
    total_proveedores = Proveedor.objects.count()
    proveedores_activos = Proveedor.objects.filter(estado='activo').count()
    proveedores_inactivos = Proveedor.objects.filter(estado='inactivo').count()
    proveedores_sancionados = Proveedor.objects.filter(estado='sancionado').count()

    porcentaje_activos = (
        int((proveedores_activos / total_proveedores) * 100)
        if total_proveedores > 0 else 0
    )

    # Obtener máximo de compras para normalizar barras
    max_compras = max([p.total_compras for p in proveedores], default=1)
    if max_compras == 0:
        max_compras = 1

    # Calcular porcentaje de ancho para cada proveedor
    for proveedor in proveedores:
        if proveedor.total_compras > 0:
            proveedor.bar_width = int((proveedor.total_compras / max_compras) * 100)
        else:
            proveedor.bar_width = 1

    # Paginación
    paginator = Paginator(proveedores, 10)  # 10 proveedores por página
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Calcular gastos por proveedor para la gráfica - usar raw SQL para evitar Decimal
    gastos_proveedor_dict = {}
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT p.nombre_empresa, SUM(c.cantidad) as total
                FROM proveedores_compra c
                JOIN proveedores_proveedor p ON c.proveedor_id = p.id
                GROUP BY p.id, p.nombre_empresa
                ORDER BY total DESC
            """)
            for nombre, total in cursor.fetchall():
                gastos_proveedor_dict[nombre] = total or 0
    except Exception:
        gastos_proveedor_dict = {}

    # Ordenar y tomar top 5
    gastos_ordenados = sorted(gastos_proveedor_dict.items(), key=lambda x: x[1], reverse=True)[:5]
    gastos_labels = [item[0] for item in gastos_ordenados]
    gastos_data = [int(item[1]) for item in gastos_ordenados]

    # Calcular porcentajes para el gráfico de pastel
    gastos_total = sum(gastos_data) if gastos_data else 0
    if gastos_total == 0:
        gastos_total = 1
    gastos_porcentajes = [int((gasto / gastos_total * 100)) for gasto in gastos_data] if gastos_data else []

    context = {
        'proveedores': proveedores,
        'page_obj': page_obj,
        'paginator': paginator,
        'total_proveedores': total_proveedores,
        'proveedores_activos': proveedores_activos,
        'proveedores_inactivos': proveedores_inactivos,
        'proveedores_sancionados': proveedores_sancionados,
        'porcentaje_activos': porcentaje_activos,
        'max_compras': max_compras,
        'gastos_labels_json': json.dumps(gastos_labels),
        'gastos_data_json': json.dumps(gastos_data),
        'gastos_porcentajes_json': json.dumps(gastos_porcentajes),
        'breadcrumb_items': [
            {'nombre': 'Proveedores', 'url': None},
        ],
    }

    return render(request, 'proveedores/proveedores.html', context)

@login_required
def crear_proveedor(request):
    if request.method == 'POST':
        form = ProveedorForm(request.POST)

        # Verificar si es AJAX
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if form.is_valid():
            proveedor = form.save(commit=False)
            proveedor.registrado_por = request.user
            proveedor.save()

            if is_ajax:
                # Retornar JSON para AJAX
                return JsonResponse({'success': True, 'message': f'Proveedor {proveedor.nombre_empresa} creado exitosamente.'})
            else:
                # Retornar redirección para formulario tradicional
                messages.success(request, f'Proveedor {proveedor.nombre_empresa} creado exitosamente.')
                return redirect('lista_proveedores')
        else:
            if is_ajax:
                # Retornar errores en JSON para AJAX
                errors = {}
                for field, field_errors in form.errors.items():
                    errors[field] = field_errors[0] if field_errors else 'Error desconocido'
                return JsonResponse({'success': False, 'errors': errors}, status=400)
            else:
                # Mostrar errores para formulario tradicional
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field}: {error}')
                return redirect('lista_proveedores')

    return redirect('lista_proveedores')

@login_required
def editar_proveedor(request, id):
    proveedor = get_object_or_404(Proveedor, id=id)

    if request.method == 'POST':
        form = ProveedorForm(request.POST, instance=proveedor)
        if form.is_valid():
            proveedor_guardado = form.save(commit=False)
            proveedor_guardado.save()
            messages.success(request, f'Proveedor {proveedor_guardado.nombre_empresa} actualizado exitosamente.')
            return redirect('lista_proveedores')
    else:
        form = ProveedorForm(instance=proveedor)

    context = {
        'form': form,
        'proveedor': proveedor,
        'breadcrumb_items': [
            {'nombre': 'Proveedores', 'url': reverse('lista_proveedores')},
            {'nombre': f'Editar: {proveedor.nombre_empresa}', 'url': None},
        ],
    }

    return render(request, 'proveedores/editar_proveedor.html', context)

@login_required
def eliminar_proveedor(request, id):
    proveedor = get_object_or_404(Proveedor, id=id)

    if request.method == 'POST':
        nombre = proveedor.nombre_empresa
        proveedor.delete()
        messages.success(request, f'Proveedor {nombre} eliminado exitosamente.')
    return redirect('lista_proveedores')

@login_required
def detalle_proveedor(request, id):
    proveedor = get_object_or_404(Proveedor, id=id)
    context = {
        'proveedor': proveedor,
        'breadcrumb_items': [
            {'nombre': 'Proveedores', 'url': reverse('lista_proveedores')},
            {'nombre': proveedor.nombre_empresa, 'url': None},
        ],
        
    }
    return render(request, 'proveedores/detalle_proveedor.html', context)

@login_required
def activar_proveedor(request, id):
    proveedor = get_object_or_404(Proveedor, id=id)

    if request.method == 'POST':
        proveedor.estado = 'activo'
        proveedor.modificado_por = request.user
        proveedor.save()
        messages.success(request, f'Proveedor {proveedor.nombre_empresa} activado exitosamente.')

    return redirect('lista_proveedores')

@login_required
def desactivar_proveedor(request, id):
    proveedor = get_object_or_404(Proveedor, id=id)

    if request.method == 'POST':
        proveedor.estado = 'inactivo'
        proveedor.modificado_por = request.user
        proveedor.save()
        messages.success(request, f'Proveedor {proveedor.nombre_empresa} desactivado exitosamente.')

    return redirect('lista_proveedores')

@login_required
def sancionar_proveedor(request, id):
    proveedor = get_object_or_404(Proveedor, id=id)

    if request.method == 'POST':
        motivo = request.POST.get('motivo_sancion', '')
        if motivo:
            proveedor.estado = 'sancionado'
            proveedor.motivo_sancion = motivo
            proveedor.modificado_por = request.user
            proveedor.save()
            messages.success(request, f'Proveedor {proveedor.nombre_empresa} sancionado exitosamente.')
        else:
            messages.error(request, 'Debe indicar el motivo de la sanción.')

    return redirect('lista_proveedores')

@login_required
def lista_compras(request):
    """Lista y registra compras de proveedores."""
    todos_proveedores = Proveedor.objects.all().order_by('nombre_empresa')
    proveedor = None
    compras = []

    # Obtener o establecer proveedor en sesión
    proveedor_id = request.POST.get('proveedor_id') or request.GET.get('proveedor') or request.session.get('proveedor_id')

    if proveedor_id:
        try:
            request.session['proveedor_id'] = int(proveedor_id)
            proveedor = get_object_or_404(Proveedor, id=request.session['proveedor_id'])
        except (ValueError, Proveedor.DoesNotExist):
            pass

    if not proveedor:
        primer_proveedor = todos_proveedores.first()
        if primer_proveedor:
            request.session['proveedor_id'] = primer_proveedor.id
            proveedor = primer_proveedor

    # Obtener compras si hay proveedor
    if proveedor:
        compras = obtener_compras_proveedor(proveedor.id)

    # Procesar registro de nueva compra
    form = NuevaCompraForm()
    if request.method == 'POST' and 'cantidad' in request.POST:
        if not proveedor:
            messages.error(request, 'Por favor selecciona un proveedor.')
            return redirect('lista_compras')

        form = NuevaCompraForm(request.POST)
        if form.is_valid():
            producto = form.cleaned_data['producto']
            cantidad = form.cleaned_data['cantidad']
            precio_unitario = form.cleaned_data['precio_unitario']

            compra, error = crear_compra_con_detalles(
                proveedor, producto, cantidad, precio_unitario, request.user
            )

            if compra:
                messages.success(
                    request,
                    f'✅ {cantidad} unidades de "{producto.nombre}" ingresadas a inventario correctamente.'
                )
                return redirect('lista_compras')
            else:
                messages.error(request, error)
        else:
            for field, errors in form.errors.items():
                messages.error(request, f'{field}: {", ".join(errors)}')

    # Obtener estadísticas
    totales = calcular_totales_compra(proveedor)
    graficos = obtener_datos_graficos(proveedor)

    context = {
        'compras': compras,
        'compras_count': len(compras) if compras else 0,
        'proveedor': proveedor,
        'todos_proveedores': todos_proveedores,
        'form': form,
        'subtotal_compras': totales['total_gastado'],
        'total_gastado': totales['total_gastado'],
        'count_mes': totales['count_mes'],
        'total_mes': totales['total_mes'],
        'producto_top': totales['producto_top'],
        'meses_labels_json': json.dumps(graficos['meses_labels']),
        'meses_data_json': json.dumps(graficos['meses_data']),
        'productos_labels_json': json.dumps(['N/A']),
        'productos_data_json': json.dumps([0]),
        'gastos_labels_json': json.dumps(graficos['gastos_labels']),
        'gastos_data_json': json.dumps(graficos['gastos_data']),
        'gastos_porcentajes_json': json.dumps(graficos['gastos_porcentajes']),
        'breadcrumb_items': [
            {'nombre': 'Proveedores', 'url': reverse('lista_proveedores')},
            {'nombre': 'Compras', 'url': None},
        ],
    }
    return render(request, 'proveedores/compras.html', context)

@login_required
def registrar_compra(request):
    """Alias para lista_compras (mantener compatibilidad URL)."""
    return lista_compras(request)


@login_required
@require_POST
def cambiar_estado_compra(request, id):
    """Cambia el estado respetando el flujo definido para una compra."""
    compra = get_object_or_404(Compra, id=id)
    nuevo_estado = request.POST.get('estado')
    transiciones = {
        'pendiente': {'confirmada', 'cancelada'},
        'confirmada': {'recibida', 'cancelada'},
    }

    if nuevo_estado not in transiciones.get(compra.estado, set()):
        messages.error(request, 'El cambio de estado solicitado no es válido.')
        return redirect('lista_compras')

    with transaction.atomic():
        anterior = compra.estado
        compra.estado = nuevo_estado
        compra.save(update_fields=['estado'])
        HistorialCompra.objects.create(
            compra=compra,
            evento='cancelada' if nuevo_estado == 'cancelada' else 'editada',
            usuario=request.user,
            descripcion=f'Estado cambiado de {anterior} a {nuevo_estado}.',
        )
    messages.success(request, 'Estado de la compra actualizado.')
    return redirect('lista_compras')


@login_required
@require_POST
def registrar_pago_compra(request, id):
    """Registra un abono sin permitir exceder el saldo de la compra."""
    compra = get_object_or_404(Compra, id=id)
    if compra.estado == 'cancelada':
        messages.error(request, 'No se pueden registrar pagos en una compra cancelada.')
        return redirect('lista_compras')

    try:
        monto = Decimal(request.POST.get('monto_pagado', ''))
    except Exception:
        monto = Decimal('0')

    if monto <= 0 or monto > compra.saldo:
        messages.error(request, 'El abono debe ser mayor a cero y no puede superar el saldo pendiente.')
        return redirect('lista_compras')

    with transaction.atomic():
        compra.saldo -= monto
        compra.save(update_fields=['saldo'])
        HistorialCompra.objects.create(
            compra=compra,
            evento='pagada' if compra.saldo == 0 else 'editada',
            usuario=request.user,
            descripcion=f'Abono registrado por ${monto:.2f}. Saldo pendiente: ${compra.saldo:.2f}.',
        )
    messages.success(request, 'Pago registrado correctamente.')
    return redirect('lista_compras')


# ============================================
# VISTAS PARA MANEJO DE MODALES (AJAX)
# ============================================

@login_required
def detalle_proveedor_modal(request, id):
    """Obtener detalles del proveedor para mostrar en modal."""
    try:
        proveedor = get_object_or_404(Proveedor, id=id)
        stats = calcular_estadisticas_proveedor(proveedor)

        data = {
            'success': True,
            'proveedor': {
                'id': proveedor.id,
                'nombre_empresa': proveedor.nombre_empresa,
                'nit': proveedor.nit or '—',
                'email': proveedor.email,
                'telefono': proveedor.telefono or '—',
                'tipo_proveedor': proveedor.get_tipo_proveedor_display(),
                'estado': proveedor.get_estado_display(),
                'estado_value': proveedor.estado,
                'observacion': proveedor.observacion or 'Sin observaciones',
                'fecha_registro': proveedor.fecha_registro.strftime('%d/%m/%Y'),
                'total_compras': stats['total_compras'],
                'total_gastado': f'${stats["total_gastado"]:,.2f}',
            }
        }
        return JsonResponse(data)
    except Exception as e:
        logger.error(f"Error en detalle_proveedor_modal: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@csrf_exempt
def desactivar_proveedor(request, id):
    """Desactivar un proveedor"""
    if request.method == 'POST':
        try:
            proveedor = get_object_or_404(Proveedor, id=id)

            if proveedor.estado == 'activo':
                proveedor.estado = 'inactivo'
                proveedor.save()

                return JsonResponse({
                    'success': True,
                    'message': f'Proveedor {proveedor.nombre_empresa} desactivado exitosamente',
                    'nuevo_estado': 'inactivo'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'El proveedor no está activo'
                }, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)


@login_required
@csrf_exempt
def reactivar_proveedor(request, id):
    """Reactivar un proveedor"""
    if request.method == 'POST':
        try:
            proveedor = get_object_or_404(Proveedor, id=id)

            if proveedor.estado in ['inactivo', 'sancionado']:
                proveedor.estado = 'activo'
                proveedor.save()

                return JsonResponse({
                    'success': True,
                    'message': f'Proveedor {proveedor.nombre_empresa} reactivado exitosamente',
                    'nuevo_estado': 'activo'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'El proveedor ya está activo'
                }, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)


@login_required
@csrf_exempt
def sancionar_proveedor(request, id):
    """Sancionar un proveedor"""
    if request.method == 'POST':
        try:
            proveedor = get_object_or_404(Proveedor, id=id)
            observacion = request.POST.get('observacion', '')

            if not observacion or len(observacion.strip()) == 0:
                return JsonResponse({
                    'success': False,
                    'error': 'Debe indicar el motivo de la sanción'
                }, status=400)

            proveedor.estado = 'sancionado'
            proveedor.observacion = observacion
            proveedor.save()

            return JsonResponse({
                'success': True,
                'message': f'Proveedor {proveedor.nombre_empresa} sancionado exitosamente',
                'nuevo_estado': 'sancionado'
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)


@login_required
@csrf_exempt
def levantar_sancion_proveedor(request, id):
    """Levantar sanción de un proveedor"""
    if request.method == 'POST':
        try:
            proveedor = get_object_or_404(Proveedor, id=id)

            if proveedor.estado == 'sancionado':
                proveedor.estado = 'activo'
                proveedor.observacion = ''
                proveedor.save()

                return JsonResponse({
                    'success': True,
                    'message': f'Sanción levantada para {proveedor.nombre_empresa}',
                    'nuevo_estado': 'activo'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'El proveedor no está sancionado'
                }, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)


# ============================================
# DEVOLUCIONES A PROVEEDORES
# ============================================

@login_required
def lista_devoluciones_proveedor(request):
    """Lista devoluciones a proveedores con filtros y KPIs."""
    from django.db.models import Sum, Count, Q
    from django.utils import timezone
    from .models import DevolucionProveedor

    devoluciones = DevolucionProveedor.objects.select_related(
        'proveedor', 'compra', 'documento_usuario'
    ).prefetch_related('detalles')

    # Filtros
    proveedor_id = request.GET.get('proveedor', '')
    estado       = request.GET.get('estado', '')
    motivo       = request.GET.get('motivo', '')
    q            = request.GET.get('q', '')

    if proveedor_id:
        devoluciones = devoluciones.filter(proveedor_id=proveedor_id)
    if estado:
        devoluciones = devoluciones.filter(estado=estado)
    if motivo:
        devoluciones = devoluciones.filter(motivo=motivo)
    if q:
        devoluciones = devoluciones.filter(
            Q(proveedor__nombre_empresa__icontains=q) |
            Q(observaciones__icontains=q)
        )

    # KPIs
    hoy = timezone.now()
    total_devoluciones = DevolucionProveedor.objects.count()
    monto_total        = DevolucionProveedor.objects.aggregate(
        s=Sum('total_devuelto')
    )['s'] or 0
    pendientes         = DevolucionProveedor.objects.filter(estado='pendiente').count()
    del_mes            = DevolucionProveedor.objects.filter(
        fecha__year=hoy.year, fecha__month=hoy.month
    ).count()
    monto_mes          = DevolucionProveedor.objects.filter(
        fecha__year=hoy.year, fecha__month=hoy.month
    ).aggregate(s=Sum('total_devuelto'))['s'] or 0

    # Paginación
    paginator   = Paginator(devoluciones, 12)
    page_number = request.GET.get('page', 1)
    page_obj    = paginator.get_page(page_number)

    todos_proveedores = Proveedor.objects.filter(estado='activo').order_by('nombre_empresa')
    form = __import__('proveedores.forms', fromlist=['DevolucionProveedorForm']).DevolucionProveedorForm()

    context = {
        'devoluciones'      : page_obj,
        'page_obj'          : page_obj,
        'todos_proveedores' : todos_proveedores,
        'form'              : form,
        'total_devoluciones': total_devoluciones,
        'monto_total'       : monto_total,
        'pendientes'        : pendientes,
        'del_mes'           : del_mes,
        'monto_mes'         : monto_mes,
        'filtro_proveedor'  : proveedor_id,
        'filtro_estado'     : estado,
        'filtro_motivo'     : motivo,
        'filtro_q'          : q,
        'breadcrumb_items'  : [
            {'nombre': 'Proveedores', 'url': reverse('lista_proveedores')},
            {'nombre': 'Devoluciones', 'url': None},
        ],
    }
    return render(request, 'proveedores/devoluciones_proveedor.html', context)


@login_required
@require_POST
def crear_devolucion_proveedor(request):
    """Registra una nueva devolución a proveedor."""
    from .models import DevolucionProveedor, DetalleDevolucionProveedor
    from .forms import DevolucionProveedorForm
    from productos.models import PresentacionProducto

    form = DevolucionProveedorForm(request.POST)
    if not form.is_valid():
        for field, errs in form.errors.items():
            for e in errs:
                messages.error(request, f'{field}: {e}')
        return redirect(reverse('ventas:lista_devoluciones') + '?tab=proveedor')

    cd = form.cleaned_data

    with transaction.atomic():
        devolucion = DevolucionProveedor.objects.create(
            proveedor        = cd['proveedor'],
            compra           = cd.get('compra'),
            motivo           = cd['motivo'],
            tipo_resolucion  = cd['tipo_resolucion'],
            observaciones    = cd.get('observaciones', ''),
            documento_usuario= request.user if request.user.is_authenticated else None,
            estado           = 'pendiente',
        )

        detalle = DetalleDevolucionProveedor.objects.create(
            devolucion      = devolucion,
            presentacion    = cd['presentacion'],
            cantidad        = cd['cantidad'],
            precio_unitario = cd['precio_unitario'],
        )

        devolucion.calcular_total()

    messages.success(
        request,
        f'✅ Devolución {devolucion.numero} registrada. '
        f'Total: ${devolucion.total_devuelto:,.0f}'
    )
    return redirect(reverse('ventas:lista_devoluciones') + '?tab=proveedor')



@login_required
def detalle_devolucion_proveedor(request, id):
    """Muestra el detalle completo de una devolución a proveedor."""
    from .models import DevolucionProveedor

    devolucion = get_object_or_404(
        DevolucionProveedor.objects.select_related(
            'proveedor', 'compra', 'documento_usuario'
        ).prefetch_related('detalles__presentacion__producto', 'detalles__lote'),
        id=id
    )

    context = {
        'devolucion': devolucion,
        'breadcrumb_items': [
            {'nombre': 'Proveedores',   'url': reverse('lista_proveedores')},
            {'nombre': 'Devoluciones',  'url': reverse('lista_devoluciones_proveedor')},
            {'nombre': devolucion.numero, 'url': None},
        ],
    }
    return render(request, 'proveedores/detalle_devolucion_proveedor.html', context)


@login_required
@require_POST
def aprobar_devolucion_proveedor(request, id):
    """Cambia el estado de una devolución a 'aprobada'."""
    from .models import DevolucionProveedor

    devolucion = get_object_or_404(DevolucionProveedor, id=id)

    if devolucion.estado != 'pendiente':
        messages.error(request, 'Solo se pueden aprobar devoluciones en estado Pendiente.')
        return redirect('detalle_devolucion_proveedor', id=id)

    devolucion.estado = 'aprobada'
    devolucion.save(update_fields=['estado'])
    messages.success(request, f'✅ Devolución {devolucion.numero} aprobada.')
    return redirect('detalle_devolucion_proveedor', id=id)


@login_required
@require_POST
def rechazar_devolucion_proveedor(request, id):
    """Cambia el estado de una devolución a 'rechazada'."""
    from .models import DevolucionProveedor

    devolucion = get_object_or_404(DevolucionProveedor, id=id)

    if devolucion.estado not in ('pendiente', 'aprobada'):
        messages.error(request, 'No se puede rechazar esta devolución en su estado actual.')
        return redirect('detalle_devolucion_proveedor', id=id)

    devolucion.estado = 'rechazada'
    devolucion.save(update_fields=['estado'])
    messages.success(request, f'Devolución {devolucion.numero} rechazada.')
    return redirect('detalle_devolucion_proveedor', id=id)


@login_required
@require_POST
def aplicar_devolucion_proveedor(request, id):
    """
    Aplica la devolución: descuenta stock del inventario y lote
    y registra el movimiento correspondiente.
    """
    from .models import DevolucionProveedor
    from inventario.models import Lote, Inventario, MovimientoInventario

    devolucion = get_object_or_404(
        DevolucionProveedor.objects.prefetch_related(
            'detalles__presentacion__producto',
            'detalles__lote',
        ),
        id=id
    )

    if devolucion.estado != 'aprobada':
        messages.error(request, 'Solo se pueden aplicar devoluciones en estado Aprobada.')
        return redirect('detalle_devolucion_proveedor', id=id)

    errores = []

    with transaction.atomic():
        for detalle in devolucion.detalles.all():
            presentacion = detalle.presentacion
            cantidad     = detalle.cantidad

            # 1. Descontar del lote (si está vinculado)
            if detalle.lote:
                lote = detalle.lote
                if lote.stock_actual < cantidad:
                    errores.append(
                        f'Stock insuficiente en lote {lote.numero_lote} '
                        f'({lote.stock_actual} disponibles, se necesitan {cantidad})'
                    )
                    continue
                lote.stock_actual -= cantidad
                lote.save(update_fields=['stock_actual'])
            else:
                # Buscar lote con mayor stock para esa presentación (FIFO simple)
                lote = Lote.objects.filter(
                    presentacion=presentacion, stock_actual__gte=cantidad
                ).order_by('fecha_registro').first()
                if not lote:
                    errores.append(
                        f'No hay lote disponible con suficiente stock para '
                        f'"{presentacion}" (necesario: {cantidad})'
                    )
                    continue
                lote.stock_actual -= cantidad
                lote.save(update_fields=['stock_actual'])

            # 2. Descontar del inventario general
            try:
                inv = Inventario.objects.get(
                    producto=presentacion.producto,
                    presentacion=presentacion,
                )
                stock_ant = inv.stock_actual
                inv.stock_actual = max(0, inv.stock_actual - cantidad)
                inv.save(update_fields=['stock_actual'])

                # 3. Registrar movimiento de inventario
                MovimientoInventario.objects.create(
                    inventario      = inv,
                    lote            = lote,
                    registrado_por  = request.user,
                    tipo            = 'salida',
                    cantidad        = -cantidad,
                    motivo          = (
                        f'Devolución a proveedor {devolucion.numero} — '
                        f'{devolucion.get_motivo_display()}'
                    ),
                    stock_resultante= inv.stock_actual,
                )
            except Inventario.DoesNotExist:
                errores.append(
                    f'No se encontró registro de inventario para "{presentacion}"'
                )
                continue

        if errores:
            raise Exception('Errores al aplicar — se revirtió la transacción')

    if errores:
        for e in errores:
            messages.error(request, e)
        return redirect('detalle_devolucion_proveedor', id=id)

    devolucion.estado = 'aplicada'
    devolucion.save(update_fields=['estado'])
    messages.success(
        request,
        f'✅ Devolución {devolucion.numero} aplicada. '
        f'Stock descontado correctamente del inventario.'
    )
    return redirect('detalle_devolucion_proveedor', id=id)

