from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.db.models import Sum
import json
from django.urls import reverse
from inventario.models import Lote, Inventario, MovimientoInventario
from productos.models import Producto, PresentacionProducto
from .forms import LoteForm


@login_required
def lote_list(request):
    productos = Producto.objects.select_related('categoria').prefetch_related('presentaciones').all()

    hoy = timezone.now().date()
    ingresos_hoy = Lote.objects.filter(fecha_registro__date=hoy).aggregate(
        total=Sum('stock_actual')
    )['total'] or 0

    ordenes_mes = Lote.objects.filter(
        fecha_registro__year=hoy.year, fecha_registro__month=hoy.month
    ).count()

    top_productos = (
        Producto.objects
        .annotate(stock_calculado=Sum('presentaciones__lotes__stock_actual'))
        .order_by('-stock_calculado')[:5]
    )
    proveedores_labels = json.dumps([p.nombre for p in top_productos])
    proveedores_data = json.dumps([p.stock_calculado or 0 for p in top_productos])

    context = {
        'productos': productos,
        'ingresos_hoy': ingresos_hoy,
        'ordenes_mes': ordenes_mes,
        'proveedores_labels': proveedores_labels,
        'proveedores_data': proveedores_data,
        'hay_presentaciones': PresentacionProducto.objects.exists(),
        'breadcrumb_items': [
            {'nombre': 'Gestión de Lotes', 'url': None},
        ],
    }
    return render(request, 'lotes/lote_list.html', context)


@login_required
def lote_detail(request, numero_lote):
    lote = get_object_or_404(Lote, numero_lote=numero_lote)
    movimientos = lote.movimientos.all()
    return render(request, 'lotes/lote_detail.html', {'lote': lote, 'movimientos': movimientos})


@login_required
def lote_create(request):
    if request.method == 'POST':
        form = LoteForm(request.POST)
        if form.is_valid():
            lote = form.save(commit=False)
            lote.registrado_por = request.user
            lote.save()
            messages.success(request, f'Lote {lote.numero_lote} registrado correctamente.')
        else:
            messages.error(request, f'No se pudo registrar el lote: {form.errors.as_text()}')
        return redirect('lotes:lote_list')

    return redirect('lotes:lote_list')


@login_required
def lote_update(request, numero_lote):
    lote = get_object_or_404(Lote, numero_lote=numero_lote)
    if request.method == 'POST':
        form = LoteForm(request.POST, instance=lote)
        if form.is_valid():
            form.save()
            messages.success(request, f'Lote {lote.numero_lote} actualizado.')
            return redirect('lotes:lote_list')
    else:
        form = LoteForm(instance=lote)
    return render(request, 'lotes/lote_form.html', {'form': form, 'lote': lote})


@login_required
@transaction.atomic
def lote_ajustar_stock(request, numero_lote):
    lote = get_object_or_404(Lote, numero_lote=numero_lote)

    if request.method == 'POST':
        nuevo_stock_raw = request.POST.get('nuevo_stock')
        costo_unitario = request.POST.get('costo_unitario')
        motivo = request.POST.get('motivo', '').strip()

        try:
            nuevo_stock = int(nuevo_stock_raw)
        except (TypeError, ValueError):
            messages.error(request, 'El stock ingresado no es válido.')
            return redirect('inventario:gestion_stock')

        if nuevo_stock < 0:
            messages.error(request, 'El stock no puede ser negativo.')
            return redirect('inventario:gestion_stock')

        diferencia = nuevo_stock - lote.stock_actual
        lote.stock_actual = nuevo_stock
        if costo_unitario:
            lote.costo_unitario = costo_unitario
        lote.save()

        inventario, _creado = Inventario.objects.get_or_create(
            presentacion=lote.presentacion,
            defaults={
                'producto': lote.presentacion.producto,
                'stock_actual': lote.stock_actual,
            }
        )
        MovimientoInventario.objects.create(
            inventario=inventario,
            lote=lote,
            registrado_por=request.user,
            tipo='ajuste',
            cantidad=diferencia,
            motivo=motivo or f'Ajuste manual de stock del lote {lote.numero_lote}',
            stock_resultante=nuevo_stock,
        )

        messages.success(request, f'Stock del lote {lote.numero_lote} actualizado a {nuevo_stock} unidades.')

    return redirect('inventario:gestion_stock')