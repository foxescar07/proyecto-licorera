from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from inventario.models import Inventario
from .forms import FiltroReporteForm
from django.utils import timezone

@login_required
def index_reportes(request):
    """
    Vista para la página principal de reportes (http://127.0.0.1:8000/reportes/)
    """
    context = {
        'titulo': "Panel General de Reportes",
        'hoy': timezone.now()
    }
    # Si moviste el archivo a la subcarpeta como buena práctica, usa 'reportes/reportes.html'
    return render(request, 'reportes.html', context)

@login_required
def reporte_movimientos(request):
    """
    Vista para el reporte filtrado de movimientos (http://127.0.0.1:8000/reportes/movimientos/)
    """
    form = FiltroReporteForm(request.GET or None)
    movimientos = Inventario.objects.none()

    if form.is_valid():
        f_inicio = form.cleaned_data['fecha_inicio']
        f_fin = form.cleaned_data['fecha_fin']
        tipo = form.cleaned_data['tipo_reporte']

        movimientos = Inventario.objects.filter(
            fecha_actualizada__date__range=[f_inicio, f_fin]
        ).select_related('lote__presentacion__producto')

        if tipo != 'general':
            movimientos = movimientos.filter(tipo=tipo[:-1]) # quita la 's' de 'entradas'/'salidas'

    context = {
        'form': form,
        'movimientos': movimientos,
        'titulo': "Reporte de Movimientos de Inventario",
        'hoy': timezone.now()
    }
    return render(request, 'reportes/reporte_movimientos.html', context)