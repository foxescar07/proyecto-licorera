from django.http import HttpResponse

def home(request):
    return HttpResponse("<h1>Proyecto Licorera - Base de Operaciones</h1><p>Las tablas del MER se han cargado exitosamente.</p>")
