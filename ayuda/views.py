from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import CategoriaAyuda, ArticuloAyuda
from .forms import MensajeSoporteForm


@login_required
def index_ayuda(request):
    categorias = CategoriaAyuda.objects.prefetch_related('articulos')
    faqs  = ArticuloAyuda.objects.filter(tipo='faq', activo=True).select_related('categoria')
    guias = ArticuloAyuda.objects.filter(tipo='guia', activo=True).select_related('categoria')

    if request.method == 'POST':
        form = MensajeSoporteForm(request.POST)
        if form.is_valid():
            mensaje = form.save(commit=False)
            mensaje.usuario = request.user
            mensaje.save()
            messages.success(request, '✅ Tu mensaje fue enviado. Te responderemos pronto.')
            return redirect('ayuda:index')
        messages.error(request, 'Corrige los errores del formulario.')
    else:
        form = MensajeSoporteForm()

    context = {
        'categorias': categorias,
        'faqs': faqs,
        'guias': guias,
        'form': form,
        'breadcrumb_items': [
            {'nombre': 'Ayuda', 'url': None},
        ],
    }
    return render(request, 'ayuda/ayuda.html', context)