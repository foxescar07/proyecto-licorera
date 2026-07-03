# proveedores/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from .models import Proveedor, Compra, OrdenCompra, DetalleCompra, HistorialOrden
from .forms import ProveedorForm, CompraForm, OrdenCompraForm, DetalleCompraForm
from productos.models import Producto
from inventario.models import Lote, Inventario
import json
from django.db.models.functions import TruncMonth

@login_required
def lista_proveedores(request):
    proveedores = Proveedor.objects.all()

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

    # Paginación
    paginator = Paginator(proveedores, 10)  # 10 proveedores por página
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'proveedores': page_obj.object_list,
        'page_obj': page_obj,
        'paginator': paginator,
        'total_proveedores': total_proveedores,
        'proveedores_activos': proveedores_activos,
        'proveedores_inactivos': proveedores_inactivos,
        'proveedores_sancionados': proveedores_sancionados,
        'porcentaje_activos': porcentaje_activos,
    }

    return render(request, 'proveedores/proveedores.html', context)

@login_required
def crear_proveedor(request):
    if request.method == 'POST':
        form = ProveedorForm(request.POST)
        if form.is_valid():
            proveedor = form.save(commit=False)
            proveedor.registrado_por = request.user
            proveedor.save()
            messages.success(request, f'Proveedor {proveedor.nombre_empresa} creado exitosamente.')
            return redirect('lista_proveedores')
        else:
            # Si hay errores, mostrarlos
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
            proveedor_guardado.modificado_por = request.user
            proveedor_guardado.save()
            messages.success(request, f'Proveedor {proveedor.nombre_empresa} actualizado exitosamente.')
            return redirect('lista_proveedores')
    else:
        form = ProveedorForm(instance=proveedor)

    context = {
        'form': form,
        'proveedor': proveedor,
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
        'proveedor': proveedor
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
    todos_proveedores = Proveedor.objects.all().order_by('nombre_empresa')
    proveedor = None
    form = None

    # Obtener proveedor de sesión o parámetro GET
    if request.method == 'POST':
        proveedor_id = request.POST.get('proveedor_id') or request.session.get('proveedor_id')
    else:
        proveedor_id = request.GET.get('proveedor') or request.session.get('proveedor_id')

    # Guardar proveedor en sesión
    if proveedor_id:
        try:
            request.session['proveedor_id'] = int(proveedor_id)
            proveedor = Proveedor.objects.get(id=request.session['proveedor_id'])
        except (Proveedor.DoesNotExist, ValueError):
            proveedor = None
    else:
        primer_proveedor = todos_proveedores.first()
        if primer_proveedor:
            request.session['proveedor_id'] = primer_proveedor.id
            proveedor = primer_proveedor

    compras = []
    if proveedor:
        compras = Compra.objects.filter(proveedor=proveedor).order_by('-fecha_registro')

    # Calcular subtotal
    subtotal = sum(
        (c.cantidad * c.precio_unitario) for c in compras
        if c.precio_unitario
    ) or 0

    # Registrar nueva compra
    if request.method == 'POST':
        if not proveedor:
            messages.error(request, 'Por favor selecciona un proveedor.')
            return redirect('lista_compras')

        form = CompraForm(request.POST)

        if form.is_valid():
            try:
                compra = form.save(commit=False)
                compra.proveedor = proveedor
                compra.save()
                messages.success(request, f'Compra registrada exitosamente.')
                return redirect('lista_compras')
            except Exception as e:
                messages.error(request, f'Error al registrar la compra: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = CompraForm()

    # Estadísticas
    total_gastado = sum(
        (c.cantidad * c.precio_unitario) for c in Compra.objects.all()
        if c.precio_unitario
    ) or 0

    from django.utils import timezone
    from datetime import timedelta
    ahora = timezone.now()
    inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    compras_mes = Compra.objects.filter(fecha_registro__gte=inicio_mes)
    count_mes = compras_mes.count()
    total_mes = sum(
        (c.cantidad * c.precio_unitario) for c in compras_mes
        if c.precio_unitario
    ) or 0

    # Producto top
    from django.db.models import Sum, Count
    from django.db.models.functions import TruncMonth
    producto_top = Compra.objects.values('producto__nombre').annotate(
        total_und=Sum('cantidad')
    ).order_by('-total_und').first()

    # ====== DATOS PARA GRÁFICOS ======
    hoy = timezone.now()
    desde = hoy - timedelta(days=365)

    # Compras por mes (últimos 12 meses)
    compras_por_mes = (
        Compra.objects
        .filter(fecha_registro__gte=desde)
        .annotate(mes=TruncMonth('fecha_registro'))
        .values('mes')
        .annotate(total=Count('id'))
        .order_by('mes')
    )

    meses_labels = []
    meses_data = []
    meses_nombres = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

    # Crear diccionario con datos por mes
    datos_por_mes = {}
    for item in compras_por_mes:
        if item['mes']:
            mes_num = item['mes'].month
            datos_por_mes[mes_num] = item['total']

    # Generar últimos 12 meses en orden cronológico
    from datetime import date
    mes_actual = hoy.month
    año_actual = hoy.year

    for i in range(12):
        mes = (mes_actual - (11 - i) - 1) % 12 + 1
        meses_labels.append(meses_nombres[mes - 1])
        meses_data.append(datos_por_mes.get(mes, 0))

    # Productos más comprados (top 5)
    productos_top_list = (
        Compra.objects
        .values('producto__nombre')
        .annotate(cantidad=Sum('cantidad'))
        .order_by('-cantidad')[:5]
    )

    productos_labels = [p['producto__nombre'] for p in productos_top_list]
    productos_data = [p['cantidad'] for p in productos_top_list]

    # Gastos por proveedor
    gastos_proveedor_dict = {}
    for c in Compra.objects.select_related('proveedor'):
        total = (c.cantidad * c.precio_unitario) if c.precio_unitario else 0
        nombre = c.proveedor.nombre_empresa
        if nombre not in gastos_proveedor_dict:
            gastos_proveedor_dict[nombre] = 0
        gastos_proveedor_dict[nombre] += total

    # Ordenar y tomar top 5
    gastos_ordenados = sorted(gastos_proveedor_dict.items(), key=lambda x: x[1], reverse=True)[:5]
    gastos_labels = [item[0] for item in gastos_ordenados]
    gastos_data = [int(item[1]) for item in gastos_ordenados]

    # Calcular porcentajes para el gráfico de pastel
    gastos_total = sum(gastos_data) if gastos_data else 1
    gastos_porcentajes = [int((gasto / gastos_total * 100)) for gasto in gastos_data] if gastos_data else []

    context = {
        'compras': compras,
        'proveedor': proveedor,
        'todos_proveedores': todos_proveedores,
        'form': form,
        'subtotal': subtotal,
        'total_gastado': total_gastado,
        'count_mes': count_mes,
        'total_mes': total_mes,
        'producto_top': producto_top,
        # Datos para gráficos
        'meses_labels_json': json.dumps(meses_labels),
        'meses_data_json': json.dumps(meses_data),
        'productos_labels_json': json.dumps(productos_labels),
        'productos_data_json': json.dumps(productos_data),
        'gastos_labels_json': json.dumps(gastos_labels),
        'gastos_data_json': json.dumps(gastos_data),
        'gastos_porcentajes_json': json.dumps(gastos_porcentajes),
    }
    return render(request, 'proveedores/compras.html', context)

@login_required
def registrar_compra(request):
    """Vista para registrar compras a proveedores"""
    todos_proveedores = Proveedor.objects.all().order_by('nombre_empresa')
    proveedor = None
    form = None

    # Obtener proveedor de sesión o parámetro GET
    if request.method == 'POST':
        proveedor_id = request.POST.get('proveedor_id') or request.session.get('proveedor_id')
    else:
        proveedor_id = request.GET.get('proveedor') or request.session.get('proveedor_id')

    # Guardar proveedor en sesión
    if proveedor_id:
        try:
            request.session['proveedor_id'] = int(proveedor_id)
            proveedor = Proveedor.objects.get(id=request.session['proveedor_id'])
        except (Proveedor.DoesNotExist, ValueError):
            proveedor = None
    else:
        primer_proveedor = todos_proveedores.first()
        if primer_proveedor:
            request.session['proveedor_id'] = primer_proveedor.id
            proveedor = primer_proveedor

    compras = []
    if proveedor:
        compras = Compra.objects.filter(proveedor=proveedor).order_by('-fecha_registro')

    # Calcular subtotal
    subtotal = sum(
        (c.cantidad * c.precio_unitario) for c in compras
        if c.precio_unitario
    ) or 0

    # Registrar nueva compra
    if request.method == 'POST':
        if not proveedor:
            messages.error(request, 'Por favor selecciona un proveedor.')
            return redirect('registrar_compra')

        form = CompraForm(request.POST)

        if form.is_valid():
            try:
                compra = form.save(commit=False)
                compra.proveedor = proveedor
                compra.save()

                # Actualizar cantidad disponible del producto
                producto = compra.producto
                producto.cantidad_disponible += compra.cantidad
                producto.save()

                # Crear registro en inventario solo si hay lote
                if compra.lote:
                    from inventario.models import Inventario

                    # Obtener la presentación del lote
                    presentacion = compra.lote.presentacion
                    presentacion.cantidad += compra.cantidad
                    presentacion.save()

                    # Crear movimiento de inventario
                    Inventario.objects.create(
                        presentacion=presentacion,
                        lote=compra.lote,
                        registrado_por=request.user,
                        tipo='entrada',
                        cantidad=compra.cantidad,
                        motivo=f'Compra a proveedor: {proveedor.nombre_empresa}',
                    )

                messages.success(
                    request,
                    f'✅ {compra.cantidad} unidades de "{producto.nombre}" ingresadas correctamente.'
                )
                return redirect('registrar_compra')

            except Exception as e:
                messages.error(request, f'Error al registrar la compra: {str(e)}')
        else:
            # Mostrar errores del formulario
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = CompraForm()

    # Obtener datos para estadísticas
    hoy = timezone.now()
    total_gastado = sum(
        c.cantidad * c.precio_unitario
        for c in Compra.objects.exclude(precio_unitario__isnull=True)
    ) or 0

    compras_mes = Compra.objects.filter(
        fecha_registro__year=hoy.year,
        fecha_registro__month=hoy.month,
    )
    count_mes = compras_mes.count()
    total_mes = sum(
        c.cantidad * c.precio_unitario
        for c in compras_mes.exclude(precio_unitario__isnull=True)
    ) or 0

    # Producto más comprado
    producto_top = (
        Compra.objects
        .values('producto__nombre', 'producto__id')
        .annotate(total_und=Sum('cantidad'))
        .order_by('-total_und')
        .first()
    )

    # ====== DATOS PARA GRÁFICOS ======

    # 1. Compras por mes (últimos 12 meses)
    desde = hoy - timedelta(days=365)
    compras_por_mes = (
        Compra.objects
        .filter(fecha_registro__gte=desde)
        .annotate(mes=TruncMonth('fecha_registro'))
        .values('mes')
        .annotate(total=Count('id'))
        .order_by('mes')
    )

    meses_labels = []
    meses_data = []
    meses_nombres = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

    for item in compras_por_mes:
        if item['mes']:
            mes_num = item['mes'].month - 1
            meses_labels.append(meses_nombres[mes_num])
            meses_data.append(item['total'])

    # 2. Productos más comprados (top 5)
    productos_top = (
        Compra.objects
        .values('producto__nombre')
        .annotate(cantidad=Sum('cantidad'))
        .order_by('-cantidad')[:5]
    )

    productos_labels = [p['producto__nombre'] for p in productos_top]
    productos_data = [p['cantidad'] for p in productos_top]

    # 3. Gastos por proveedor
    gastos_proveedor = (
        Compra.objects
        .values('proveedor__nombre_empresa')
        .annotate(
            gasto=Sum('cantidad', output_field=models.IntegerField()) *
                   Sum('precio_unitario', output_field=models.DecimalField())
        )
        .order_by('-gasto')[:5]
    )

    # Calcular gastos totales por proveedor correctamente
    gastos_proveedor_dict = {}
    for c in Compra.objects.select_related('proveedor'):
        total = (c.cantidad * c.precio_unitario) if c.precio_unitario else 0
        nombre = c.proveedor.nombre_empresa
        if nombre not in gastos_proveedor_dict:
            gastos_proveedor_dict[nombre] = 0
        gastos_proveedor_dict[nombre] += total

    # Ordenar y tomar top 5
    gastos_ordenados = sorted(gastos_proveedor_dict.items(), key=lambda x: x[1], reverse=True)[:5]
    gastos_labels = [item[0] for item in gastos_ordenados]
    gastos_data = [int(item[1]) for item in gastos_ordenados]

    # Calcular porcentajes para el gráfico de pastel
    gastos_total = sum(gastos_data) if gastos_data else 1
    gastos_porcentajes = [int((gasto / gastos_total * 100)) for gasto in gastos_data] if gastos_data else []

    productos = Producto.objects.all()
    lotes = Lote.objects.select_related('presentacion').all()

    # ====== CONTEXTO PARA EL TEMPLATE ======
    context = {
        # --- INFORMACIÓN GENERAL ---
        'proveedor': proveedor,
        'todos_proveedores': todos_proveedores,
        'form': form,

        # --- PRODUCTOS Y LOTES ---
        'productos': productos,
        'lotes': lotes,

        # --- COMPRAS Y HISTORIAL ---
        'compras': compras,
        'subtotal_compras': subtotal,

        # --- ESTADÍSTICAS KPI ---
        'total_gastado': total_gastado,              # Total gasto histórico
        'count_mes': count_mes,                      # Cantidad de compras este mes
        'total_mes': total_mes,                      # Total gasto este mes
        'producto_top': producto_top,                # Producto más comprado

        # --- DATOS PARA GRÁFICOS (JSON) ---
        'meses_labels_json': json.dumps(meses_labels),          # Meses (últimos 12)
        'meses_data_json': json.dumps(meses_data),              # Cantidad de compras por mes
        'productos_labels_json': json.dumps(productos_labels),  # Top 5 productos
        'productos_data_json': json.dumps(productos_data),      # Cantidad comprada por producto
        'gastos_labels_json': json.dumps(gastos_labels),        # Top 5 proveedores
        'gastos_data_json': json.dumps(gastos_data),            # Monto gasto por proveedor
        'gastos_porcentajes_json': json.dumps(gastos_porcentajes),  # Porcentaje de gasto
    }

    return render(request, 'proveedores/compras.html', context)


# ════════════════════════════════════════════════════════════════════════════
# VISTAS PARA ÓRDENES DE COMPRA (US-010, US-011, US-012)
# ════════════════════════════════════════════════════════════════════════════

@login_required
def listar_ordenes(request):
    """US-010: Listar órdenes de compra con filtros."""
    from django.db.models import Prefetch

    ordenes = OrdenCompra.objects.all().select_related('proveedor', 'registrado_por').prefetch_related('detalles__presentacion__producto')

    # Filtros
    q = request.GET.get('q', '')
    estado = request.GET.get('estado', '')
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')

    if q:
        ordenes = ordenes.filter(
            proveedor__nombre_empresa__icontains=q
        ) | ordenes.filter(id__icontains=q)

    if estado:
        ordenes = ordenes.filter(estado=estado)

    if fecha_inicio:
        ordenes = ordenes.filter(fecha__date__gte=fecha_inicio)
    if fecha_fin:
        ordenes = ordenes.filter(fecha__date__lte=fecha_fin)

    # Ordenar por fecha descendente
    ordenes = ordenes.order_by('-fecha')

    # Estadísticas generales
    total_ordenes = OrdenCompra.objects.count()
    ordenes_pendientes = OrdenCompra.objects.filter(estado='pendiente').count()
    ordenes_confirmadas = OrdenCompra.objects.filter(estado='confirmada').count()
    ordenes_recibidas = OrdenCompra.objects.filter(estado='recibida').count()

    # Formulario para el modal
    form = OrdenCompraForm()
    form_detalle = DetalleCompraForm()

    # Verificar si hay que mostrar detalle de una orden
    mostrar_orden_id = request.GET.get('mostrar_orden')
    orden_detalle = None
    if mostrar_orden_id:
        try:
            orden_detalle = OrdenCompra.objects.select_related('proveedor', 'registrado_por').prefetch_related('detalles__presentacion__producto').get(id=mostrar_orden_id)
        except OrdenCompra.DoesNotExist:
            orden_detalle = None

    context = {
        'ordenes': ordenes,
        'ordenes_count': ordenes.count(),
        'total_ordenes': total_ordenes,
        'ordenes_pendientes': ordenes_pendientes,
        'ordenes_confirmadas': ordenes_confirmadas,
        'ordenes_recibidas': ordenes_recibidas,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'form': form,
        'form_detalle': form_detalle,
        'orden_detalle': orden_detalle,
    }

    return render(request, 'proveedores/orden_compra.html', context)


@login_required
def crear_orden(request):
    """US-010: Crear nueva orden de compra con opción de agregar primer producto."""
    if request.method == 'POST':
        form = OrdenCompraForm(request.POST)

        if form.is_valid():
            orden = form.save(commit=False)
            orden.registrado_por = request.user
            orden.save()

            # Intentar agregar primer detalle si se proporciona
            presentacion_id = request.POST.get('presentacion')
            cantidad = request.POST.get('cantidad')
            precio = request.POST.get('precio_unitario')

            if presentacion_id and cantidad and precio:
                try:
                    from productos.models import PresentacionProducto
                    presentacion = PresentacionProducto.objects.get(id=presentacion_id)

                    DetalleCompra.objects.create(
                        orden_compra=orden,
                        presentacion=presentacion,
                        cantidad=int(cantidad),
                        precio_unitario=float(precio)
                    )

                    # Recalcular total
                    orden.calcular_total()

                    messages.success(
                        request,
                        f'Orden #{orden.id} creada con 1 producto agregado'
                    )
                except Exception as e:
                    messages.warning(
                        request,
                        f'Orden #{orden.id} creada, pero hubo error al agregar el producto: {str(e)}'
                    )
            else:
                messages.success(
                    request,
                    f'Orden #{orden.id} creada exitosamente para {orden.proveedor.nombre_empresa}'
                )

            return redirect('detalle_orden', pk=orden.id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
            return redirect('listar_ordenes')

    else:
        form = OrdenCompraForm()

    from productos.models import PresentacionProducto
    form_detalle = DetalleCompraForm()

    context = {
        'form': form,
        'form_detalle': form_detalle
    }
    return render(request, 'proveedores/nueva_orden.html', context)


@login_required
def detalle_orden(request, pk):
    """Redirigir al listado de órdenes con el modal abierto."""
    # Verificar que la orden existe
    get_object_or_404(OrdenCompra, pk=pk)
    # Redirigir al listado con parámetro para abrir el modal
    return redirect(f'{reverse("listar_ordenes")}?mostrar_orden={pk}')


@login_required
def agregar_detalle_orden(request, pk):
    """Agregar un detalle (línea) a una orden existente."""
    orden = get_object_or_404(OrdenCompra, pk=pk)

    # No permitir agregar detalles si la orden ya fue recibida
    if orden.estado == 'recibida':
        messages.error(request, 'No se pueden agregar detalles a una orden recibida.')
        return redirect('detalle_orden', pk=pk)

    if request.method == 'POST':
        form = DetalleCompraForm(request.POST)
        if form.is_valid():
            detalle = form.save(commit=False)
            detalle.orden_compra = orden
            detalle.save()

            # Recalcular total
            orden.calcular_total()

            messages.success(request, 'Detalle agregado exitosamente.')
            return redirect('listar_ordenes')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
            return redirect('listar_ordenes')

    return redirect('listar_ordenes')


@login_required
def cambiar_estado_orden(request, pk):
    """US-011: Cambiar estado de una orden (pendiente → confirmada → recibida)."""
    orden = get_object_or_404(OrdenCompra, pk=pk)

    if request.method == 'POST':
        nuevo_estado = request.POST.get('nuevo_estado')

        # Validar transición de estados
        transiciones_validas = {
            'pendiente': ['confirmada', 'cancelada'],
            'confirmada': ['recibida', 'cancelada'],
            'recibida': [],
            'cancelada': [],
        }

        if nuevo_estado not in transiciones_validas.get(orden.estado, []):
            messages.error(request, f'No se puede cambiar de {orden.estado} a {nuevo_estado}.')
            return redirect('listar_ordenes')

        orden_anterior = orden.estado
        orden.estado = nuevo_estado
        orden.save()

        messages.success(
            request,
            f'Estado de orden #{orden.id} cambió de {orden_anterior} a {nuevo_estado}'
        )

        return redirect('listar_ordenes')

    return redirect('listar_ordenes')


@login_required
def recibir_compra(request, pk):
    """US-012: Recibir una orden y crear automáticamente los lotes."""
    from django.db import transaction
    from inventario.models import Lote

    orden = get_object_or_404(OrdenCompra, pk=pk)

    # Validar que la orden esté en estado confirmada
    if orden.estado != 'confirmada':
        messages.error(request, 'Solo se pueden recibir órdenes en estado "confirmada".')
        return redirect('listar_ordenes')

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Cambiar estado a recibida
                orden.estado = 'recibida'
                orden.save()

                # Crear lotes automáticamente para cada detalle
                lotes_creados = 0
                for detalle in orden.detalles.all():
                    numero_lote = f"LOT-{orden.id}-{detalle.id}-{timezone.now().strftime('%Y%m%d')}"

                    lote = Lote.objects.create(
                        numero_lote=numero_lote,
                        presentacion=detalle.presentacion,
                        stock_actual=detalle.cantidad,
                        costo_unitario=detalle.precio_unitario,
                        fecha_vencimiento=None,
                        registrado_por=request.user,
                        detalle_compra=detalle,
                    )

                    lotes_creados += 1

                messages.success(
                    request,
                    f'Orden #{orden.id} recibida correctamente. {lotes_creados} lote(s) creado(s).'
                )

        except Exception as e:
            messages.error(request, f'Error al recibir la orden: {str(e)}')

        return redirect('listar_ordenes')

    return redirect('listar_ordenes')


@login_required
def cambiar_estado_orden_rapido(request, pk):
    """Cambiar estado de orden desde la tabla (sin página separada)."""
    orden = get_object_or_404(OrdenCompra, pk=pk)

    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')

        # Validar transición de estados
        transiciones_validas = {
            'pendiente': ['confirmada', 'cancelada'],
            'confirmada': ['recibida', 'cancelada'],
            'recibida': [],
            'cancelada': [],
        }

        if nuevo_estado in transiciones_validas.get(orden.estado, []):
            orden_anterior = orden.estado
            orden.estado = nuevo_estado
            orden.save()

            messages.success(
                request,
                f'Estado de orden #{orden.id} cambió de {orden_anterior} a {nuevo_estado}'
            )
        else:
            messages.error(request, f'No se puede cambiar de {orden.estado} a {nuevo_estado}.')

    # Redirige a la lista de órdenes (o a la página anterior)
    return redirect('listar_ordenes')


@login_required
def api_orden_detalles(request, orden_id):
    """API: Retorna los detalles de una orden en JSON."""
    from django.http import JsonResponse

    try:
        orden = OrdenCompra.objects.get(id=orden_id)
        detalles_data = []

        for detalle in orden.detalles.all():
            detalles_data.append({
                'id': detalle.id,
                'presentacion': detalle.presentacion.nombre,
                'cantidad': detalle.cantidad,
                'precio_unitario': f"{detalle.precio_unitario:.2f}",
                'subtotal': f"{detalle.subtotal:.2f}"
            })

        return JsonResponse({'detalles': detalles_data})
    except OrdenCompra.DoesNotExist:
        return JsonResponse({'error': 'Orden no encontrada'}, status=404)


# ════════════════════════════════════════════════════════════════════════════
# VISTAS PARA MODALES: NOTAS, EDITAR, HISTORIAL
# ════════════════════════════════════════════════════════════════════════════

@login_required
def guardar_nota_orden(request, pk):
    """Guardar notas internas en una orden."""
    if request.method == 'POST':
        try:
            orden = OrdenCompra.objects.get(id=pk)
            nota = request.POST.get('notas', '').strip()

            orden.notas = nota
            orden.save()

            # Registrar en historial
            HistorialOrden.objects.create(
                orden=orden,
                evento='nota_agregada',
                usuario=request.user,
                descripcion=f"Nota actualizada: {nota[:50]}{'...' if len(nota) > 50 else ''}"
            )

            messages.success(request, '✅ Nota guardada correctamente')
        except OrdenCompra.DoesNotExist:
            messages.error(request, '❌ Orden no encontrada')
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')

    return redirect(f'{reverse("listar_ordenes")}?mostrar_orden={pk}')


@login_required
def obtener_historial_orden(request, pk):
    """Obtener historial de cambios de una orden."""
    from django.http import JsonResponse

    try:
        orden = OrdenCompra.objects.get(id=pk)
        historial = orden.historial.all()

        eventos = []

        # Evento: Creación (siempre incluir)
        eventos.append({
            'evento': 'Orden Creada',
            'usuario': orden.registrado_por.get_full_name() if orden.registrado_por else 'Sistema',
            'fecha': orden.fecha.strftime('%d/%m/%Y %H:%M'),
            'descripcion': 'Orden creada en el sistema',
            'color': '#9b5de5'
        })

        # Eventos adicionales del historial
        for h in historial:
            eventos.append({
                'evento': h.get_evento_display(),
                'usuario': h.usuario.get_full_name() if h.usuario else 'Sistema',
                'fecha': h.fecha.strftime('%d/%m/%Y %H:%M'),
                'descripcion': h.descripcion,
                'color': {
                    'creada': '#9b5de5',
                    'confirmada': '#4DA8DA',
                    'recibida': '#27ae60',
                    'cancelada': '#e74c3c',
                    'nota_agregada': '#f39c12',
                    'editada': '#4DA8DA',
                }.get(h.evento, '#8FA3B1')
            })

        return JsonResponse({'status': 'ok', 'historial': eventos})
    except OrdenCompra.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Orden no encontrada'}, status=404)


@login_required
def editar_detalle_orden(request, detalle_id):
    """Editar cantidad y precio de un detalle de orden."""
    from django.http import JsonResponse

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)

    try:
        detalle = DetalleCompra.objects.get(id=detalle_id)

        # Solo si la orden está en pendiente
        if detalle.orden_compra.estado != 'pendiente':
            return JsonResponse({
                'status': 'error',
                'message': 'No se puede editar orden que no está pendiente'
            }, status=400)

        # Actualizar detalle
        detalle.cantidad = int(request.POST.get('cantidad'))
        detalle.precio_unitario = float(request.POST.get('precio_unitario'))
        detalle.save()

        # Recalcular total de la orden
        detalle.orden_compra.calcular_total()

        # Registrar en historial
        HistorialOrden.objects.create(
            orden=detalle.orden_compra,
            evento='editada',
            usuario=request.user,
            descripcion=f"Editada línea: {detalle.presentacion.nombre}"
        )

        return JsonResponse({
            'status': 'ok',
            'subtotal': f"{detalle.subtotal:.2f}",
            'total_orden': f"{detalle.orden_compra.total:.2f}"
        })
    except DetalleCompra.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Detalle no encontrado'}, status=404)
    except ValueError:
        return JsonResponse({'status': 'error', 'message': 'Datos inválidos'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
def guardar_pago_compra(request, compra_id):
    """Guardar información de pago en una compra legacy."""
    from django.http import JsonResponse
    from django.utils.dateparse import parse_datetime

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)

    try:
        compra = Compra.objects.get(id=compra_id)

        compra.numero_factura = request.POST.get('numero_factura', '').strip()
        compra.metodo_pago = request.POST.get('metodo_pago')
        compra.estado_pago = request.POST.get('estado_pago')
        compra.monto_pagado = float(request.POST.get('monto_pagado', 0))

        fecha_pago = request.POST.get('fecha_pago')
        if fecha_pago:
            compra.fecha_pago = parse_datetime(fecha_pago)

        compra.save()

        return JsonResponse({'status': 'ok', 'message': 'Pago registrado correctamente'})
    except Compra.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Compra no encontrada'}, status=404)
    except ValueError:
        return JsonResponse({'status': 'error', 'message': 'Datos inválidos'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
