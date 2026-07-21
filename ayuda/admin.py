from django.contrib import admin
from .models import CategoriaAyuda, ArticuloAyuda, MensajeSoporte

@admin.register(CategoriaAyuda)
class CategoriaAyudaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'orden')

@admin.register(ArticuloAyuda)
class ArticuloAyudaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'categoria', 'tipo', 'activo', 'orden')
    list_filter = ('tipo', 'categoria', 'activo')
    search_fields = ('titulo', 'contenido')

@admin.register(MensajeSoporte)
class MensajeSoporteAdmin(admin.ModelAdmin):
    list_display = ('asunto', 'usuario', 'fecha', 'atendido')
    list_filter = ('atendido',)