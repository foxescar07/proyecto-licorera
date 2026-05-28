from django.shortcuts import render, redirect

def principal(request):
    if not request.session.get('usuario_id'):
        return redirect('login')
    return render(request, 'principal.html')

def cerrar_sesion(request):
    request.session.flush()
    return redirect('login')