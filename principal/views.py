import json
from datetime import timedelta

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Sum, Count

from ventas.models import Venta
from productos.models import Categoria

DIAS_SEMANA   = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
MESES         = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
                  'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
MESES_LABEL   = ['ene', 'feb', 'mar', 'abr', 'may', 'jun',
                  'jul', 'ago', 'sep', 'oct', 'nov', 'dic']


# ════════════════════════════════════════
# HELPERS DE DATOS
# ════════════════════════════════════════

def _lunes_de_semana(offset=0):
    hoy = timezone.localdate()
    lunes_actual = hoy - timedelta(days=hoy.weekday())
    return lunes_actual - timedelta(weeks=offset)


def _datos_semana(offset=0):
    offset = max(0, offset)
    lunes    = _lunes_de_semana(offset)
    domingo  = lunes + timedelta(days=6)
    hoy      = timezone.localdate()

    labels, data, data_count = [], [], []

    for i in range(7):
        dia = lunes + timedelta(days=i)
        ventas_dia = Venta.objects.filter(fecha__date=dia)
        total = ventas_dia.aggregate(t=Sum('total_con_descuento'))['t'] or 0
        labels.append(DIAS_SEMANA[i])
        data.append(float(total))
        data_count.append(ventas_dia.count())

    es_actual = (offset == 0)

    ventas_hoy     = Venta.objects.filter(fecha__date=hoy)
    total_hoy      = float(ventas_hoy.aggregate(t=Sum('total_con_descuento'))['t'] or 0)
    ventas_hoy_num = ventas_hoy.count()

    dias_con_datos = sum(1 for d in data if d > 0)
    prom_diario    = (sum(data) / dias_con_datos) if dias_con_datos else 0

    if any(data):
        idx_mejor     = data.index(max(data))
        mejor_dia     = labels[idx_mejor]
        mejor_dia_val = data[idx_mejor]
    else:
        mejor_dia     = '—'
        mejor_dia_val = 0

    if lunes.month == domingo.month:
        semana_label = f"{lunes.day} - {domingo.day} {MESES_LABEL[lunes.month - 1]}"
    else:
        semana_label = (f"{lunes.day} {MESES_LABEL[lunes.month - 1]} - "
                         f"{domingo.day} {MESES_LABEL[domingo.month - 1]}")

    return {
        'labels':          labels,
        'data':            data,
        'data_count':      data_count,
        'semana_label':    semana_label,
        'offset':          offset,
        'es_actual':       es_actual,
        'total_hoy':       total_hoy,
        'ventas_hoy_num':  ventas_hoy_num,
        'prom_diario':     prom_diario,
        'mejor_dia':       mejor_dia,
        'mejor_dia_val':   mejor_dia_val,
    }


def _datos_mensuales():
    anio = timezone.localdate().year
    labels, data, data_count = [], [], []

    for mes in range(1, 13):
        ventas_mes = Venta.objects.filter(fecha__year=anio, fecha__month=mes)
        total = ventas_mes.aggregate(t=Sum('total_con_descuento'))['t'] or 0
        labels.append(MESES[mes - 1])
        data.append(float(total))
        data_count.append(ventas_mes.count())

    meses_con_datos = [i for i, v in enumerate(data) if v > 0]

    idx_mejores, idx_peores = [], []
    if meses_con_datos:
        ordenados   = sorted(meses_con_datos, key=lambda i: data[i], reverse=True)
        idx_mejores = ordenados[:3]
        idx_peores  = [i for i in ordenados[-3:] if i not in idx_mejores]

    colores = []
    for i in range(12):
        if i in idx_mejores:
            colores.append('rgba(29,158,117,0.85)')
        elif i in idx_peores:
            colores.append('rgba(220,53,69,0.75)')
        else:
            colores.append('rgba(167,139,250,0.75)')

    return {
        'labels':      labels,
        'data':        data,
        'data_count':  data_count,
        'colores':     colores,
        'idx_mejores': idx_mejores,
        'idx_peores':  idx_peores,
    }


def _resumen_meses(mensual):
    mejores = [(mensual['labels'][i], mensual['data'][i], mensual['data_count'][i])
               for i in mensual['idx_mejores']]
    peores  = [(mensual['labels'][i], mensual['data'][i], mensual['data_count'][i])
               for i in mensual['idx_peores']]
    return mejores, peores


def _grupos_categorias():
    categorias = Categoria.objects.annotate(total=Count('productos')).order_by('nombre')
    grupos, actual = [], []
    for cat in categorias:
        actual.append(cat)
        if len(actual) == 6:
            grupos.append(actual)
            actual = []
    if actual:
        grupos.append(actual)
    return grupos


# ════════════════════════════════════════
# VISTAS
# ════════════════════════════════════════

def principal(request):
    if not request.session.get('usuario_id'):
        return redirect('login')

    semana  = _datos_semana(offset=0)
    mensual = _datos_mensuales()
    mejores_meses, peores_meses = _resumen_meses(mensual)

    context = {
        'grupos_categorias': _grupos_categorias(),

        'semana_label':    semana['semana_label'],
        'offset':          semana['offset'],
        'total_hoy':       semana['total_hoy'],
        'ventas_hoy_num':  semana['ventas_hoy_num'],
        'prom_diario':     semana['prom_diario'],
        'mejor_dia':       semana['mejor_dia'],
        'mejor_dia_val':   semana['mejor_dia_val'],

        # se inyectan crudos en el <script> como JS arrays
        'labels':     json.dumps(semana['labels'], ensure_ascii=False),
        'data':       json.dumps(semana['data']),
        'data_count': json.dumps(semana['data_count']),

        'mejores_meses': mejores_meses,
        'peores_meses':  peores_meses,
    }
    return render(request, 'principal.html', context)


def semana_json(request):
    if not request.session.get('usuario_id'):
        return JsonResponse({'error': 'no autorizado'}, status=403)
    try:
        offset = int(request.GET.get('offset', 0))
    except (TypeError, ValueError):
        offset = 0
    return JsonResponse(_datos_semana(offset))


def meses_json(request):
    if not request.session.get('usuario_id'):
        return JsonResponse({'error': 'no autorizado'}, status=403)
    return JsonResponse(_datos_mensuales())


def cerrar_sesion(request):
    request.session.flush()
    return redirect('login')  