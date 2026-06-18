# proveedores/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from .models import Proveedor, Compra
from .forms import ProveedorForm, CompraForm
from productos.models import Producto
from inventario.models import Lote, Inventario

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
    
    porcentaje_activos = int((proveedores_activos / total_proveedores * 100)) if total_proveedores > 0 else 0
    
    return render(request, 'proveedores/proveedores.html', {
        'proveedores': proveedores,
        'total_proveedores': total_proveedores,
        'proveedores_activos': proveedores_activos,
        'proveedores_inactivos': proveedores_inactivos,
        'proveedores_sancionados': proveedores_sancionados,
        'porcentaje_activos': porcentaje_activos,
    })

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

    return render(request, 'proveedores/editar_proveedor.html', {'form': form, 'proveedor': proveedor})

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
        .values('producto__nombre')
        .annotate(total_und=Sum('cantidad'))
        .order_by('-total_und')
        .first()
    )

    productos = Producto.objects.all()
    lotes = Lote.objects.select_related('presentacion').all()

    context = {
        'proveedor': proveedor,
        'todos_proveedores': todos_proveedores,
        'productos': productos,
        'compras': compras,
        'subtotal_compras': subtotal,
        'total_gastado': total_gastado,
        'count_mes': count_mes,
        'total_mes': total_mes,
        'producto_top': producto_top,
        'lotes': lotes,
        'form': form,
    }

    return render(request, 'proveedores/compras.html', context)
