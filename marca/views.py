from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Marca
from .forms import MarcaForm


@login_required
def lista_marcas(request):
    marcas = Marca.objects.all()
    return render(request, "marcas/marcas_list.html", {
        "marcas": marcas
    })


@login_required
def crear_marca(request):
    if request.method == "POST":
        form = MarcaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Marca creada correctamente.")
            return redirect("lista_marcas")
    else:
        form = MarcaForm()
    return render(request, "marcas/marca_form.html", {
        "form": form, "titulo": "Nueva Marca"
    })


@login_required
def editar_marca(request, pk):
    marca = get_object_or_404(Marca, pk=pk)
    if request.method == "POST":
        form = MarcaForm(request.POST, instance=marca)
        if form.is_valid():
            form.save()
            messages.success(request, "Marca actualizada correctamente.")
            return redirect("lista_marcas")
    else:
        form = MarcaForm(instance=marca)
    return render(request, "marcas/marca_form.html", {
        "form": form, "titulo": "Editar Marca"
    })


@login_required
def eliminar_marca(request, pk):
    marca = get_object_or_404(Marca, pk=pk)
    if request.method == "POST":
        marca.delete()
        messages.success(request, "Marca eliminada correctamente.")
        return redirect("lista_marcas")
    return render(request, "marcas/confirmar_eliminar.html", {
        "objeto": marca, "tipo": "Marca", "url_cancelar": "lista_marcas"
    })