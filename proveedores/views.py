# proveedores/views.py
from django.shortcuts import render

def lista_proveedores(request):
    return render(request, 'proveedores/proveedores.html', {})

def lista_compras(request):
    return render(request, 'proveedores/compras.html', {})
