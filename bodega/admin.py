from django.contrib import admin
from .models import (
    AgendaInventario,
    Hallazgo,
)

@admin.register(AgendaInventario)
class AgendaInventarioAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'fecha', 'estado', 'responsable']
    list_filter  = ['estado']

@admin.register(Hallazgo)
class HallazgoAdmin(admin.ModelAdmin):
    list_display = ['agenda', 'producto', 'cantidad_sistema', 'cantidad_fisica', 'diferencia', 'tipo_hallazgo']
    list_filter  = ['tipo_hallazgo']