from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm


def login_view(request):
    form = AuthenticationForm(request, data=request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')

    return render(request, 'usuarios/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


# Vista de usuario
def usuario(request) -> HttpResponse:
    return render(request, 'usuario.html')