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
        'compras_count': compras.count(),
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
