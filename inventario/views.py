from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db import models as db_models
from django.db.models import Prefetch, Sum

from .models import Inventario, AgendaInventario, SesionConteo, ConteoProducto, Lote
from productos.models import Producto, PresentacionProducto, Categoria
from django.urls import reverse


@login_required
def inventario_home(request):
    if request.method == 'POST' and request.POST.get('titulo'):
        AgendaInventario.objects.create(
            titulo=request.POST.get('titulo'),
            fecha_programada=request.POST.get('fecha_programada'),
            descripcion=request.POST.get('descripcion', ''),
            creado_por=request.user,
            responsable=request.user,
        )
        messages.success(request, 'Inventario agendado correctamente.')
        return redirect('inventario_home')

    hoy          = timezone.now().date()
    fecha_filtro = request.GET.get('fecha_mov', str(hoy))

    movimientos = Inventario.objects.select_related(
        'lote__presentacion__producto__categoria',
        'registrado_por'
    ).filter(fecha_actualizada__date=fecha_filtro).order_by('-fecha_actualizada')

    dias_con_movimientos = Inventario.objects.dates('fecha_actualizada', 'day', order='DESC')[:30]
    agendas  = AgendaInventario.objects.order_by('fecha_programada')
    sesion   = SesionConteo.objects.filter(estado='activa').first()
    conteos  = ConteoProducto.objects.filter(sesion=sesion).select_related('presentacion__producto') if sesion else []

    productos = Producto.objects.select_related('categoria').prefetch_related(
        'presentaciones__lotes'
    ).annotate(
        stock_sum=Sum('presentaciones__lotes__stock_actual')
    ).all()

    categorias = Categoria.objects.all()

    discrepancias = []
    if sesion:
        for c in ConteoProducto.objects.filter(sesion=sesion).select_related('presentacion__producto__categoria'):
            diff = c.cantidad_contada - c.presentacion.cantidad
            discrepancias.append({
                'presentacion': c.presentacion,
                'en_sistema':   c.presentacion.cantidad,
                'fisico':       c.cantidad_contada,
                'diferencia':   diff,
                'estado':       'ok' if diff == 0 else ('sobrante' if diff > 0 else 'faltante'),
            })

    # =========================================================================
    # KPIs Y GRÁFICOS
    # =========================================================================

    ingresos_hoy = Lote.objects.filter(fecha_registro__date=hoy).aggregate(
        total=Sum('stock_actual')
    )['total'] or 0

    mes_actual  = timezone.now().month
    anio_actual = timezone.now().year
    ordenes_mes = Lote.objects.filter(
        fecha_registro__month=mes_actual,
        fecha_registro__year=anio_actual
    ).count()

    salidas_por_motivo = Inventario.objects.filter(tipo='salida').values('motivo').annotate(total=Sum('cantidad'))
    motivos_dict = {item['motivo'].lower(): item['total'] for item in salidas_por_motivo}
    chart_motivos_data = [
        motivos_dict.get('venta', 0),
        motivos_dict.get('merma', 0),
        motivos_dict.get('daño', 0),
        motivos_dict.get('vencido', 0)
    ]

    top_productos = Lote.objects.values('presentacion__producto__nombre').annotate(
        total_uds=Sum('stock_actual')
    ).order_by('-total_uds')[:5]

    proveedores_labels = [item['presentacion__producto__nombre'] for item in top_productos]
    proveedores_data   = [item['total_uds'] for item in top_productos]

    if not proveedores_labels:
        proveedores_labels = ['Sin datos', '-', '-', '-', '-']
        proveedores_data   = [0, 0, 0, 0, 0]
    else:
        while len(proveedores_labels) < 5:
            proveedores_labels.append('-')
            proveedores_data.append(0)


    context = {
        'movimientos':          movimientos,
        'dias_con_movimientos': dias_con_movimientos,
        'fecha_filtro':         fecha_filtro,
        'hoy':                  str(hoy),
        'agendas':              agendas,
        'sesion':               sesion,
        'conteos':              conteos,
        'productos':            productos,
        'categorias':           categorias,
        'discrepancias':        discrepancias,
        'con_codigo':           Producto.objects.exclude(codigo='').exclude(codigo=None).count(),
        'sin_codigo':           Producto.objects.filter(codigo=None).count() + Producto.objects.filter(codigo='').count(),
        'ingresos_hoy':         ingresos_hoy,
        'ordenes_mes':          ordenes_mes,
        'chart_motivos_data':   chart_motivos_data,
        'proveedores_labels':   proveedores_labels,
        'proveedores_data':     proveedores_data,
    }
    return render(request, 'inventario/inventario_home.html', context)


@login_required
def agenda_estado(request, pk):
    if request.method == 'POST':
        agenda = get_object_or_404(AgendaInventario, pk=pk)
        agenda.estado = request.POST.get('estado', agenda.estado)
        agenda.save()
        messages.success(request, 'Estado actualizado.')
    return redirect('inventario_home')


@login_required
def conteo_inventario(request):
    if request.method == 'POST' and request.POST.get('iniciar_sesion') is not None:
        SesionConteo.objects.filter(estado='activa').update(estado='finalizada')
        SesionConteo.objects.create(responsable=request.user, estado='activa')
        messages.success(request, 'Sesión de conteo iniciada.')
    return redirect('inventario_home')


@login_required
def guardar_conteo(request):
    if request.method == 'POST':
        sesion_id        = request.POST.get('sesion_id')
        producto_id      = request.POST.get('producto_id')
        cantidad_contada = int(request.POST.get('cantidad_contada', 0))

        sesion       = get_object_or_404(SesionConteo, pk=sesion_id)
        presentacion = PresentacionProducto.objects.filter(producto_id=producto_id).first()

        if presentacion:
            ConteoProducto.objects.update_or_create(
                sesion=sesion,
                presentacion=presentacion,
                defaults={'cantidad_contada': cantidad_contada}
            )
            messages.success(request, 'Conteo guardado.')
    return redirect('inventario_home')


@login_required
def ajustar_stock_presentacion(request, pk):
    presentacion = get_object_or_404(PresentacionProducto, pk=pk)

    if request.method != 'POST':
        return redirect('gestion_stock')

    stock_deseado_raw = request.POST.get('stock_deseado', '').strip()
    motivo = request.POST.get('motivo', '').strip() or 'Ajuste manual'

    try:
        stock_deseado = int(stock_deseado_raw)
        if stock_deseado < 0:
            raise ValueError
    except (ValueError, TypeError):
        messages.error(request, '⚠️ Stock deseado inválido.')
        return redirect('gestion_stock')

    stock_real = presentacion.lotes.aggregate(total=Sum('stock_actual'))['total'] or 0
    diff = stock_deseado - stock_real

    if diff == 0:
        messages.info(request, f'ℹ️ El stock de "{presentacion.nombre}" ya es {stock_real} uds.')
        return redirect('gestion_stock')

    if diff > 0:
        import uuid
        numero_lote = f"AJU-{uuid.uuid4().hex[:8].upper()}"
        lote = Lote.objects.create(
            numero_lote=numero_lote,
            presentacion=presentacion,
            costo_unitario=0,
            stock_actual=diff,
            fecha_vencimiento=None,
            registrado_por=request.user,
        )
        Inventario.objects.create(
            presentacion=presentacion,
            lote=lote,
            registrado_por=request.user,
            tipo='ajuste',
            cantidad=diff,
            motivo=motivo,
            stock_resultante=lote.stock_actual,
        )
        messages.success(request, f'✅ Ajuste: +{diff} uds a "{presentacion.nombre}" (lote {numero_lote}).')

    else:
        restante = abs(diff)
        if restante > stock_real:
            messages.error(request, f'⚠️ No hay suficiente stock para ese ajuste (stock real: {stock_real} uds).')
            return redirect('gestion_stock')

        lotes_qs = presentacion.lotes.filter(stock_actual__gt=0).order_by(
            db_models.F('fecha_vencimiento').asc(nulls_last=True), 'id'
        )
        lote_principal = None
        for lote in lotes_qs:
            if restante <= 0:
                break
            if lote_principal is None:
                lote_principal = lote
            descuento = min(lote.stock_actual, restante)
            lote.stock_actual -= descuento
            lote.save()
            restante -= descuento

        if lote_principal:
            Inventario.objects.create(
                presentacion=presentacion,
                lote=lote_principal,
                registrado_por=request.user,
                tipo='ajuste',
                cantidad=abs(diff),
                motivo=motivo,
                stock_resultante=lote_principal.stock_actual,
            )
        messages.success(request, f'✅ Ajuste: {diff} uds de "{presentacion.nombre}".')

    return redirect('gestion_stock')


@login_required
def guardar_codigo(request, pk):
    if request.method == 'POST':
        producto = get_object_or_404(Producto, pk=pk)
        producto.codigo = request.POST.get('codigo', '').strip()
        producto.save()
        messages.success(request, f'Código guardado para {producto.nombre}.')
    return redirect('inventario_home')


@login_required
def editar_movimiento(request, pk):
    if request.method == 'POST':
        mov = get_object_or_404(Inventario, pk=pk)
        try:
            tipo_nuevo     = request.POST.get('tipo', mov.tipo)
            cantidad_nueva = abs(int(request.POST.get('cantidad', mov.cantidad)))
            motivo_nuevo   = request.POST.get('motivo', mov.motivo)

            lote = mov.lote
            cantidad_anterior = abs(mov.cantidad)

            if mov.tipo == 'entrada' or mov.tipo == 'ajuste':
                lote.stock_actual -= cantidad_anterior
            else:
                lote.stock_actual += cantidad_anterior

            if tipo_nuevo == 'entrada' or tipo_nuevo == 'ajuste':
                lote.stock_actual += cantidad_nueva
            else:
                if lote.stock_actual < cantidad_nueva:
                    messages.error(request, f'⚠️ Stock insuficiente ({lote.stock_actual} uds disponibles).')
                    return redirect('inventario_home')
                lote.stock_actual -= cantidad_nueva

            lote.save()

            mov.tipo             = tipo_nuevo
            mov.cantidad         = cantidad_nueva
            mov.motivo           = motivo_nuevo
            mov.stock_resultante = lote.stock_actual
            mov.save()

            messages.success(request, '✅ Movimiento actualizado y stock corregido.')
        except (ValueError, TypeError):
            messages.error(request, '❌ Cantidad inválida.')
    return redirect('inventario_home')




@login_required
def registrar_salida_view(request):
    hoy         = timezone.now().date()
    mes_actual  = timezone.now().month
    anio_actual = timezone.now().year

    productos = Producto.objects.select_related('categoria').prefetch_related(
        'presentaciones__lotes'
    ).all()

    ordenes_mes = Lote.objects.filter(
        fecha_registro__month=mes_actual,
        fecha_registro__year=anio_actual
    ).count()

    salidas_por_motivo = Inventario.objects.filter(tipo='salida').values('motivo').annotate(total=Sum('cantidad'))
    motivos_dict = {item['motivo'].lower(): item['total'] for item in salidas_por_motivo}
    chart_motivos_data = [
        motivos_dict.get('venta', 0),
        motivos_dict.get('merma', 0),
        motivos_dict.get('daño', 0),
        motivos_dict.get('vencido', 0),
    ]

    context = {
        'productos':          productos,
        'ordenes_mes':        ordenes_mes,
        'chart_motivos_data': chart_motivos_data,
    }
    return render(request, 'inventario/registrar_salida.html', context)


@login_required
def gestion_lotes_view(request):
    hoy         = timezone.now().date()
    mes_actual  = timezone.now().month
    anio_actual = timezone.now().year

    productos = Producto.objects.select_related('categoria').prefetch_related(
        'presentaciones__lotes'
    ).all()

    ingresos_hoy = Lote.objects.filter(
        fecha_registro__date=hoy
    ).aggregate(total=Sum('stock_actual'))['total'] or 0

    ordenes_mes = Lote.objects.filter(
        fecha_registro__month=mes_actual,
        fecha_registro__year=anio_actual
    ).count()

    top_productos = Lote.objects.values('presentacion__producto__nombre').annotate(
        total_uds=Sum('stock_actual')
    ).order_by('-total_uds')[:5]

    proveedores_labels = [item['presentacion__producto__nombre'] for item in top_productos]
    proveedores_data   = [item['total_uds'] for item in top_productos]

    if not proveedores_labels:
        proveedores_labels = ['Sin datos']
        proveedores_data   = [0]

    context = {
        'productos':          productos,
        'ingresos_hoy':       ingresos_hoy,
        'ordenes_mes':        ordenes_mes,
        'proveedores_labels': proveedores_labels,
        'proveedores_data':   proveedores_data,
    }
    return render(request, 'inventario/gestion_lotes.html', context)

@login_required
def gestion_salida(request):
    if request.method == 'POST':
        presentacion_id = request.POST.get('presentacion')
        cantidad_raw    = request.POST.get('cantidad', '')
        motivo          = request.POST.get('motivo', '').strip()
        lote_id         = request.POST.get('lote_id') or None

        if not presentacion_id:
            messages.error(request, '⚠️ Debes seleccionar una presentación.')
            return redirect('registrar_salida_view')

        try:
            cantidad = int(cantidad_raw)
            if cantidad <= 0:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, '⚠️ La cantidad debe ser un número mayor a cero.')
            return redirect('registrar_salida_view')

        if not motivo:
            messages.error(request, '⚠️ Debes indicar el motivo de la salida.')
            return redirect('registrar_salida_view')

        if lote_id:
            lote = get_object_or_404(Lote, pk=lote_id)
            if lote.fecha_vencimiento and lote.fecha_vencimiento < timezone.now().date():
                messages.error(request, f'🚫 El lote "{lote.numero_lote}" está vencido.')
                return redirect('registrar_salida_view')

        presentacion = get_object_or_404(PresentacionProducto, pk=presentacion_id)

        if cantidad > presentacion.cantidad:
            messages.error(request, f'⚠️ Stock insuficiente: solo hay {presentacion.cantidad} unidades.')
            return redirect('registrar_salida_view')

        restante = cantidad
        lotes_qs = presentacion.lotes.filter(stock_actual__gt=0).order_by(
            db_models.F('fecha_vencimiento').asc(nulls_last=True), 'id'
        )
        for lote in lotes_qs:
            if restante <= 0:
                break
            if lote.stock_actual >= restante:
                lote.stock_actual -= restante
                lote.save()
                restante = 0
            else:
                restante -= lote.stock_actual
                lote.stock_actual = 0
                lote.save()

        lote_referencia = presentacion.lotes.order_by('fecha_vencimiento').first()
        Inventario.objects.create(
            presentacion=presentacion,
            lote=lote_referencia,
            registrado_por=request.user,
            tipo='salida',
            cantidad=cantidad,
            motivo=motivo,
            stock_resultante=lote_referencia.stock_actual if lote_referencia else None,
        )
        messages.success(request, f'✅ Salida de {cantidad} unidades de "{presentacion.nombre}" registrada.')

    return redirect('registrar_salida_view')












@login_required
def registrar_lote(request):
    if request.method == 'POST':
        numero_lote           = request.POST.get('numero_lote', '').strip()
        presentacion_id       = request.POST.get('presentacion_lote')
        costo_unitario        = request.POST.get('costo_unitario', 0)
        stock_inicial         = request.POST.get('cantidad_lote', 0)
        fecha_vencimiento_str = request.POST.get('fecha_vencimiento', '').strip()

        if fecha_vencimiento_str:
            from datetime import date
            try:
                fecha_vencimiento = date.fromisoformat(fecha_vencimiento_str)
            except ValueError:
                fecha_vencimiento = None
        else:
            fecha_vencimiento = None

        if not numero_lote:
            messages.error(request, '⚠️ El número de lote es obligatorio.')
            return redirect('gestion_lotes_view')

        if not presentacion_id:
            messages.error(request, '⚠️ Debes seleccionar una presentación.')
            return redirect('gestion_lotes_view')

        if Lote.objects.filter(numero_lote=numero_lote).exists():
            messages.error(request, f'⚠️ El lote "{numero_lote}" ya está registrado.')
            return redirect('gestion_lotes_view')

        presentacion = get_object_or_404(PresentacionProducto, pk=presentacion_id)

        try:
            stock_inicial_int = int(stock_inicial)
        except (ValueError, TypeError):
            stock_inicial_int = 0

        lote = Lote.objects.create(
            numero_lote=numero_lote,
            presentacion=presentacion,
            costo_unitario=costo_unitario,
            stock_actual=stock_inicial_int,
            fecha_vencimiento=fecha_vencimiento,
            registrado_por=request.user,
        )

        if fecha_vencimiento:
            messages.success(request, f'✅ Lote "{numero_lote}" registrado — vence el {lote.fecha_vencimiento.strftime("%d/%m/%Y")}.')
        else:
            messages.success(request, f'✅ Lote "{numero_lote}" registrado para "{presentacion.producto.nombre}".')

    return redirect('gestion_lotes_view')


@login_required
def gestion_stock(request):
    productos = Producto.objects.select_related('categoria').prefetch_related(
        'presentaciones__lotes'
    ).all()

    categorias    = Categoria.objects.filter(padre=None).prefetch_related('subcategorias', 'productos__presentaciones')
    todas_cats    = Categoria.objects.all()

    lotes_activos = Lote.objects.select_related(
        'presentacion__producto__categoria',
        'registrado_por'
    ).filter(stock_actual__gt=0).order_by(
        db_models.F('fecha_vencimiento').asc(nulls_last=True)
    )

    hoy               = timezone.now().date()
    lotes_por_vencer = [l for l in lotes_activos if l.proximo_a_vencer]
    lotes_vencidos   = [l for l in lotes_activos if l.esta_vencido]

    context = {
        'productos':        productos,
        'categorias':       categorias,
        'todas_cats':       todas_cats,
        'lotes_activos':    lotes_activos,
        'lotes_por_vencer': lotes_por_vencer,
        'lotes_vencidos':   lotes_vencidos,
        'total_criticos':   0,
        'hoy':              hoy,
    }
    return render(request, 'inventario/gestion_stock.html', context)




@login_required
def editar_lote_stock(request, pk):
    lote = get_object_or_404(Lote, pk=pk)

    if request.method != 'POST':
        return redirect('gestion_stock')

    nuevo_stock_raw = request.POST.get('nuevo_stock', '').strip()
    motivo = request.POST.get('motivo', '').strip() or 'Corrección de lote'

    try:
        nuevo_stock = int(nuevo_stock_raw)
        if nuevo_stock < 0:
            raise ValueError
    except (ValueError, TypeError):
        messages.error(request, '⚠️ Stock inválido.')
        return redirect('gestion_stock')

    stock_anterior = lote.stock_actual
    diff = nuevo_stock - stock_anterior

    if diff == 0:
        messages.info(request, f'ℹ️ El lote "{lote.numero_lote}" ya tiene {nuevo_stock} uds.')
        return redirect('gestion_stock')

    costo_raw = request.POST.get('costo_unitario', '').strip()
    if costo_raw:
        try:
            lote.costo_unitario = max(0, float(costo_raw))
        except (ValueError, TypeError):
            pass
    
    lote.stock_actual = nuevo_stock
    lote.save()

    Inventario.objects.create(
        presentacion=lote.presentacion,
        lote=lote,
        registrado_por=request.user,
        tipo='ajuste',
        cantidad=abs(diff),
        motivo=motivo,
        stock_resultante=lote.stock_actual,
    )

    signo = f'+{diff}' if diff > 0 else str(diff)
    messages.success(
        request,
        f'✅ Lote "{lote.numero_lote}" actualizado: {stock_anterior} → {nuevo_stock} uds ({signo}).'
    )

    return redirect('gestion_stock')
# ===============================
# FUNCIONES MOVIDAS DESDE PRODUCTOS
# ===============================
@login_required
def stock_status(request):
    productos = Producto.objects.prefetch_related('presentaciones__lotes').all()
    criticos, bajos = [], []

    for p in productos:
        stock_total = p.presentaciones.aggregate(total=Sum('lotes__stock_actual'))['total'] or 0
        
        # Tomamos la primera presentación para la URL de lotes
        primera_pres = p.presentaciones.first()
        pres_pk = primera_pres.pk if primera_pres else None
        
        entrada = {
            'nombre':           p.nombre,
            'cantidad':          stock_total,
            'url_presentacion':  reverse('gestion_productos'),
            'url_lote':          reverse('gestion_lotes_view') + f'?tab=lote&presentacion={pres_pk}' if pres_pk else '#',
        }
        
        if stock_total == 0:
            criticos.append(entrada)
        elif stock_total <= 5:
            bajos.append(entrada)

    if criticos:
        estado = 'rojo'
    elif bajos:
        estado = 'amarillo'
    else:
        estado = 'verde'

    return JsonResponse({
        'estado':        estado,
        'total_alertas': len(criticos) + len(bajos),
        'criticos':      criticos,
        'bajos':         bajos,
    })

@login_required
def producto_salida(request):
    if request.method != 'POST':
        return redirect('lista_productos')

    presentacion_id = request.POST.get('presentacion_id') or request.POST.get('presentacion')
    cantidad_raw    = request.POST.get('cantidad', 0)
    motivo          = request.POST.get('motivo', 'Salida manual')

    try:
        cantidad = int(cantidad_raw)
        if cantidad <= 0:
            raise ValueError
    except (ValueError, TypeError):
        messages.error(request, '⚠️ Cantidad inválida.')
        return redirect('lista_productos')

    if not presentacion_id:
        messages.error(request, '⚠️ Debes seleccionar una presentación.')
        return redirect('lista_productos')

    presentacion = get_object_or_404(PresentacionProducto, pk=presentacion_id)
    stock_actual = presentacion.lotes.aggregate(total=Sum('stock_actual'))['total'] or 0

    if cantidad > stock_actual:
        messages.error(
            request,
            f"⚠️ Stock insuficiente: solo hay {stock_actual} unidades de '{presentacion.nombre}'."
        )
        return redirect('lista_productos')

    # Descuento FEFO
    restante = cantidad
    for lote in presentacion.lotes.filter(stock_actual__gt=0).order_by('fecha_vencimiento'):
        if restante <= 0:
            break
        descuento         = min(lote.stock_actual, restante)
        lote.stock_actual -= descuento
        lote.save()
        restante          -= descuento

    Inventario.objects.create(
        presentacion=presentacion,
        lote=presentacion.lotes.order_by('fecha_vencimiento').first(),
        tipo='salida',
        cantidad=cantidad,
        motivo=motivo,
        registrado_por=request.user,
    )
    messages.success(
        request,
        f"✅ Salida registrada: {cantidad} × '{presentacion.nombre}'. Motivo: {motivo}."
    )
    return redirect('lista_productos')

@login_required
def rotacion_json(request):
    hace_30 = timezone.now() - timedelta(days=30)

    rotacion_qs = (
        Inventario.objects
        .filter(tipo='salida', fecha_actualizada__gte=hace_30)
        .values('presentacion__producto__pk', 'presentacion__producto__nombre')
        .annotate(total_vendido=Sum('cantidad'))
        .order_by('-total_vendido')[:15]
    )

    ids_con_movimiento = {r['presentacion__producto__pk'] for r in rotacion_qs}
    sin_movimiento     = list(
        Producto.objects.exclude(pk__in=ids_con_movimiento).values('pk', 'nombre')
    )

    estrella_nombre        = None
    estrella_categoria     = None
    estrella_vendido       = 0
    estrella_stock         = 0
    estrella_stock_critico = False
    estrella_presentacion  = None
    estrella_ingresos      = 0

    if rotacion_qs:
        top = rotacion_qs[0]
        try:
            prod = Producto.objects.select_related('categoria').prefetch_related('presentaciones__lotes').get(
                pk=top['presentacion__producto__pk']
            )
            estrella_nombre        = prod.nombre
            estrella_categoria     = prod.categoria.nombre if prod.categoria else ''
            estrella_vendido       = top['total_vendido']
            
            # Cálculo seguro de stock total de presentaciones
            estrella_stock         = prod.presentaciones.aggregate(total=Sum('lotes__stock_actual'))['total'] or 0
            estrella_stock_critico = getattr(prod, 'stock_critico', False)

            pres_top = (
                Inventario.objects
                .filter(tipo='salida', fecha_actualizada__gte=hace_30, presentacion__producto=prod)
                .values('presentacion__nombre')
                .annotate(total=Sum('cantidad'))
                .order_by('-total')
                .first()
            )
            if pres_top:
                estrella_presentacion = pres_top['presentacion__nombre']

            estrella_ingresos = (
                Inventario.objects
                .filter(tipo='salida', fecha_actualizada__gte=hace_30, presentacion__producto=prod)
                .aggregate(total=Sum('cantidad'))['total'] or 0
            )
        except Producto.DoesNotExist:
            pass

    return JsonResponse({
        'rotacion':               [{'nombre': r['presentacion__producto__nombre'], 'cantidad': r['total_vendido']} for r in rotacion_qs],
        'sin_movimiento':         [{'nombre': p['nombre'], 'cantidad': 0} for p in sin_movimiento],
        'estrella_nombre':        estrella_nombre,
        'estrella_categoria':     estrella_categoria,
        'estrella_vendido':       estrella_vendido,
        'estrella_ingresos':      estrella_ingresos,
        'estrella_presentacion':  estrella_presentacion,
        'estrella_stock':         estrella_stock,
        'estrella_stock_critico': estrella_stock_critico,
    })

@login_required
def agenda_lista(request):
    agendas = AgendaInventario.objects.all().order_by('fecha_programada')
    context = {
        'agendas': agendas,
    }
    return render(request, 'inventario/inventario_home.html', context)

@login_required
def agenda_eliminar(request, pk):
    agenda = get_object_or_404(AgendaInventario, pk=pk)
    if request.method == 'POST':
        agenda.delete()
        messages.success(request, '✅ Registro de agenda eliminado.')
    return redirect('agenda_lista')

