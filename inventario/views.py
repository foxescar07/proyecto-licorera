from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.db.models import F, Q, Sum
import json
from productos.models import Producto, PresentacionProducto

from .forms import (
    AgendaInventarioForm,
    HallazgoForm,
    LoteForm,
    MovimientoInventarioForm,
)
from .models import (
    AgendaInventario,
    Hallazgo,
    Inventario,
    Lote,
    MovimientoInventario,
)
from productos.models import Producto


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
def inventario_home(request):
    lotes_por_vencer = [l for l in Lote.objects.all() if l.proximo_a_vencer]
    lotes_vencidos    = [l for l in Lote.objects.all() if l.esta_vencido]
    bajo_stock        = Inventario.objects.filter(stock_actual__lte=F('stock_min'))
    agendas_pendientes = AgendaInventario.objects.filter(estado='pendiente')

    movimientos = MovimientoInventario.objects.values_list('fecha', flat=True).distinct().order_by('-fecha')
    dias_con_movimientos = [m.date() for m in movimientos]
    hoy = timezone.now().date()

    context = {
        'lotes_por_vencer': lotes_por_vencer,
        'lotes_vencidos': lotes_vencidos,
        'bajo_stock': bajo_stock,
        'agendas_pendientes': agendas_pendientes,
        'dias_con_movimientos': dias_con_movimientos,
        'hoy': hoy,
        'fecha_filtro': hoy,
        'lotes': Lote.objects.select_related('presentacion__producto').all(),

    }
    return render(request, 'inventario/inventario_home.html', context)


@login_required
def gestion_stock(request):
    """Vista de stock completa para la página legacy "Stock & Productos"."""
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
        'breadcrumb_items': [
            {'nombre': 'Inventario', 'url': None},
        ],
    }
    return render(request, 'inventario/gestion_stock.html', context)


# ---------------------------------------------------------------------------
# Lote
# ---------------------------------------------------------------------------

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
    }
    return render(request, 'inventario/lote_list.html', context)


@login_required
def lote_detail(request, numero_lote):
    lote = get_object_or_404(Lote, numero_lote=numero_lote)
    movimientos = lote.movimientos.all()
    return render(request, 'inventario/lote_detail.html', {'lote': lote, 'movimientos': movimientos})

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
        return redirect('inventario:lote_list')

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


# ---------------------------------------------------------------------------
# Inventario (stock)
# ---------------------------------------------------------------------------

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
    movimientos = item.movimientos.all()
    return render(request, 'inventario/inventario_detail.html', {'item': item, 'movimientos': movimientos})


# ---------------------------------------------------------------------------
# Movimiento de inventario
# ---------------------------------------------------------------------------

@login_required
def movimiento_list(request):
    movimientos = MovimientoInventario.objects.select_related(
        'inventario', 'lote', 'registrado_por'
    )
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
        cantidad_raw = request.POST.get('cantidad')
        motivo = request.POST.get('motivo', '').strip()

        lote = get_object_or_404(Lote, pk=lote_id)

        try:
            cantidad = int(cantidad_raw)
        except (TypeError, ValueError):
            messages.error(request, 'La cantidad ingresada no es válida.')
            return redirect('inventario:inventario_home')

        if cantidad <= 0:
            messages.error(request, 'La cantidad debe ser mayor a cero.')
            return redirect('inventario:inventario_home')

        if tipo == 'entrada':
            lote.stock_actual += cantidad
        elif tipo == 'salida':
            if cantidad > lote.stock_actual:
                messages.error(request, f'No hay suficiente stock en el lote {lote.numero_lote}.')
                return redirect('inventario:inventario_home')
            lote.stock_actual -= cantidad
        else:
            messages.error(request, 'Tipo de movimiento no válido.')
            return redirect('inventario:inventario_home')

        lote.save()

        inventario = Inventario.objects.filter(presentacion=lote.presentacion).first()

        MovimientoInventario.objects.create(
            inventario=inventario,
            lote=lote,
            registrado_por=request.user,
            tipo=tipo,
            cantidad=cantidad,
            motivo=motivo or None,
            stock_resultante=lote.stock_actual,
        )

        messages.success(request, 'Movimiento registrado correctamente.')

    return redirect('inventario:inventario_home')

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

        inventario = Inventario.objects.filter(presentacion=lote.presentacion).first()

        if inventario:
            MovimientoInventario.objects.create(
                inventario=inventario,
                lote=lote,
                registrado_por=request.user,
                tipo='ajuste',
                cantidad=diferencia,
                motivo=motivo or f'Ajuste manual de stock del lote {lote.numero_lote}',
                stock_resultante=nuevo_stock,
            )
        else:
            messages.warning(request, 'Stock del lote actualizado, pero no se encontró un registro de Inventario asociado para dejar el historial del movimiento.')

        messages.success(request, f'Stock del lote {lote.numero_lote} actualizado a {nuevo_stock} unidades.')

    return redirect('inventario:gestion_stock')


# ---------------------------------------------------------------------------
# Agenda de inventario
# ---------------------------------------------------------------------------

@login_required
def agenda_list(request):
    estado = request.GET.get('estado')
    agendas = AgendaInventario.objects.select_related('documento_usuario', 'responsable')
    if estado:
        agendas = agendas.filter(estado=estado)
    return render(request, 'inventario/agenda_list.html', {'agendas': agendas, 'estado': estado})


@login_required
def agenda_create(request):
    if request.method == 'POST':
        form = AgendaInventarioForm(request.POST)
        if form.is_valid():
            agenda = form.save(commit=False)
            agenda.documento_usuario = request.user
            agenda.save()
            messages.success(request, f'Agenda "{agenda.titulo}" creada.')
            return redirect('inventario:agenda_list')
    else:
        form = AgendaInventarioForm()
    return render(request, 'inventario/agenda_form.html', {'form': form})


@login_required
def agenda_update(request, codigo):
    agenda = get_object_or_404(AgendaInventario, codigo=codigo)
    if request.method == 'POST':
        form = AgendaInventarioForm(request.POST, instance=agenda)
        if form.is_valid():
            form.save()
            messages.success(request, f'Agenda "{agenda.titulo}" actualizada.')
            return redirect('inventario:agenda_list')
    else:
        form = AgendaInventarioForm(instance=agenda)
    return render(request, 'inventario/agenda_form.html', {'form': form, 'agenda': agenda})


@login_required
def agenda_detail(request, codigo):
    agenda = get_object_or_404(AgendaInventario, codigo=codigo)
    hallazgos = agenda.hallazgos.all()
    return render(request, 'inventario/agenda_detail.html', {'agenda': agenda, 'hallazgos': hallazgos})


@login_required
def agenda_completar(request, codigo):
    agenda = get_object_or_404(AgendaInventario, codigo=codigo)
    agenda.estado = 'completada'
    agenda.save()
    messages.success(request, f'Agenda "{agenda.titulo}" marcada como completada.')
    return redirect('inventario:agenda_detail', codigo=agenda.codigo)


# ---------------------------------------------------------------------------
# Hallazgo
# ---------------------------------------------------------------------------

@login_required
def hallazgo_create(request, codigo_agenda):
    agenda = get_object_or_404(AgendaInventario, codigo=codigo_agenda)
    if request.method == 'POST':
        form = HallazgoForm(request.POST)
        if form.is_valid():
            hallazgo = form.save(commit=False)
            hallazgo.agenda = agenda
            hallazgo.save()
            messages.success(request, 'Hallazgo registrado correctamente.')
            return redirect('inventario:agenda_detail', codigo=agenda.codigo)
    else:
        form = HallazgoForm()
    return render(request, 'inventario/hallazgo_form.html', {'form': form, 'agenda': agenda})


@login_required
def hallazgo_list(request):
    tipo = request.GET.get('tipo')
    hallazgos = Hallazgo.objects.select_related('agenda', 'producto')
    if tipo:
        hallazgos = hallazgos.filter(tipo_hallazgo=tipo)
    return render(request, 'inventario/hallazgo_list.html', {'hallazgos': hallazgos, 'tipo': tipo})