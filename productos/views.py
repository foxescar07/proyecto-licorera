from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Prefetch
from django.db import transaction
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta
from django.db import IntegrityError

from .models import Producto, Categoria, PresentacionProducto
from inventario.models import Inventario, MovimientoInventario
from .forms import ProductoRegistroForm

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
        'breadcrumb_items': [
            {'nombre': 'Productos', 'url': None},
        ],
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
    if codigo and Producto.objects.filter(codigo=codigo).exists():
        errores['codigo'] = [f'Ya existe un producto con el código "{codigo}".']

    if errores:
        if is_ajax:
            return JsonResponse({'ok': False, 'errores': errores}, status=400)
        messages.error(request, 'Corrige los errores del formulario.')
        return redirect('lista_productos')

    try:
        producto = Producto.objects.create(
            nombre=nombre,
            codigo=codigo,  # ya validamos que no está vacío ni duplicado; si va vacío, generamos abajo
            categoria_id=categoria,
            descripcion=descripcion,
        )
    except IntegrityError:
        error_msg = 'No se pudo crear el producto (código duplicado).'
        if is_ajax:
            return JsonResponse({'ok': False, 'error': error_msg}, status=400)
        messages.error(request, error_msg)
        return redirect('lista_productos')

    messages.success(request, f'✅ Producto "{producto.nombre}" creado correctamente.')

    if is_ajax:
        return JsonResponse({'ok': True, 'pk': producto.pk, 'nombre': producto.nombre})

    return redirect(next_url)

# ===============================
# DETALLE PRODUCTO
# ===============================
@login_required
def producto_detalle(request, pk):
    producto    = get_object_or_404(Producto, pk=pk)
    movimientos = MovimientoInventario.objects.filter(
    inventario__producto=producto
).order_by('-fecha')
    context = {
        'producto': producto,
        'movimientos': movimientos,
        'breadcrumb_items': [
            {'nombre': 'Productos', 'url': reverse('lista_productos')},
            {'nombre': producto.nombre, 'url': None},
        ],
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
        'breadcrumb_items': [
            {'nombre': 'Productos', 'url': reverse('lista_productos')},
            {'nombre': 'Registrar Producto', 'url': None},
        ],
    }

    return render(request, 'productos/productos.html', context)

# ===============================
# STOCK STATUS (Widget con URLs unificado)

# ===============================
@login_required
def stock_status(request):
    criticos = []
    bajos = []

    for producto in Producto.objects.filter(activo=True):
        if producto.stock_critico:
            criticos.append({'nombre': producto.nombre, 'total_stock': producto.stock_total})

    for item in Inventario.objects.select_related('producto'):
        if item.necesita_reabastecimiento and not item.producto.stock_critico:
            bajos.append({'nombre': item.producto.nombre, 'total_stock': item.stock_actual})

    return JsonResponse({
        'criticos': criticos,
        'bajos': bajos,
        'total_alertas': len(criticos) + len(bajos),
    })
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
