from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db import models as db_models
from django.db.models import Prefetch

from .models import Inventario, AgendaInventario, SesionConteo, ConteoProducto, Lote
from productos.models import Producto, PresentacionProducto, Categoria


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
    agendas   = AgendaInventario.objects.order_by('fecha_programada')
    sesion    = SesionConteo.objects.filter(estado='activa').first()
    conteos   = ConteoProducto.objects.filter(sesion=sesion).select_related('presentacion__producto') if sesion else []
    productos = Producto.objects.all()

    discrepancias = []
    if sesion:
        for c in ConteoProducto.objects.filter(sesion=sesion).select_related('presentacion__producto__categoria'):
            diff = c.cantidad_contada - c.presentacion.stock_total
            discrepancias.append({
                'presentacion': c.presentacion,
                'en_sistema':   c.presentacion.stock_total,
                'fisico':       c.cantidad_contada,
                'diferencia':   diff,
                'estado':       'ok' if diff == 0 else ('sobrante' if diff > 0 else 'faltante'),
            })

    context = {
        'movimientos':          movimientos,
        'dias_con_movimientos': dias_con_movimientos,
        'fecha_filtro':         fecha_filtro,
        'hoy':                  str(hoy),
        'agendas':              agendas,
        'sesion':               sesion,
        'conteos':              conteos,
        'productos':            productos,
        'discrepancias':        discrepancias,
        'con_codigo':           Producto.objects.exclude(codigo='').exclude(codigo=None).count(),
        'sin_codigo':           Producto.objects.filter(codigo=None).count() + Producto.objects.filter(codigo='').count(),
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
        sesion_id        = request.POST.get('sesion_id')
        producto_id      = request.POST.get('producto_id')
        cantidad_contada = int(request.POST.get('cantidad_contada', 0))

        sesion       = get_object_or_404(SesionConteo, pk=sesion_id)
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
        try:
            mov.tipo     = request.POST.get('tipo', mov.tipo)
            mov.cantidad = int(request.POST.get('cantidad', mov.cantidad))
            mov.motivo   = request.POST.get('motivo', mov.motivo)
            mov.ubicacion = request.POST.get('ubicacion', getattr(mov, 'ubicacion', ''))
            mov.save()
            messages.success(request, f'✅ Movimiento de "{mov.presentacion.producto.nombre}" actualizado.')
        except (ValueError, TypeError):
            messages.error(request, '❌ Cantidad inválida.')
    return redirect('inventario:inventario_home')


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
    return render(request, 'inventario/gestion_productos.html', context)


@login_required
def gestion_inventario(request):
    productos = Producto.objects.select_related('categoria').prefetch_related('presentaciones__lotes').all()
    return render(request, 'inventario/gestion_inventario.html', {'productos': productos})


@login_required
def gestion_salida(request):
    if request.method == 'POST':
        presentacion_id = request.POST.get('presentacion')
        cantidad_raw    = request.POST.get('cantidad', '')
        motivo          = request.POST.get('motivo', '').strip()
        lote_id         = request.POST.get('lote_id') or None

        if not presentacion_id:
            messages.error(request, '⚠️ Debes seleccionar una presentación.')
            return redirect('inventario:gestion_inventario')

        try:
            cantidad = int(cantidad_raw)
            if cantidad <= 0:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, '⚠️ La cantidad debe ser un número mayor a cero.')
            return redirect('inventario:gestion_inventario')

        if not motivo:
            messages.error(request, '⚠️ Debes indicar el motivo de la salida.')
            return redirect('inventario:gestion_inventario')

        if lote_id:
            lote = get_object_or_404(Lote, pk=lote_id)
            if lote.fecha_vencimiento and lote.fecha_vencimiento < timezone.now().date():
                messages.error(request, f'🚫 El lote "{lote.numero_lote}" está vencido desde el {lote.fecha_vencimiento.strftime("%d/%m/%Y")}.')
                return redirect('inventario:gestion_inventario')

        presentacion = get_object_or_404(PresentacionProducto, pk=presentacion_id)
        producto     = presentacion.producto

        if cantidad > presentacion.cantidad:
            messages.error(request, f'⚠️ Stock insuficiente: solo hay {presentacion.cantidad} unidades de "{presentacion.nombre}".')
            return redirect('inventario:gestion_inventario')

        # Descontar lotes por FEFO
        restante = cantidad
        lotes_qs = presentacion.lotes.filter(stock_actual__gt=0).order_by(
            db_models.F('fecha_vencimiento').asc(nulls_last=True), 'id'
        )
        for lote in lotes_qs:
            if restante <= 0:
                break
            if lote.stock_actual >= restante:
                lote.stock_actual -= restante
                lote.save()
                restante = 0
            else:
                restante -= lote.stock_actual
                lote.stock_actual = 0
                lote.save()

        Inventario.objects.create(
            presentacion=presentacion,
            lote=presentacion.lotes.order_by('fecha_vencimiento').first(),
            registrado_por=request.user,
            tipo='salida',
            cantidad=cantidad,
            motivo=motivo,
        )
        messages.success(request, f'✅ Salida de {cantidad} × "{presentacion.nombre}" registrada para {producto.nombre}.')

    return redirect('inventario:gestion_inventario')


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
                'ok':         True,
                'cambios':    cambios if cambios else [],
                'sin_cambios': len(cambios) == 0,
            })

    return redirect('inventario:gestion_productos')


@login_required
def gestion_producto_eliminar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        nombre = producto.nombre
        producto.delete()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'nombre': nombre})
    return redirect('inventario:gestion_productos')


@login_required
def gestion_categoria_crear(request):
    if request.method == 'POST':
        nombre      = request.POST.get('nombre', '').strip()
        codigo      = request.POST.get('codigo', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        padre_id    = request.POST.get('padre') or None

        if not nombre or not codigo:
            messages.error(request, '⚠️ Nombre y código son obligatorios.')
            return redirect('inventario:gestion_productos')

        if Categoria.objects.filter(codigo=codigo).exists():
            messages.error(request, f'⚠️ Ya existe una categoría con el código "{codigo}".')
            return redirect('inventario:gestion_productos')

        padre = get_object_or_404(Categoria, pk=padre_id) if padre_id else None
        Categoria.objects.create(nombre=nombre, codigo=codigo, descripcion=descripcion, padre=padre)
        tipo = 'Subcategoría' if padre else 'Categoría'
        messages.success(request, f'✅ {tipo} "{nombre}" creada.')

    return redirect('inventario:gestion_productos')


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
            return redirect('inventario:gestion_productos')

        if Categoria.objects.filter(codigo=codigo).exclude(pk=pk).exists():
            messages.error(request, f'⚠️ Ya existe otra categoría con el código "{codigo}".')
            return redirect('inventario:gestion_productos')

        categoria.nombre      = nombre
        categoria.codigo      = codigo
        categoria.descripcion = descripcion
        categoria.padre       = get_object_or_404(Categoria, pk=padre_id) if padre_id else None
        categoria.save()
        messages.success(request, f'✅ Categoría "{nombre}" actualizada.')

    return redirect('inventario:gestion_productos')


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
    return redirect('inventario:gestion_productos')


@login_required
def registrar_lote(request):
    if request.method == 'POST':
        numero_lote       = request.POST.get('numero_lote', '').strip()
        presentacion_id   = request.POST.get('presentacion')
        costo_unitario    = request.POST.get('costo_unitario', 0)
        stock_inicial     = request.POST.get('stock_inicial', 0)
        fecha_vencimiento = request.POST.get('fecha_vencimiento') or None

        if not numero_lote:
            messages.error(request, '⚠️ El número de lote es obligatorio.')
            return redirect('inventario:gestion_inventario')

        if not presentacion_id:
            messages.error(request, '⚠️ Debes seleccionar una presentación.')
            return redirect('inventario:gestion_inventario')

        if Lote.objects.filter(numero_lote=numero_lote).exists():
            messages.error(request, f'⚠️ El lote "{numero_lote}" ya está registrado.')
            return redirect('inventario:gestion_inventario')

        presentacion = get_object_or_404(PresentacionProducto, pk=presentacion_id)

        lote = Lote.objects.create(
            numero_lote=numero_lote,
            presentacion=presentacion,
            costo_unitario=costo_unitario,
            stock_actual=stock_inicial,
            fecha_vencimiento=fecha_vencimiento,
            registrado_por=request.user,
        )

        if fecha_vencimiento:
            messages.success(request, f'✅ Lote "{numero_lote}" registrado para "{presentacion.producto.nombre}" — vence el {lote.fecha_vencimiento.strftime("%d/%m/%Y")}.')
        else:
            messages.success(request, f'✅ Lote "{numero_lote}" registrado para "{presentacion.producto.nombre}" (sin fecha de vencimiento).')

    return redirect('inventario:gestion_inventario')