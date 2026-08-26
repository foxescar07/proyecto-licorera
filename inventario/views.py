from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
import json

from productos.models import Producto, PresentacionProducto
from .forms import LoteForm, MovimientoInventarioForm
from .models import Inventario, Lote, MovimientoInventario

@login_required
def inventario_home(request):
    lotes_por_vencer = [l for l in Lote.objects.all() if l.proximo_a_vencer]
    lotes_vencidos    = [l for l in Lote.objects.all() if l.esta_vencido]
    bajo_stock        = Inventario.objects.filter(stock_actual__lte=F('stock_min'))
    
    movimientos = MovimientoInventario.objects.values_list('fecha', flat=True).distinct().order_by('-fecha')
    dias_con_movimientos = [m.date() for m in movimientos]
    hoy = timezone.now().date()

    context = {
        'lotes_por_vencer': lotes_por_vencer,
        'lotes_vencidos': lotes_vencidos,
        'bajo_stock': bajo_stock,
        'dias_con_movimientos': dias_con_movimientos,
        'hoy': hoy,
        'fecha_filtro': hoy,
        'lotes': Lote.objects.select_related('presentacion__producto').all(),
        'movimientos': MovimientoInventario.objects.all(),
        'productos': Producto.objects.select_related('categoria').prefetch_related('presentaciones__lotes').all(),
        'sin_codigo': Producto.objects.filter(codigo__isnull=True).count(),
        'con_codigo': Producto.objects.filter(codigo__isnull=False).count(),
    }
    return render(request, 'inventario/inventario_home.html', context)

@login_required
def gestion_stock(request):
    productos = Producto.objects.select_related('categoria').prefetch_related('presentaciones__lotes').all()
    lotes = Lote.objects.select_related('presentacion__producto', 'registrado_por').all()
    lotes_activos = list(lotes)
    lotes_por_vencer = [l for l in lotes_activos if getattr(l, 'proximo_a_vencer', False)]
    lotes_vencidos = [l for l in lotes_activos if getattr(l, 'esta_vencido', False)]

    context = {
        'productos': productos,
        'lotes_activos': lotes_activos,
        'lotes_por_vencer': lotes_por_vencer,
        'lotes_vencidos': lotes_vencidos,
    }
    return render(request, 'inventario/gestion_stock.html', context)

@login_required
def lote_list(request):
    productos = Producto.objects.select_related('categoria').prefetch_related('presentaciones').all()
    hoy = timezone.now().date()
    ingresos_hoy = Lote.objects.filter(fecha_registro__date=hoy).aggregate(total=Sum('stock_actual'))['total'] or 0
    ordenes_mes = Lote.objects.filter(fecha_registro__year=hoy.year, fecha_registro__month=hoy.month).count()
    
    top_productos = Producto.objects.annotate(stock_calculado=Sum('presentaciones__lotes__stock_actual')).order_by('-stock_calculado')[:5]
    proveedores_labels = json.dumps([p.nombre for p in top_productos])
    proveedores_data = json.dumps([p.stock_calculado or 0 for p in top_productos])

    context = {
        'productos': productos,
        'ingresos_hoy': ingresos_hoy,
        'ordenes_mes': ordenes_mes,
        'proveedores_labels': proveedores_labels,
        'proveedores_data': proveedores_data,
        'hay_presentaciones': PresentacionProducto.objects.exists(),
    }
    return render(request, 'inventario/lote_list.html', context)

@login_required
def lote_detail(request, numero_lote):
    lote = get_object_or_404(Lote, numero_lote=numero_lote)
    return render(request, 'inventario/lote_detail.html', {'lote': lote, 'movimientos': lote.movimientos.all()})

@login_required
def lote_create(request):
    if request.method == 'POST':
        form = LoteForm(request.POST)
        if form.is_valid():
            lote = form.save(commit=False)
            lote.registrado_por = request.user
            lote.save()
            messages.success(request, f'Lote {lote.numero_lote} registrado.')
        else:
            messages.error(request, 'Error al registrar lote.')
    return redirect('inventario:lote_list')

@login_required
def lote_update(request, numero_lote):
    lote = get_object_or_404(Lote, numero_lote=numero_lote)
    if request.method == 'POST':
        form = LoteForm(request.POST, instance=lote)
        if form.is_valid():
            form.save()
            messages.success(request, f'Lote {lote.numero_lote} actualizado.')
            return redirect('inventario:lote_list')
    else:
        form = LoteForm(instance=lote)
    return render(request, 'inventario/lote_form.html', {'form': form, 'lote': lote})

@login_required
def inventario_list(request):
    query = request.GET.get('q', '')
    items = Inventario.objects.select_related('producto', 'presentacion')
    if query:
        items = items.filter(producto__nombre__icontains=query)
    return render(request, 'inventario/inventario_list.html', {'items': items, 'query': query})

@login_required
def inventario_detail(request, codigo_inventario):
    item = get_object_or_404(Inventario, codigo_inventario=codigo_inventario)
    # Lógica para guardar código de barras si viene por POST (desde el modal)
    if request.method == 'POST':
        codigo = request.POST.get('codigo')
        if codigo:
            item.producto.codigo = codigo
            item.producto.save()
            return redirect('inventario:inventario_home')
    return render(request, 'inventario/inventario_detail.html', {'item': item, 'movimientos': item.movimientos.all()})

@login_required
def movimiento_list(request):
    movimientos = MovimientoInventario.objects.select_related('inventario', 'lote', 'registrado_por')
    tipo = request.GET.get('tipo')
    if tipo:
        movimientos = movimientos.filter(tipo=tipo)
    return render(request, 'inventario/movimiento_list.html', {'movimientos': movimientos, 'tipo': tipo})

@login_required
@transaction.atomic
def movimiento_create(request):
    if request.method == 'POST':
        lote_id = request.POST.get('lote_id')
        tipo = request.POST.get('tipo')
        cantidad = int(request.POST.get('cantidad', 0))
        motivo = request.POST.get('motivo', '').strip()
        lote = get_object_or_404(Lote, pk=lote_id)

        if tipo == 'entrada':
            lote.stock_actual += cantidad
        elif tipo == 'salida':
            lote.stock_actual -= cantidad
        lote.save()

        inventario, _ = Inventario.objects.get_or_create(
            presentacion=lote.presentacion,
            defaults={'producto': lote.presentacion.producto, 'stock_actual': lote.stock_actual}
        )

        MovimientoInventario.objects.create(
            inventario=inventario, lote=lote, registrado_por=request.user,
            tipo=tipo, cantidad=cantidad, motivo=motivo, stock_resultante=lote.stock_actual
        )
        messages.success(request, 'Movimiento registrado.')
    return redirect('inventario:inventario_home')

@login_required
@transaction.atomic
def lote_ajustar_stock(request, numero_lote):
    lote = get_object_or_404(Lote, numero_lote=numero_lote)
    if request.method == 'POST':
        nuevo_stock = int(request.POST.get('nuevo_stock', 0))
        diferencia = nuevo_stock - lote.stock_actual
        lote.stock_actual = nuevo_stock
        lote.save()

        inventario = Inventario.objects.filter(presentacion=lote.presentacion).first()
        if inventario:
            MovimientoInventario.objects.create(
                inventario=inventario, lote=lote, registrado_por=request.user,
                tipo='ajuste', cantidad=diferencia, motivo='Ajuste manual', stock_resultante=nuevo_stock
            )
        messages.success(request, 'Stock ajustado.')
    return redirect('inventario:gestion_stock')