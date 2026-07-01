from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Prefetch
from django.db import transaction
from django.utils import timezone
from django.urls import reverse
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
    
    # Se calcula usando la propiedad o agregando lógica alternativa segura si stock_critico es dinámico
    total_criticos = sum(1 for p in productos_qs if getattr(p, 'stock_critico', False))
    form           = ProductoRegistroForm()

    context = {
        'productos': productos_qs,
        'categorias': categorias,
        'todas_cats': todas_cats,
        'resumen_categorias': resumen_categorias,
        'form': form,
        'total_criticos': total_criticos,
    }

    return render(request, 'productos/productos.html', context)


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
    context = {
        'producto': producto,
        'movimientos': movimientos,
    }

    return render(request, 'productos/productos.html', context)


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
                                pres.lotes.all().update(costo_unitario=np_)
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

            nueva_pres = PresentacionProducto.objects.create(
                producto=producto,
                nombre=nombre_pres,
                unidades=unidades_pres,
                precio=precio_pres,
            )
            if precio_pres > 0:
                nueva_pres.lotes.all().update(costo_unitario=precio_pres)

            cambios.append(f'➕ Nueva presentación: "{nombre_pres}" · {unidades_pres} uds')

        if cambios:
            messages.success(request, f"✅ Producto '{producto.nombre}' actualizado.")
        else:
            messages.info(request, 'ℹ️ No se detectaron cambios en el producto.')

    return redirect('lista_productos')


@login_required
def gestion_producto_desactivar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        producto.activo = False
        producto.save()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'nombre': producto.nombre, 'activo': False})
        messages.success(request, f'⏸️ Producto "{producto.nombre}" desactivado correctamente.')
    return redirect('gestion_productos')


@login_required
def gestion_producto_activar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        producto.activo = True
        producto.save()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'nombre': producto.nombre, 'activo': True})
        messages.success(request, f'▶️ Producto "{producto.nombre}" activado correctamente.')
    return redirect('gestion_productos')


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
    context = {
        'form': form,
    }

    return render(request, 'productos/productos.html', context)


# ===============================
# STOCK STATUS (Widget con URLs unificado)
# ===============================


# ===============================
# SALIDA DE PRODUCTO
# ===============================


# ===============================
# BUSCAR PRODUCTO
# ===============================
@login_required
def buscar_producto(request):
    q    = request.GET.get('q', '').strip()
    modo = request.GET.get('modo', '')

    if not q:
        if modo == 'sugerencias':
            return JsonResponse({'resultados': []})
        return JsonResponse({'encontrado': False, 'mensaje': 'Escribe un nombre o código.'})

    # ── MODO SUGERENCIAS: lista corta para el autocomplete ──────────────
    if modo == 'sugerencias':
        productos = (
            Producto.objects.filter(nombre__icontains=q) |
            Producto.objects.filter(codigo__icontains=q)
        ).select_related('categoria').distinct()[:8]

        resultados = [{
            'pk':        p.pk,
            'nombre':    p.nombre,
            'codigo':    p.codigo or '—',
            'categoria': p.categoria.nombre if p.categoria else '—',
        } for p in productos]

        return JsonResponse({'resultados': resultados})

    # ── MODO DETALLE (comportamiento original, intacto) ─────────────────
    producto = (
        Producto.objects.filter(nombre__icontains=q).first() or
        Producto.objects.filter(codigo__icontains=q).first()
    )

    if not producto:
        return JsonResponse({'encontrado': False, 'mensaje': f'No se encontró "{q}".'})

    stock_total = producto.presentaciones.aggregate(
        total=Sum('lotes__stock_actual')
    )['total'] or 0

    presentaciones = []
    for pres in producto.presentaciones.all():
        stock_pres = pres.lotes.aggregate(total=Sum('stock_actual'))['total'] or 0
        presentaciones.append({
            'id':           pres.id,
            'nombre':       pres.nombre,
            'unidades':     pres.unidades,
            'precio':       str(pres.precio),
            'stock_actual': stock_pres,
        })

    return JsonResponse({
        'encontrado': True,
        'producto': {
            'pk':           producto.pk,
            'nombre':       producto.nombre,
            'codigo':       producto.codigo or '—',
            'categoria':    producto.categoria.nombre if producto.categoria else '—',
            'stock_total':  stock_total,
            'descripcion':  producto.descripcion or '',
            'presentaciones': presentaciones,
        }
    })


# ===============================
# ROTACIÓN JSON
# ===============================


# ===============================
# GESTIÓN DE CATEGORÍAS
# ===============================
@login_required
def categorias_lista(request):
    categorias = Categoria.objects.prefetch_related(
        'productos', 'subcategorias__productos'
    ).filter(padre__isnull=True)
    todas_cats = Categoria.objects.all()
    context = {
        'categorias': categorias,
        'todas_cats': todas_cats,
    }
    return render(request, 'productos/categorias.html', context)


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




# ===============================
# FUNCIONES MOVIDAS DESDE INVENTARIO
# ===============================
@login_required
def gestion_productos(request):
    categorias     = Categoria.objects.filter(padre=None).prefetch_related('subcategorias', 'productos__presentaciones')
    todas_cats     = Categoria.objects.all()
    productos      = Producto.objects.select_related('categoria').prefetch_related('presentaciones__lotes').all()
    total_criticos = 0

    context = {
        'categorias':     categorias,
        'todas_cats':     todas_cats,
        'productos':      productos,
        'lotes':          [],
        'total_criticos': total_criticos,
    }
    return render(request, 'productos/gestion_productos.html', context)

@login_required
def gestion_producto_editar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        cambios = []

        nombre       = request.POST.get('nombre', '').strip()
        codigo       = request.POST.get('codigo', '').strip()
        descripcion  = request.POST.get('descripcion', '').strip()
        categoria_pk = request.POST.get('categoria')
        precio_raw   = request.POST.get('precio_unitario', '').strip()

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

        if precio_raw:
            try:
                nuevo_precio = max(0, float(precio_raw))
                if nuevo_precio != float(producto.precio_unitario or 0):
                    cambios.append(f'💲 Precio base: ${int(producto.precio_unitario or 0):,} → ${int(nuevo_precio):,}')
                producto.precio_unitario = nuevo_precio
            except (ValueError, TypeError):
                pass

        producto.save()

        for key, valor in request.POST.items():
            if key.startswith('pres_nombre_'):
                pres_id = key.replace('pres_nombre_', '')
                try:
                    pres           = PresentacionProducto.objects.get(pk=int(pres_id), producto=producto)
                    nuevo_nombre   = valor.strip()
                    nuevo_precio   = request.POST.get(f'pres_precio_{pres_id}', '').strip()
                    nueva_cantidad = request.POST.get(f'pres_cantidad_{pres_id}', '').strip()

                    if nuevo_nombre and nuevo_nombre != pres.nombre:
                        cambios.append(f'📦 Presentación: "{pres.nombre}" → "{nuevo_nombre}"')
                        pres.nombre = nuevo_nombre

                    if nuevo_precio:
                        try:
                            np = max(0, float(nuevo_precio))
                            if np != float(pres.precio or 0):
                                cambios.append(f'💲 Precio "{pres.nombre}": ${int(pres.precio or 0):,} → ${int(np):,}')
                            pres.precio = np
                        except (ValueError, TypeError):
                            pass

                    if nueva_cantidad:
                        try:
                            nq = max(0, int(nueva_cantidad))
                            if nq != pres.cantidad:
                                diff  = nq - pres.cantidad
                                signo = f'+{diff}' if diff > 0 else str(diff)
                                cambios.append(f'📊 Stock "{pres.nombre}": {pres.cantidad} → {nq} ({signo} uds)')
                            pres.cantidad = nq
                        except (ValueError, TypeError):
                            pass

                    pres.save()
                except PresentacionProducto.DoesNotExist:
                    pass

        nuevos_nombres    = request.POST.getlist('nueva_pres_nombre[]')
        nuevos_precios    = request.POST.getlist('nueva_pres_precio[]')
        nuevas_cantidades = request.POST.getlist('nueva_pres_cantidad[]')

        for i, nombre_pres in enumerate(nuevos_nombres):
            nombre_pres = nombre_pres.strip()
            if not nombre_pres:
                continue
            if PresentacionProducto.objects.filter(producto=producto, nombre__iexact=nombre_pres).exists():
                continue
            try:
                precio_pres   = max(0, float(nuevos_precios[i]))   if i < len(nuevos_precios)    else 0
                cantidad_pres = max(0, int(nuevas_cantidades[i]))   if i < len(nuevas_cantidades) else 0
            except (ValueError, TypeError):
                precio_pres   = 0
                cantidad_pres = 0

            PresentacionProducto.objects.create(
                producto=producto,
                nombre=nombre_pres,
                precio=precio_pres,
                cantidad=cantidad_pres,
                unidades=1,
            )
            cambios.append(f'➕ Nueva presentación: "{nombre_pres}" ${int(precio_pres):,} · {cantidad_pres} uds')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'ok':          True,
                'cambios':     cambios if cambios else [],
                'sin_cambios': len(cambios) == 0,
            })

    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('gestion_productos')

@login_required
def gestion_producto_eliminar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        nombre = producto.nombre
        producto.delete()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'nombre': nombre})
    return redirect('gestion_productos')

@login_required
def gestion_categoria_crear(request):
    if request.method == 'POST':
        nombre      = request.POST.get('nombre', '').strip()
        codigo      = request.POST.get('codigo', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        padre_id    = request.POST.get('padre') or None

        if not nombre or not codigo:
            messages.error(request, '⚠️ Nombre y código son obligatorios.')
            return redirect('gestion_productos')

        if Categoria.objects.filter(codigo=codigo).exists():
            messages.error(request, f'⚠️ Ya existe una categoría con el código "{codigo}".')
            return redirect('gestion_productos')

        padre = get_object_or_404(Categoria, pk=padre_id) if padre_id else None
        Categoria.objects.create(nombre=nombre, codigo=codigo, descripcion=descripcion, padre=padre)
        tipo = 'Subcategoría' if padre else 'Categoría'
        messages.success(request, f'✅ {tipo} "{nombre}" creada.')

    return redirect('gestion_productos')

@login_required
def gestion_categoria_editar(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        nombre      = request.POST.get('nombre', '').strip()
        codigo      = request.POST.get('codigo', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        padre_id    = request.POST.get('padre') or None

        if not nombre or not codigo:
            messages.error(request, '⚠️ Nombre y código son obligatorios.')
            return redirect('gestion_productos')

        if Categoria.objects.filter(codigo=codigo).exclude(pk=pk).exists():
            messages.error(request, f'⚠️ Ya existe otra categoría con el código "{codigo}".')
            return redirect('gestion_productos')

        categoria.nombre      = nombre
        categoria.codigo      = codigo
        categoria.descripcion = descripcion
        categoria.padre       = get_object_or_404(Categoria, pk=padre_id) if padre_id else None
        categoria.save()
        messages.success(request, f'✅ Categoría "{nombre}" actualizada.')

    return redirect('gestion_productos')

@login_required
def gestion_categoria_eliminar(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        if categoria.productos.exists() or categoria.subcategorias.exists():
            messages.error(request, f'⚠️ No se puede eliminar "{categoria.nombre}": tiene productos o subcategorías asociadas.')
        else:
            nombre = categoria.nombre
            categoria.delete()
            messages.success(request, f'✅ Categoría "{nombre}" eliminada.')
    return redirect('gestion_productos')

