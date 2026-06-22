# proveedores/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from .models import Proveedor, Compra
from .forms import ProveedorForm, CompraForm
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

    context = {
        'proveedores': proveedores,
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
    return render(request, 'proveedores/detalle_proveedor.html', {'proveedor': proveedor})

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
    return render(request, 'proveedores/compras.html', {})

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
