from django.contrib import admin
from .models import Marca


@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activo", "fecha_creacion")
    list_filter = ("activo",)
    search_fields = ("nombre",)