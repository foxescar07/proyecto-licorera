from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Prefetch
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from .models import Producto, Categoria, PresentacionProducto
from inventario.models import Inventario, AgendaInventario
from .forms import ProductoForm, AgendaInventarioForm, PresentacionForm, ProductoRegistroForm


# ===============================
# LISTA / VISTA PRINCIPAL
# ===============================
@login_required
def lista_productos(request):
    productos_qs = Producto.objects.select_related('categoria').prefetch_related('presentaciones__lotes').all()

    categorias = Categoria.objects.filter(padre__isnull=True).prefetch_related(
        Prefetch(
            'productos',
            queryset=Producto.objects.prefetch_related('presentaciones__lotes').select_related('categoria')
        ),
        Prefetch(
            'subcategorias',
            queryset=Categoria.objects.prefetch_related(
                Prefetch(
                    'productos',
                    queryset=Producto.objects.prefetch_related('presentaciones__lotes').select_related('categoria')
                )
            )
        ),
    )

    resumen_categorias = []
    for cat in Categoria.objects.filter(padre__isnull=True):
        total  = Producto.objects.filter(categoria=cat).count()
        total += Producto.objects.filter(categoria__padre=cat).count()
        resumen_categorias.append({'pk': cat.pk, 'nombre': cat.nombre, 'total': total})

    todas_cats     = Categoria.objects.all()
    total_criticos = sum(1 for p in productos_qs if p.stock_critico)
    form           = ProductoRegistroForm()

    return render(request, 'productos/productos.html', {
        'productos':          productos_qs,
        'categorias':         categorias,
        'todas_cats':         todas_cats,
        'resumen_categorias': resumen_categorias,
        'form':               form,
        'total_criticos':     total_criticos,
    })


# ===============================
# CREAR PRODUCTO
# ===============================
@login_required
def crear_producto(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido.'}, status=405)

    is_ajax  = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    next_url = request.POST.get('next') or request.GET.get('next') or 'lista_productos'

    nombre      = request.POST.get('nombre', '').strip()
    codigo      = request.POST.get('codigo', '').strip()
    categoria   = request.POST.get('categoria')
    descripcion = request.POST.get('descripcion', '').strip()

    errores = {}
    if not nombre:
        errores['nombre'] = ['El nombre es obligatorio.']
    if not categoria:
        errores['categoria'] = ['La categoría es obligatoria.']

    if errores:
        if is_ajax:
            return JsonResponse({'ok': False, 'errores': errores}, status=400)
        messages.error(request, 'Corrige los errores del formulario.')
        return redirect('lista_productos')

    producto = Producto.objects.create(
        nombre=nombre,
        codigo=codigo or None,
        categoria_id=categoria,
        descripcion=descripcion,
    )

    if is_ajax:
        return JsonResponse({'ok': True, 'pk': producto.pk, 'nombre': producto.nombre})

    messages.success(request, f'✅ Producto "{producto.nombre}" creado correctamente.')
    return redirect(next_url)


# ===============================
# DETALLE PRODUCTO
# ===============================
@login_required
def producto_detalle(request, pk):
    producto    = get_object_or_404(Producto, pk=pk)
    movimientos = Inventario.objects.filter(presentacion__producto=producto).order_by('-fecha_actualizada')
    return render(request, 'productos/producto_detalle.html', {
        'producto':    producto,
        'movimientos': movimientos,
    })


# ===============================
# EDITAR PRODUCTO
# ===============================
@login_required
def producto_editar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        cambios = []

        nombre       = request.POST.get('nombre', '').strip()
        codigo       = request.POST.get('codigo', '').strip()
        descripcion  = request.POST.get('descripcion', '').strip()
        categoria_pk = request.POST.get('categoria')

        if nombre and nombre != producto.nombre:
            cambios.append(f'📝 Nombre: "{producto.nombre}" → "{nombre}"')
        if nombre:
            producto.nombre = nombre

        if codigo and codigo != producto.codigo:
            cambios.append(f'🔖 Código: {producto.codigo} → {codigo}')
        if codigo:
            producto.codigo = codigo

        if descripcion != (producto.descripcion or ''):
            cambios.append('📄 Descripción actualizada')
        producto.descripcion = descripcion

        if categoria_pk:
            try:
                nueva_cat_id = int(categoria_pk)
                if nueva_cat_id != producto.categoria_id:
                    nueva_cat = Categoria.objects.get(pk=nueva_cat_id)
                    cambios.append(f'🏷️ Categoría: "{producto.categoria.nombre}" → "{nueva_cat.nombre}"')
                producto.categoria_id = nueva_cat_id
            except (ValueError, TypeError, Categoria.DoesNotExist):
                pass

        producto.save()

        # ── Presentaciones existentes ──────────────────────────────────
        for key, valor in request.POST.items():
            if key.startswith('pres_nombre_'):
                pres_id = key.replace('pres_nombre_', '')
                try:
                    pres            = PresentacionProducto.objects.get(pk=int(pres_id), producto=producto)
                    nuevo_nombre    = valor.strip()
                    nuevas_unidades = request.POST.get(f'pres_unidades_{pres_id}', '').strip()
                    nuevo_precio    = request.POST.get(f'pres_precio_{pres_id}', '').strip()

                    if nuevo_nombre and nuevo_nombre != pres.nombre:
                        cambios.append(f'📦 Presentación: "{pres.nombre}" → "{nuevo_nombre}"')
                        pres.nombre = nuevo_nombre

                    if nuevas_unidades:
                        try:
                            nu = max(1, int(nuevas_unidades))
                            if nu != pres.unidades:
                                cambios.append(f'📦 Unidades "{pres.nombre}": {pres.unidades} → {nu}')
                                pres.unidades = nu
                        except (ValueError, TypeError):
                            pass

                    if nuevo_precio:
                        try:
                            np_ = float(nuevo_precio)
                            if np_ != float(pres.precio):
                                cambios.append(f'💲 Precio "{pres.nombre}": ${pres.precio} → ${np_}')
                                pres.precio = np_
                        except (ValueError, TypeError):
                            pass

                    pres.save()

                except PresentacionProducto.DoesNotExist:
                    pass

        # ── Nuevas presentaciones ──────────────────────────────────────
        nuevos_nombres  = request.POST.getlist('nueva_pres_nombre[]')
        nuevas_unidades = request.POST.getlist('nueva_pres_unidades[]')
        nuevos_precios  = request.POST.getlist('nueva_pres_precio[]')

        for i, nombre_pres in enumerate(nuevos_nombres):
            nombre_pres = nombre_pres.strip()
            if not nombre_pres:
                continue

            try:
                unidades_pres = max(1, int(nuevas_unidades[i])) if i < len(nuevas_unidades) else 1
            except (ValueError, TypeError, IndexError):
                unidades_pres = 1

            try:
                precio_pres = float(nuevos_precios[i]) if i < len(nuevos_precios) and nuevos_precios[i].strip() else 0.0
            except (ValueError, TypeError):
                precio_pres = 0.0

            PresentacionProducto.objects.create(
                producto=producto,
                nombre=nombre_pres,
                unidades=unidades_pres,
                precio=precio_pres,
            )
            cambios.append(f'➕ Nueva presentación: "{nombre_pres}" · {unidades_pres} uds')

        if cambios:
            messages.success(request, f"✅ Producto '{producto.nombre}' actualizado.")
        else:
            messages.info(request, 'ℹ️ No se detectaron cambios en el producto.')

    return redirect('lista_productos')


# ===============================
# ELIMINAR PRODUCTO
# ===============================
@login_required
def producto_eliminar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        nombre = producto.nombre
        producto.delete()
        messages.success(request, f'✅ Producto "{nombre}" eliminado correctamente.')
    return redirect('lista_productos')


# ===============================
# PRESENTACIONES
# ===============================
@login_required
def presentaciones_guardar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)

    if request.method == 'POST':
        nombres  = request.POST.getlist('nombre[]')
        unidades = request.POST.getlist('unidades_base[]')
        precios  = request.POST.getlist('precio[]')

        producto.presentaciones.all().delete()

        nuevas = []
        for i in range(len(nombres)):
            nombre_v = nombres[i].strip() if i < len(nombres) else ''
            unidad_v = unidades[i]        if i < len(unidades) else '1'
            precio_v = precios[i]         if i < len(precios)  else '0'

            if not nombre_v:
                continue

            try:
                precio_f = float(precio_v)
            except (ValueError, TypeError):
                precio_f = 0.0

            nuevas.append(PresentacionProducto(
                producto=producto,
                nombre=nombre_v,
                unidades=int(unidad_v),
                precio=precio_f,
            ))

        if nuevas:
            with transaction.atomic():
                PresentacionProducto.objects.bulk_create(nuevas)

        messages.success(request, 'Presentaciones guardadas correctamente.')
        return redirect(request.GET.get('next', 'lista_productos'))

    return redirect('lista_productos')


@login_required
def presentaciones_json(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    data     = list(producto.presentaciones.values('id', 'nombre', 'unidades', 'precio'))
    return JsonResponse({'presentaciones': data, 'producto': producto.nombre})


# ===============================
# REGISTRO PRODUCTO
# ===============================
@login_required
def producto_registro(request):
    form = ProductoRegistroForm()
    if request.method == 'POST':
        form = ProductoRegistroForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Producto registrado correctamente.')
            return redirect('producto_registro')
    return render(request, 'productos/registro.html', {'form': form})


# ===============================
# STOCK STATUS (widget)
# ===============================
@login_required
def stock_status(request):
    productos = Producto.objects.prefetch_related('presentaciones__lotes').all()
    criticos, bajos = [], []

    for p in productos:
        stock_total = p.presentaciones.aggregate(total=Sum('lotes__stock_actual'))['total'] or 0
        if stock_total == 0:
            criticos.append({'nombre': p.nombre, 'cantidad': stock_total})
        elif stock_total <= 10:
            bajos.append({'nombre': p.nombre, 'cantidad': stock_total})

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


# ===============================
# SALIDA DE PRODUCTO
# ===============================
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


# ===============================
# BUSCAR PRODUCTO
# ===============================
@login_required
def buscar_producto(request):
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse({'encontrado': False, 'mensaje': 'Escribe un nombre o código.'})

    producto = (
        Producto.objects.filter(nombre__icontains=q).first() or
        Producto.objects.filter(codigo__icontains=q).first()
    )

    if not producto:
        return JsonResponse({'encontrado': False, 'mensaje': f'No se encontró "{q}".'})

    stock_total = producto.presentaciones.aggregate(
        total=Sum('lotes__stock_actual')
    )['total'] or 0

    return JsonResponse({
        'encontrado': True,
        'producto': {
            'pk':           producto.pk,
            'nombre':       producto.nombre,
            'codigo':       producto.codigo or '—',
            'categoria':    producto.categoria.nombre if producto.categoria else '—',
            'stock_total':  stock_total,
            'descripcion':  producto.descripcion or '',
            'presentaciones': list(
                producto.presentaciones.values('id', 'nombre', 'unidades', 'precio')
            ),
        }
    })


# ===============================
# ROTACIÓN JSON
# ===============================
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
            prod = Producto.objects.prefetch_related('presentaciones').get(
                pk=top['presentacion__producto__pk']
            )
            estrella_nombre        = prod.nombre
            estrella_categoria     = prod.categoria.nombre if prod.categoria else ''
            estrella_vendido       = top['total_vendido']
            estrella_stock         = prod.stock_total
            estrella_stock_critico = prod.stock_critico

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


# ===============================
# GESTIÓN DE CATEGORÍAS
# ===============================
@login_required
def categorias_lista(request):
    categorias = Categoria.objects.prefetch_related(
        'productos', 'subcategorias__productos'
    ).filter(padre__isnull=True)
    todas_cats = Categoria.objects.all()
    return render(request, 'productos/categorias.html', {
        'categorias': categorias,
        'todas_cats': todas_cats,
    })


@login_required
def categoria_crear(request):
    if request.method == 'POST':
        nombre      = request.POST.get('nombre', '').strip()
        codigo      = request.POST.get('codigo', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        padre_id    = request.POST.get('padre') or None

        if not nombre or not codigo:
            messages.error(request, '⚠️ Nombre y código son obligatorios.')
            return redirect('categorias_lista')

        if Categoria.objects.filter(codigo=codigo).exists():
            messages.error(request, f'⚠️ Ya existe una categoría con el código "{codigo}".')
            return redirect('categorias_lista')

        padre = get_object_or_404(Categoria, pk=padre_id) if padre_id else None
        Categoria.objects.create(nombre=nombre, codigo=codigo, descripcion=descripcion, padre=padre)
        tipo = 'Subcategoría' if padre else 'Categoría'
        messages.success(request, f'✅ {tipo} "{nombre}" creada.')

    return redirect('categorias_lista')


@login_required
def categoria_editar(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        nombre      = request.POST.get('nombre', '').strip()
        codigo      = request.POST.get('codigo', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        padre_id    = request.POST.get('padre') or None

        if not nombre or not codigo:
            messages.error(request, '⚠️ Nombre y código son obligatorios.')
            return redirect('categorias_lista')

        if Categoria.objects.filter(codigo=codigo).exclude(pk=pk).exists():
            messages.error(request, f'⚠️ Ya existe otra categoría con el código "{codigo}".')
            return redirect('categorias_lista')

        categoria.nombre      = nombre
        categoria.codigo      = codigo
        categoria.descripcion = descripcion
        categoria.padre       = get_object_or_404(Categoria, pk=padre_id) if padre_id else None
        categoria.save()
        messages.success(request, f'✅ Categoría "{nombre}" actualizada.')

    return redirect('categorias_lista')


@login_required
def categoria_eliminar(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        if categoria.productos.exists() or categoria.subcategorias.exists():
            messages.error(request, f'⚠️ No se puede eliminar "{categoria.nombre}": tiene productos o subcategorías asociadas.')
        else:
            nombre = categoria.nombre
            categoria.delete()
            messages.success(request, f'✅ Categoría "{nombre}" eliminada.')
    return redirect('categorias_lista')


# ===============================
# AGENDA INVENTARIO
# ===============================
@login_required
def agenda_lista(request):
    agendas = AgendaInventario.objects.all().order_by('fecha_programada')
    return render(request, 'productos/agenda.html', {'agendas': agendas})


@login_required
def agenda_eliminar(request, pk):
    agenda = get_object_or_404(AgendaInventario, pk=pk)
    if request.method == 'POST':
        agenda.delete()
        messages.success(request, '✅ Registro de agenda eliminado.')
    return redirect('agenda_lista')

# ===============================
# GESTIÓN DE PRODUCTOS
# ===============================
@login_required
def gestion_productos(request):
    productos  = Producto.objects.select_related('categoria').all()
    categorias = Categoria.objects.all()
    return render(request, 'productos/gestion_productos.html', {
        'productos':  productos,
        'categorias': categorias,
    })
    # ===============================
# STOCK STATUS (widget)
# ===============================
@login_required
def stock_status(request):
    from django.urls import reverse
    productos = Producto.objects.prefetch_related('presentaciones__lotes').all()
    criticos, bajos = [], []

    for p in productos:
        stock_total = p.presentaciones.aggregate(total=Sum('lotes__stock_actual'))['total'] or 0
        
        # Tomamos la primera presentación para la URL
        primera_pres = p.presentaciones.first()
        pres_pk = primera_pres.pk if primera_pres else None
        
        entrada = {
            'nombre':            p.nombre,
            'cantidad':          stock_total,
            'url_presentacion':  reverse('gestion_productos'),
            'url_lote':          reverse('gestion_lotes') + f'?tab=lote&presentacion={pres_pk}' if pres_pk else '#',
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