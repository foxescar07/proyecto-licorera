from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse

from productos.models import Producto, Categoria, PresentacionProducto


@login_required
def detalle_producto_lista(request):
    categorias     = Categoria.objects.filter(padre=None).prefetch_related('subcategorias', 'productos__presentaciones')
    todas_cats     = Categoria.objects.all()
    productos      = Producto.objects.select_related('categoria').prefetch_related('presentaciones__lotes').all()
    total_criticos = 0
    con_codigo     = productos.exclude(codigo__isnull=True).exclude(codigo__exact='').count()
    sin_codigo     = productos.count() - con_codigo

    context = {
        'categorias':     categorias,
        'todas_cats':     todas_cats,
        'productos':      productos,
        'lotes':          [],
        'total_criticos': total_criticos,
        'con_codigo':     con_codigo,
        'sin_codigo':     sin_codigo,
        'breadcrumb_items': [
            {'nombre': 'Detalle de Producto', 'url': None},
        ],
    }
    return render(request, 'detalle_producto/detalle_producto.html', context)


@login_required
def detalle_producto_desactivar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        producto.activo = False
        producto.save()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'nombre': producto.nombre, 'activo': False})
        messages.success(request, f'⏸️ Producto "{producto.nombre}" desactivado correctamente.')
    return redirect('detalle_producto:lista')


@login_required
def detalle_producto_activar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        producto.activo = True
        producto.save()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'nombre': producto.nombre, 'activo': True})
        messages.success(request, f'▶️ Producto "{producto.nombre}" activado correctamente.')
    return redirect('detalle_producto:lista')


@login_required
def detalle_producto_editar(request, pk):
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
    return redirect('detalle_producto:lista')

@login_required
def guardar_codigo(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        producto.codigo = request.POST.get('codigo', '').strip()
        producto.save()
        return JsonResponse({'ok': True, 'codigo': producto.codigo})
    return JsonResponse({'ok': False, 'error': 'Método no permitido.'}, status=405)