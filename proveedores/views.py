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
from .models import Proveedor, Compra, DetalleCompra, HistorialCompra
from .forms import ProveedorForm, CompraForm, DetalleCompraForm, NuevaCompraForm
from productos.models import Producto
from inventario.models import Lote, Inventario
import json
from django.db.models.functions import TruncMonth

@login_required
def lista_proveedores(request):
    from django.db.models import Sum, F, DecimalField, Case, When, Value

    proveedores = Proveedor.objects.all()

    # Calcular total de compras manualmente para cada proveedor
    for proveedor in proveedores:
        try:
            compras = Compra.objects.filter(proveedor=proveedor)
            total = sum(
                (c.cantidad * c.precio_unitario if c.precio_unitario else 0)
                for c in compras
            ) or 0
            proveedor.total_compras = total
            proveedor.total_ordenes = compras.count()
        except Exception:
            proveedor.total_compras = 0
            proveedor.total_ordenes = 0

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

    # Obtener máximo de compras para normalizar barras
    max_compras = max([p.total_compras for p in proveedores], default=1)
    if max_compras == 0:
        max_compras = 1

    # Calcular porcentaje de ancho para cada proveedor
    for proveedor in proveedores:
        if proveedor.total_compras > 0:
            proveedor.bar_width = int((proveedor.total_compras / max_compras) * 100)
        else:
            proveedor.bar_width = 1

    # Paginación
    paginator = Paginator(proveedores, 10)  # 10 proveedores por página
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Calcular gastos por proveedor para la gráfica - usar raw SQL para evitar Decimal
    gastos_proveedor_dict = {}
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT p.nombre_empresa, SUM(c.cantidad) as total
                FROM proveedores_compra c
                JOIN proveedores_proveedor p ON c.proveedor_id = p.id
                GROUP BY p.id, p.nombre_empresa
                ORDER BY total DESC
            """)
            for nombre, total in cursor.fetchall():
                gastos_proveedor_dict[nombre] = total or 0
    except Exception:
        gastos_proveedor_dict = {}

    # Ordenar y tomar top 5
    gastos_ordenados = sorted(gastos_proveedor_dict.items(), key=lambda x: x[1], reverse=True)[:5]
    gastos_labels = [item[0] for item in gastos_ordenados]
    gastos_data = [int(item[1]) for item in gastos_ordenados]

    # Calcular porcentajes para el gráfico de pastel
    gastos_total = sum(gastos_data) if gastos_data else 0
    if gastos_total == 0:
        gastos_total = 1
    gastos_porcentajes = [int((gasto / gastos_total * 100)) for gasto in gastos_data] if gastos_data else []

    context = {
        'proveedores': proveedores,
        'page_obj': page_obj,
        'paginator': paginator,
        'total_proveedores': total_proveedores,
        'proveedores_activos': proveedores_activos,
        'proveedores_inactivos': proveedores_inactivos,
        'proveedores_sancionados': proveedores_sancionados,
        'porcentaje_activos': porcentaje_activos,
        'max_compras': max_compras,
        'gastos_labels_json': json.dumps(gastos_labels),
        'gastos_data_json': json.dumps(gastos_data),
        'gastos_porcentajes_json': json.dumps(gastos_porcentajes),
        'breadcrumb_items': [
            {'nombre': 'Proveedores', 'url': None},
        ],
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
        'breadcrumb_items': [
            {'nombre': 'Proveedores', 'url': reverse('lista_proveedores')},
            {'nombre': f'Editar: {proveedor.nombre_empresa}', 'url': None},
        ],
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
        'proveedor': proveedor,
        'breadcrumb_items': [
            {'nombre': 'Proveedores', 'url': reverse('lista_proveedores')},
            {'nombre': proveedor.nombre_empresa, 'url': None},
        ],
        
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

    # Obtener compras de forma simple
    compras = []
    compras_count = 0
    subtotal = 0

    if proveedor:
        compras = []
        compras_count = 0
        subtotal = 0

        try:
            from django.db import connection
            with connection.cursor() as cursor:
                # Ver TODAS las compras (sin filtro) para diagnosticar
                cursor.execute("""
                    SELECT c.id, c.producto_id, c.cantidad, CAST(c.precio_unitario AS REAL),
                           CAST(c.total AS REAL), c.fecha, c.estado, c.estado_pago, c.recibida,
                           p.nombre, c.proveedor_id
                    FROM proveedores_compra c
                    LEFT JOIN productos_producto p ON c.producto_id = p.id
                    ORDER BY c.fecha DESC
                """)

                rows = cursor.fetchall()
                print(f"DEBUG: TOTAL Filas en BD: {len(rows)}")
                print(f"DEBUG: Proveedor actual: {proveedor.id}")

                for row in rows:
                    prov_id_row = row[10]  # proveedor_id from query
                    print(f"DEBUG: Compra ID:{row[0]}, Proveedor:{prov_id_row}, Producto:{row[9]}")

                    # Filtrar solo compras del proveedor actual
                    if prov_id_row == proveedor.id:
                        class C:
                            pass
                        c = C()
                        c.id = row[0]
                        c.producto_id = row[1]
                        c.cantidad = row[2]
                        c.precio_unitario = float(row[3] or 0)
                        c.total = float(row[4] or 0)
                        c.fecha = row[5]
                        c.estado = row[6]
                        c.estado_pago = row[7]
                        c.recibida = row[8]

                        class P:
                            pass
                        c.producto = P()
                        c.producto.nombre = row[9] or f"Producto {row[1]}"

                        compras.append(c)
                        print(f"DEBUG: ✓ Compra AÑADIDA - ID: {c.id}")

                compras_count = len(compras)
                subtotal = sum(float(c.precio_unitario or 0) * c.cantidad for c in compras) or 0
                print(f"DEBUG: TOTAL compras para este proveedor: {compras_count}, Subtotal: {subtotal}")

        except Exception as e:
            print(f"ERROR en lista_compras: {e}")
            import traceback
            traceback.print_exc()
            compras = []
            compras_count = 0
            subtotal = 0

    # Registrar nueva compra
    if request.method == 'POST':
        if not proveedor:
            messages.error(request, 'Por favor selecciona un proveedor.')
            return redirect('lista_compras')

        form = NuevaCompraForm(request.POST)
        print(f"DEBUG: Form válido: {form.is_valid()}, Proveedor: {proveedor.id if proveedor else 'None'}")
        if not form.is_valid():
            print(f"DEBUG: Errores del formulario: {form.errors}")

        if form.is_valid():
            try:
                from inventario.models import Inventario, Lote
                from productos.models import PresentacionProducto

                if not proveedor:
                    print(f"DEBUG: ERROR - Proveedor es None!")
                    messages.error(request, 'Error: Proveedor no válido.')
                    return redirect('lista_compras')

                # Extraer datos del formulario
                producto = form.cleaned_data['producto']
                cantidad = form.cleaned_data['cantidad']
                precio_unitario = form.cleaned_data['precio_unitario']
                lote_obj = form.cleaned_data.get('lote')

                total_compra = cantidad * precio_unitario

                # Crear la compra
                compra = Compra.objects.create(
                    proveedor=proveedor,
                    valor=total_compra,
                    saldo=total_compra,
                    documento_usuario=request.user
                )
                print(f"DEBUG: Compra guardada exitosamente - ID: {compra.id}, Proveedor: {proveedor.nombre_empresa}")

                # Registrar en historial de compras
                try:
                    from .models import HistorialCompra
                    HistorialCompra.objects.create(
                        compra=compra,
                        evento='creada',
                        usuario=request.user,
                        descripcion=f'Compra registrada: {cantidad} x {producto.nombre}'
                    )
                    print(f"DEBUG: Historial creado para compra {compra.id}")
                except Exception as e:
                    print(f"DEBUG: Error creando historial: {e}")
                    import traceback
                    traceback.print_exc()

                # Usar lote existente o crear uno nuevo
                if not lote_obj:
                    presentacion = producto.presentaciones.first()

                    # Si no hay presentación, crear una automáticamente
                    if not presentacion:
                        presentacion = PresentacionProducto.objects.create(
                            producto=producto,
                            nombre=f"{producto.nombre} - Presentación Estándar",
                            cantidad=0,
                            unidad_medida="unidades"
                        )

                    import uuid
                    lote_numero = f"LOTE-{uuid.uuid4().hex[:8].upper()}"
                    lote_obj = Lote.objects.create(
                        numero_lote=lote_numero,
                        presentacion=presentacion,
                        stock_actual=cantidad,
                        costo_unitario=precio_unitario,
                        registrado_por=request.user
                    )
                else:
                    # Actualizar lote existente
                    lote_obj.stock_actual += cantidad
                    lote_obj.save()

                # Crear el detalle de compra
                DetalleCompra.objects.create(
                    compra=compra,
                    producto=producto,
                    presentacion=lote_obj.presentacion,
                    cantidad=cantidad,
                    precio_unitario=precio_unitario
                )

                # Actualizar cantidad disponible del producto
                producto.cantidad_disponible += cantidad
                producto.save()

                # Obtener la presentación del lote
                presentacion = lote_obj.presentacion
                presentacion.cantidad += cantidad
                presentacion.save()

                # Crear movimiento de inventario (entrada)
                Inventario.objects.create(
                    presentacion=presentacion,
                    lote=lote_obj,
                    registrado_por=request.user,
                    tipo='entrada',
                    cantidad=cantidad,
                    motivo=f'Compra a proveedor: {proveedor.nombre_empresa}',
                )

                messages.success(request, f'✅ {cantidad} unidades de "{producto.nombre}" ingresadas a inventario correctamente.')
                return redirect('lista_compras')
            except Exception as e:
                print(f"DEBUG: Error guardando compra: {e}")
                import traceback
                traceback.print_exc()
                messages.error(request, f'Error al registrar la compra: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = NuevaCompraForm()

    # Estadísticas - Calcular gasto de esta semana (últimos 7 días)
    hoy = timezone.now()
    hace_7_dias = hoy - timedelta(days=7)

    try:
        # Usar exclude para evitar errores de Decimal NULL
        compras_semana_qs = Compra.objects.filter(fecha__gte=hace_7_dias).exclude(valor__isnull=True)
        total_gastado = float(sum(c.valor for c in compras_semana_qs) or 0)
    except Exception:
        total_gastado = 0

    # Compras este mes
    count_mes = Compra.objects.filter(
        fecha__year=hoy.year,
        fecha__month=hoy.month,
    ).count()

    try:
        compras_mes_qs = Compra.objects.filter(
            fecha__year=hoy.year,
            fecha__month=hoy.month,
        ).exclude(valor__isnull=True)
        total_mes = float(sum(c.valor for c in compras_mes_qs) or 0)
    except Exception:
        total_mes = 0

    # Producto top - filtrado por proveedor seleccionado
    try:
        if proveedor:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT p.nombre, SUM(c.cantidad) as total
                    FROM proveedores_compra c
                    LEFT JOIN productos_producto p ON c.producto_id = p.id
                    WHERE c.proveedor_id = %s
                    GROUP BY COALESCE(p.id, -1), COALESCE(p.nombre, 'Sin producto')
                    ORDER BY total DESC
                    LIMIT 1
                """, [proveedor.id])
                row = cursor.fetchone()
                if row:
                    producto_top = {'producto__nombre': row[0], 'total_und': row[1]}
                else:
                    producto_top = None
        else:
            producto_top = None
    except Exception:
        producto_top = None

    # ====== DATOS PARA GRÁFICOS ======
    hoy = timezone.now()
    desde = hoy - timedelta(days=365)

    # Compras por mes (últimos 12 meses)
    compras_por_mes = (
        Compra.objects
        .filter(fecha__gte=desde)
        .annotate(mes=TruncMonth('fecha'))
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
    mes_actual = hoy.month
    año_actual = hoy.year

    for i in range(12):
        mes = (mes_actual - (11 - i) - 1) % 12 + 1
        meses_labels.append(meses_nombres[mes - 1])
        meses_data.append(datos_por_mes.get(mes, 0))

    # Productos más comprados (top 5)
    # TODO: Reescribir esta lógica para usar DetalleCompra en lugar de Compra
    # ya que los productos ahora están en DetalleCompra, no en Compra
    productos_labels = ['N/A']
    productos_data = [0]

    # Gastos por proveedor
    # TODO: Reescribir para usar nuevo modelo - Compra ya no tiene cantidad directa
    gastos_proveedor_dict = {}
    try:
        # Usar el modelo ORM en lugar de SQL raw
        for compra in compras:
            nombre = compra.proveedor.nombre_empresa
            gastos_proveedor_dict[nombre] = gastos_proveedor_dict.get(nombre, 0) + float(compra.valor or 0)
    except Exception:
        gastos_proveedor_dict = {}

    # Ordenar y tomar top 5
    gastos_ordenados = sorted(gastos_proveedor_dict.items(), key=lambda x: x[1], reverse=True)[:5]
    gastos_labels = [item[0] for item in gastos_ordenados]
    gastos_data = [int(item[1]) for item in gastos_ordenados]

    # Calcular porcentajes para el gráfico de pastel (evitar división por cero)
    gastos_total = sum(gastos_data) if gastos_data else 0
    if gastos_total == 0:
        gastos_total = 1
    gastos_porcentajes = [int((gasto / gastos_total * 100)) for gasto in gastos_data] if gastos_data else []

    context = {
        'compras': compras,
        'compras_count': compras_count,
        'proveedor': proveedor,
        'todos_proveedores': todos_proveedores,
        'form': form,
        'subtotal_compras': subtotal,
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
        'breadcrumb_items': [
        {'nombre': 'Proveedores', 'url': reverse('lista_proveedores')},
        {'nombre': 'Compras', 'url': None},
],
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
    subtotal = 0

    if proveedor:
        compras = []
        subtotal = 0

        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT c.id, c.producto_id, c.cantidad, c.precio_unitario, c.total,
                           c.fecha, c.estado, c.estado_pago, c.recibida, p.nombre
                    FROM proveedores_compra c
                    LEFT JOIN productos_producto p ON c.producto_id = p.id
                    WHERE c.proveedor_id = ?
                    ORDER BY c.fecha DESC
                """, [proveedor.id])

                for row in cursor.fetchall():
                    class C:
                        pass
                    c = C()
                    c.id = row[0]
                    c.producto_id = row[1]
                    c.cantidad = row[2]
                    c.precio_unitario = float(row[3] or 0)
                    c.total = float(row[4] or 0)
                    c.fecha = row[5]
                    c.estado = row[6]
                    c.estado_pago = row[7]
                    c.recibida = row[8]

                    class P:
                        pass
                    c.producto = P()
                    c.producto.nombre = row[9]

                    compras.append(c)

                subtotal = sum(float(c.precio_unitario or 0) * c.cantidad for c in compras) or 0
        except Exception as e:
            print(f"Error: {e}")
            compras = []
            subtotal = 0

    # Registrar nueva compra
    if request.method == 'POST':
        if not proveedor:
            messages.error(request, 'Por favor selecciona un proveedor.')
            return redirect('registrar_compra')

        form = CompraForm(request.POST)

        if form.is_valid():
            from inventario.models import Inventario, Lote
            from productos.models import PresentacionProducto

            compra = form.save(commit=False)
            compra.proveedor = proveedor
            compra.save()

            # Registrar en historial de compras
            try:
                from .models import HistorialCompra
                producto_nombre = compra.producto.nombre if compra.producto else 'Producto desconocido'
                HistorialCompra.objects.create(
                    compra=compra,
                    evento='creada',
                    usuario=request.user,
                    descripcion=f'Compra registrada: {compra.cantidad} x {producto_nombre}'
                )
            except Exception as e:
                print(f"Error creando historial: {e}")
                import traceback
                traceback.print_exc()

            producto = compra.producto

            # Crear lote automáticamente si no existe
            if not compra.lote:
                presentacion = producto.presentaciones.first()

                # Si no hay presentación, crear una automáticamente
                if not presentacion:
                    presentacion = PresentacionProducto.objects.create(
                        producto=producto,
                        nombre=f"{producto.nombre} - Presentación Estándar",
                        cantidad=0,
                        unidad_medida="unidades"
                    )

                import uuid
                lote_numero = f"LOTE-{uuid.uuid4().hex[:8].upper()}"
                compra.lote = Lote.objects.create(
                    numero_lote=lote_numero,
                    presentacion=presentacion,
                    stock_actual=compra.cantidad,
                    costo_unitario=compra.precio_unitario or 0,
                    registrado_por=request.user
                )
                compra.save()

            # Actualizar cantidad disponible del producto
            producto.cantidad_disponible += compra.cantidad
            producto.save()

            # Obtener la presentación del lote
            presentacion = compra.lote.presentacion
            presentacion.cantidad += compra.cantidad
            presentacion.save()

            # Crear movimiento de inventario (entrada)
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
                f'✅ {compra.cantidad} unidades de "{producto.nombre}" ingresadas a inventario correctamente.'
            )
            return redirect('registrar_compra')
        else:
            # Mostrar errores del formulario
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = NuevaCompraForm()

    # Obtener datos para estadísticas
    hoy = timezone.now()
    # Calcular gasto de esta semana (últimos 7 días)
    hace_7_dias = hoy - timedelta(days=7)
    compras_semana = Compra.objects.filter(fecha__gte=hace_7_dias)
    total_gastado = sum(
        c.cantidad * c.precio_unitario
        for c in compras_semana.exclude(precio_unitario__isnull=True)
    ) or 0

    compras_mes = Compra.objects.filter(
        fecha__year=hoy.year,
        fecha__month=hoy.month,
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
        .filter(fecha__gte=desde)
        .annotate(mes=TruncMonth('fecha'))
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

    # Calcular porcentajes para el gráfico de pastel (evitar división por cero)
    gastos_total = sum(gastos_data) if gastos_data else 0
    if gastos_total == 0:
        gastos_total = 1
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
        'total_gastado': total_gastado,              # Total gasto esta semana
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
        'gastos_porcentajes_json': json.dumps(gastos_porcentajes),
        'breadcrumb_items': [
            {'nombre': 'Proveedores', 'url': reverse('lista_proveedores')},
            {'nombre': 'Compras', 'url': None},
        ],
    }

    return render(request, 'proveedores/compras.html', context)
