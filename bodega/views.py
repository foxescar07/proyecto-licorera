from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from productos.models import Producto
from .models import AgendaInventario, Hallazgo
from .forms import AgendaInventarioForm, HallazgoForm 

@login_required
def bodega_home(request):
    agendas = AgendaInventario.objects.all()
    # Procesar modal de agendar si se envía por POST a esta ruta
    if request.method == 'POST' and 'Agendar' in request.POST:
        titulo = request.POST.get('titulo')
        fecha_programada = request.POST.get('fecha_programada')
        descripcion = request.POST.get('descripcion')
        AgendaInventario.objects.create(
            titulo=titulo, fecha=fecha_programada, descripcion=descripcion,
            documento_usuario=request.user
        )
        messages.success(request, "Inventario programado correctamente.")
        return redirect('bodega:bodega_home')

    context = {
        'agendas': agendas,
        'productos': Producto.objects.all(),
        # Variables de plantillas para conteo y discrepancias
        'conteos': [],
        'discrepancias': [],
        'sesion': None,
    }
    return render(request, 'bodega_home.html', context)

@login_required
def agenda_list(request):
    estado = request.GET.get('estado')
    agendas = AgendaInventario.objects.select_related('documento_usuario', 'responsable')
    if estado:
        agendas = agendas.filter(estado=estado)
    return render(request, 'agenda_list.html', {'agendas': agendas, 'estado': estado})

@login_required
def agenda_create(request):
    if request.method == 'POST':
        form = AgendaInventarioForm(request.POST)
        if form.is_valid():
            agenda = form.save(commit=False)
            agenda.documento_usuario = request.user
            agenda.save()
            messages.success(request, f'Agenda "{agenda.titulo}" creada.')
            return redirect('bodega:bodega_home')
    else:
        form = AgendaInventarioForm()
    return render(request, 'agenda_form.html', {'form': form})

@login_required
def agenda_update(request, codigo):
    agenda = get_object_or_404(AgendaInventario, pk=codigo)
    if request.method == 'POST':
        if 'estado' in request.POST:
            agenda.estado = request.POST.get('estado')
            if agenda.estado == 'completada':
                agenda.completado_por = request.user
            agenda.save()
            messages.success(request, "Estado de agenda actualizado.")
            return redirect('bodega:bodega_home')
            
        form = AgendaInventarioForm(request.POST, instance=agenda)
        if form.is_valid():
            form.save()
            return redirect('bodega:bodega_home')
    else:
        form = AgendaInventarioForm(instance=agenda)
    return render(request, 'agenda_form.html', {'form': form, 'agenda': agenda})

@login_required
def agenda_detail(request, codigo):
    agenda = get_object_or_404(AgendaInventario, pk=codigo)
    return render(request, 'agenda_detail.html', {'agenda': agenda, 'hallazgos': agenda.hallazgos.all()})

@login_required
def agenda_completar(request, codigo):
    agenda = get_object_or_404(AgendaInventario, pk=codigo)
    agenda.estado = 'completada'
    agenda.completado_por = request.user
    agenda.save()
    messages.success(request, f'Agenda "{agenda.titulo}" completada.')
    return redirect('bodega:bodega_home')

@login_required
def hallazgo_create(request, codigo_agenda):
    agenda = get_object_or_404(AgendaInventario, pk=codigo_agenda)
    if request.method == 'POST':
        form = HallazgoForm(request.POST)
        if form.is_valid():
            hallazgo = form.save(commit=False)
            hallazgo.agenda = agenda
            hallazgo.save()
            messages.success(request, 'Hallazgo registrado correctamente.')
            return redirect('bodega:agenda_detail', codigo=agenda.pk)
    else:
        form = HallazgoForm()
    return render(request, 'hallazgo_form.html', {'form': form, 'agenda': agenda})

@login_required
def hallazgo_list(request):
    tipo = request.GET.get('tipo')
    hallazgos = Hallazgo.objects.select_related('agenda', 'producto')
    if tipo:
        hallazgos = hallazgos.filter(tipo_hallazgo=tipo)
    return render(request, 'hallazgo_list.html', {'hallazgos': hallazgos, 'tipo': tipo})