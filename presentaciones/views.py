from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction

from productos.models import Producto, PresentacionProducto


@login_required
def guardar(request, pk):
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
def listar_json(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    data     = list(producto.presentaciones.values('id', 'nombre', 'unidades', 'precio'))
    return JsonResponse({'presentaciones': data, 'producto': producto.nombre})
