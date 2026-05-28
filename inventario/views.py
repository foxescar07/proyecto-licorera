from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Inventario, AgendaInventario, SesionConteo, ConteoProducto
from productos.models import Producto, PresentacionProducto


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
        return redirect('inventario:inventario_home')

    hoy          = timezone.now().date()
    fecha_filtro = request.GET.get('fecha_mov', str(hoy))

    movimientos = Inventario.objects.select_related(
        'lote__presentacion__producto__categoria',
        'registrado_por'
    ).filter(fecha_actualizada__date=fecha_filtro).order_by('-fecha_actualizada')

    dias_con_movimientos = Inventario.objects.dates('fecha_actualizada', 'day', order='DESC')[:30]
    agendas      = AgendaInventario.objects.order_by('fecha_programada')
    sesion       = SesionConteo.objects.filter(estado='activa').first()
    conteos      = ConteoProducto.objects.filter(sesion=sesion).select_related('presentacion__producto') if sesion else []
    productos    = Producto.objects.all()
    discrepancias = []

    context = {
        'movimientos':           movimientos,
        'dias_con_movimientos':  dias_con_movimientos,
        'fecha_filtro':          fecha_filtro,
        'hoy':                   str(hoy),
        'agendas':               agendas,
        'sesion':                sesion,
        'conteos':               conteos,
        'productos':             productos,
        'discrepancias':         discrepancias,
        'con_codigo':            Producto.objects.exclude(codigo='').exclude(codigo=None).count(),
        'sin_codigo':            Producto.objects.filter(codigo=None).count() + Producto.objects.filter(codigo='').count(),
    }
    return render(request, 'inventario/inventario_home.html', context)


@login_required
def agenda_estado(request, pk):
    if request.method == 'POST':
        agenda = get_object_or_404(AgendaInventario, pk=pk)
        agenda.estado = request.POST.get('estado', agenda.estado)
        agenda.save()
        messages.success(request, 'Estado actualizado.')
    return redirect('inventario:inventario_home')


@login_required
def conteo_inventario(request):
    if request.method == 'POST' and request.POST.get('iniciar_sesion') is not None:
        SesionConteo.objects.filter(estado='activa').update(estado='finalizada')
        SesionConteo.objects.create(responsable=request.user, estado='activa')
        messages.success(request, 'Sesión de conteo iniciada.')
    return redirect('inventario:inventario_home')


@login_required
def guardar_conteo(request):
    if request.method == 'POST':
        sesion_id       = request.POST.get('sesion_id')
        producto_id     = request.POST.get('producto_id')
        cantidad_contada = int(request.POST.get('cantidad_contada', 0))

        sesion      = get_object_or_404(SesionConteo, pk=sesion_id)
        presentacion = PresentacionProducto.objects.filter(producto_id=producto_id).first()

        if presentacion:
            ConteoProducto.objects.update_or_create(
                sesion=sesion,
                presentacion=presentacion,
                defaults={'cantidad_contada': cantidad_contada}
            )
            messages.success(request, 'Conteo guardado.')
    return redirect('inventario:inventario_home')


@login_required
def ajustar_stock(request, pk):
    if request.method == 'POST':
        messages.success(request, 'Ajuste de stock registrado.')
    return redirect('inventario:inventario_home')


@login_required
def guardar_codigo(request, pk):
    if request.method == 'POST':
        producto = get_object_or_404(Producto, pk=pk)
        producto.codigo = request.POST.get('codigo', '').strip()
        producto.save()
        messages.success(request, f'Código guardado para {producto.nombre}.')
    return redirect('inventario:inventario_home')


@login_required
def editar_movimiento(request, pk):
    if request.method == 'POST':
        mov = get_object_or_404(Inventario, pk=pk)
        mov.tipo     = request.POST.get('tipo', mov.tipo)
        mov.cantidad = int(request.POST.get('cantidad', mov.cantidad))
        mov.motivo   = request.POST.get('motivo', mov.motivo)
        mov.save()
        messages.success(request, 'Movimiento actualizado.')
    return redirect('inventario:inventario_home')


@login_required
def gestion_productos(request):
    from productos.models import Categoria
    categorias  = Categoria.objects.filter(padre=None).prefetch_related('subcategorias', 'productos__presentaciones')
    todas_cats  = Categoria.objects.all()
    productos   = Producto.objects.prefetch_related('presentaciones').all()
    lotes       = []
    total_criticos = 0

    context = {
        'categorias':     categorias,
        'todas_cats':     todas_cats,
        'productos':      productos,
        'lotes':          lotes,
        'total_criticos': total_criticos,
    }
    return render(request, 'inventario/gestion_productos.html', context)