from django.shortcuts import render
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from .models import Producto, Categoria, PresentacionProducto


@login_required
def lista_productos(request):
    productos    = Producto.objects.select_related('categoria').prefetch_related('presentaciones').all()
    categorias   = Categoria.objects.filter(padre=None).prefetch_related('subcategorias', 'productos')
    resumen_categorias = Categoria.objects.filter(padre=None).annotate_total() \
        if hasattr(Categoria.objects, 'annotate_total') else Categoria.objects.filter(padre=None)

    # Resumen simple para las stat cards
    resumen = []
    for cat in Categoria.objects.filter(padre=None):
        total = Producto.objects.filter(categoria=cat).count()
        total += Producto.objects.filter(categoria__padre=cat).count()
        resumen.append({'pk': cat.pk, 'nombre': cat.nombre, 'total': total})

    context = {
        'productos':           productos,
        'categorias':          categorias,
        'resumen_categorias':  resumen,
    }
    return render(request, 'productos/productos.html', context)


@login_required
def crear_producto(request):
    if request.method == 'POST':
        nombre    = request.POST.get('nombre', '').strip()
        codigo    = request.POST.get('codigo', '').strip()
        categoria = request.POST.get('categoria')
        cantidad  = request.POST.get('cantidad_disponible', 0)
        descripcion = request.POST.get('descripcion', '').strip()

        errores = {}
        if not nombre:
            errores['nombre'] = ['El nombre es obligatorio.']
        if not categoria:
            errores['categoria'] = ['La categoría es obligatoria.']

        if errores:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'ok': False, 'errores': errores}, status=400)
            messages.error(request, 'Corrige los errores del formulario.')
            return redirect('producto:lista_productos')

        producto = Producto.objects.create(
            nombre=nombre,
            codigo=codigo or None,
            categoria_id=categoria,
            descripcion=descripcion,
        )

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'pk': producto.pk, 'nombre': producto.nombre})

        messages.success(request, f'Producto "{producto.nombre}" creado correctamente.')
        return redirect('producto:lista_productos')

    return JsonResponse({'ok': False, 'error': 'Método no permitido.'}, status=405)


@login_required
def presentaciones_guardar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)

    if request.method == 'POST':
        nombres   = request.POST.getlist('nombre[]')
        unidades  = request.POST.getlist('unidades_base[]')
        precios   = request.POST.getlist('precio[]')
        cantidades = request.POST.getlist('cantidad[]')

        # Elimina presentaciones anteriores y recrea
        producto.presentaciones.all().delete()

        for i in range(len(nombres)):
            nombre_p = nombres[i].strip()
            if not nombre_p:
                continue
            PresentacionProducto.objects.create(
                producto=producto,
                nombre=nombre_p,
                unidades=int(unidades[i]) if unidades[i] else 1,
                precio=precios[i] if precios[i] else 0,
            )

        messages.success(request, 'Presentaciones guardadas correctamente.')
        next_url = request.GET.get('next', 'producto:lista_productos')
        return redirect(next_url)

    return redirect('producto:lista_productos')


@login_required
def buscar_producto(request):
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse({'encontrado': False, 'mensaje': 'Escribe un nombre o código.'})

    producto = Producto.objects.filter(nombre__icontains=q).first() or \
               Producto.objects.filter(codigo__icontains=q).first()

    if not producto:
        return JsonResponse({'encontrado': False, 'mensaje': f'No se encontró "{q}".'})

    presentaciones = [
        {
            'nombre':   p.nombre,
            'unidades': p.unidades,
            'precio':   str(p.precio),
            'cantidad': 0,
        }
        for p in producto.presentaciones.all()
    ]

    return JsonResponse({
        'encontrado': True,
        'producto': {
            'nombre':              producto.nombre,
            'codigo':              producto.codigo or '',
            'categoria':           producto.categoria.nombre,
            'stock_total':         0,
            'cantidad_disponible': 0,
            'stock_presentaciones': 0,
            'presentaciones':      presentaciones,
        }
    })


@login_required
def stock_status(request):
    """Endpoint para el widget de stock."""
    productos = Producto.objects.prefetch_related('presentaciones').all()
    criticos, bajos = [], []

    for p in productos:
        stock = sum(l.stock_actual for l in getattr(p, 'lotes_relacionados', []))
        if stock == 0 or stock <= 3:
            criticos.append({'nombre': p.nombre, 'cantidad': stock})
        elif stock <= 10:
            bajos.append({'nombre': p.nombre, 'cantidad': stock})

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
def rotacion_json(request):
    """Datos de rotación para la gráfica."""
    return JsonResponse({
        'rotacion':          [],
        'sin_movimiento':    [],
        'estrella_nombre':   None,
        'estrella_categoria': None,
        'estrella_vendido':  0,
        'estrella_ingresos': 0,
        'estrella_presentacion': None,
        'estrella_stock':    0,
        'estrella_stock_critico': False,
    })