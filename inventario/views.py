from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

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


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
def inventario_home(request):
    lotes_por_vencer = [l for l in Lote.objects.all() if l.proximo_a_vencer]
    lotes_vencidos    = [l for l in Lote.objects.all() if l.esta_vencido]
    bajo_stock        = Inventario.objects.filter(stock_actual__lte=F('stock_min'))
    agendas_pendientes = AgendaInventario.objects.filter(estado='pendiente')

    context = {
        'lotes_por_vencer': lotes_por_vencer,
        'lotes_vencidos': lotes_vencidos,
        'bajo_stock': bajo_stock,
        'agendas_pendientes': agendas_pendientes,
    }
    return render(request, 'inventario/inventario_home.html', context)


# ---------------------------------------------------------------------------
# Lote
# ---------------------------------------------------------------------------

@login_required
def lote_list(request):
    query = request.GET.get('q', '')
    lotes = Lote.objects.select_related('presentacion', 'registrado_por')
    if query:
        lotes = lotes.filter(
            Q(numero_lote__icontains=query) |
            Q(presentacion__producto__nombre__icontains=query)
        )
    return render(request, 'inventario/lote_list.html', {'lotes': lotes, 'query': query})


@login_required
def lote_detail(request, codigo):
    lote = get_object_or_404(Lote, codigo=codigo)
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
            return redirect('inventario:lote_list')
    else:
        form = LoteForm()
    return render(request, 'inventario/lote_form.html', {'form': form})


@login_required
def lote_update(request, codigo):
    lote = get_object_or_404(Lote, codigo=codigo)
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
        form = MovimientoInventarioForm(request.POST)
        if form.is_valid():
            movimiento = form.save(commit=False)
            movimiento.registrado_por = request.user

            inventario = movimiento.inventario
            if movimiento.tipo == 'entrada':
                inventario.stock_actual += movimiento.cantidad
            elif movimiento.tipo == 'salida':
                if movimiento.cantidad > inventario.stock_actual:
                    messages.error(request, 'La salida supera el stock disponible.')
                    return render(request, 'inventario/movimiento_form.html', {'form': form})
                inventario.stock_actual -= movimiento.cantidad
            else:  # ajuste
                inventario.stock_actual = movimiento.cantidad

            inventario.save()
            movimiento.stock_resultante = inventario.stock_actual
            movimiento.save()

            messages.success(request, 'Movimiento registrado correctamente.')
            return redirect('inventario:movimiento_list')
    else:
        form = MovimientoInventarioForm()
    return render(request, 'inventario/movimiento_form.html', {'form': form})


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