# 🎯 Guía: Implementar Botones Editar, Notas e Historial

## 📋 Lo que se quitó
- ❌ Botón "Duplicar" (innecesario)
- ❌ Modal "Duplicar Orden"

## ✅ Lo que falta implementar

### 1. Modelo OrdenCompra - Agregar campo de notas

En `proveedores/models.py`:

```python
class OrdenCompra(models.Model):
    # ... campos existentes ...
    
    notas = models.TextField(
        blank=True,
        null=True,
        help_text="Notas internas sobre la orden"
    )
```

### 2. Modelo HistorialOrden (NUEVO)

Agregar en `proveedores/models.py`:

```python
class HistorialOrden(models.Model):
    EVENTO_CHOICES = [
        ('creada', 'Orden Creada'),
        ('confirmada', 'Confirmada'),
        ('recibida', 'Recibida'),
        ('cancelada', 'Cancelada'),
        ('nota_agregada', 'Nota Agregada'),
        ('editada', 'Editada'),
    ]
    
    orden = models.ForeignKey(
        OrdenCompra,
        on_delete=models.CASCADE,
        related_name='historial'
    )
    evento = models.CharField(max_length=20, choices=EVENTO_CHOICES)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    fecha = models.DateTimeField(auto_now_add=True)
    descripcion = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-fecha']
    
    def __str__(self):
        return f"{self.orden.id} - {self.get_evento_display()}"
```

### 3. Vistas Django (proveedores/views.py)

```python
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from .models import OrdenCompra, DetalleCompra, HistorialOrden
from datetime import datetime

# GUARDAR NOTAS
@login_required
@require_http_methods(["POST"])
def guardar_nota_orden(request, pk):
    try:
        orden = OrdenCompra.objects.get(id=pk)
        nota = request.POST.get('notas', '')
        
        orden.notas = nota
        orden.save()
        
        # Registrar en historial
        HistorialOrden.objects.create(
            orden=orden,
            evento='nota_agregada',
            usuario=request.user,
            descripcion=f"Nota actualizada: {nota[:50]}..."
        )
        
        return JsonResponse({'status': 'ok', 'message': 'Nota guardada'})
    except OrdenCompra.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Orden no encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


# OBTENER HISTORIAL
@login_required
@require_http_methods(["GET"])
def obtener_historial_orden(request, pk):
    try:
        orden = OrdenCompra.objects.get(id=pk)
        historial = orden.historial.all()
        
        # Agregar evento de creación automáticamente
        eventos = []
        
        # Evento: Creación
        eventos.append({
            'evento': 'Orden Creada',
            'usuario': orden.registrado_por.get_full_name() if orden.registrado_por else 'Sistema',
            'fecha': orden.fecha.strftime('%d/%m/%Y %H:%M'),
            'descripcion': 'Orden creada en el sistema',
            'color': '#9b5de5'
        })
        
        # Eventos del historial
        for h in historial:
            eventos.append({
                'evento': h.get_evento_display(),
                'usuario': h.usuario.get_full_name() if h.usuario else 'Sistema',
                'fecha': h.fecha.strftime('%d/%m/%Y %H:%M'),
                'descripcion': h.descripcion,
                'color': {
                    'creada': '#9b5de5',
                    'confirmada': '#4DA8DA',
                    'recibida': '#27ae60',
                    'cancelada': '#e74c3c',
                    'nota_agregada': '#f39c12',
                    'editada': '#4DA8DA',
                }.get(h.evento, '#8FA3B1')
            })
        
        return JsonResponse({'status': 'ok', 'historial': eventos})
    except OrdenCompra.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Orden no encontrada'}, status=404)


# EDITAR DETALLE (opcional)
@login_required
@require_http_methods(["POST"])
def editar_detalle_orden(request, detalle_id):
    try:
        detalle = DetalleCompra.objects.get(id=detalle_id)
        
        # Solo si la orden está en pendiente
        if detalle.orden_compra.estado != 'pendiente':
            return JsonResponse({
                'status': 'error',
                'message': 'No se puede editar orden que no está pendiente'
            }, status=400)
        
        # Actualizar detalle
        detalle.cantidad = int(request.POST.get('cantidad'))
        detalle.precio_unitario = float(request.POST.get('precio_unitario'))
        detalle.save()
        
        # Recalcular total de la orden
        detalle.orden_compra.calcular_total()
        
        # Registrar en historial
        HistorialOrden.objects.create(
            orden=detalle.orden_compra,
            evento='editada',
            usuario=request.user,
            descripcion=f"Editada línea: {detalle.presentacion.nombre}"
        )
        
        return JsonResponse({
            'status': 'ok',
            'subtotal': str(detalle.subtotal),
            'total_orden': str(detalle.orden_compra.total)
        })
    except DetalleCompra.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Detalle no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
```

### 4. URLs (proveedores/urls.py)

Agregar estas rutas:

```python
path('ordenes/<int:pk>/notas/', views.guardar_nota_orden, name='guardar_nota_orden'),
path('ordenes/<int:pk>/historial/', views.obtener_historial_orden, name='historial_orden'),
path('detalles/<int:detalle_id>/editar/', views.editar_detalle_orden, name='editar_detalle'),
```

### 5. Migraciones

```bash
python manage.py makemigrations
python manage.py migrate
```

---

## ✅ Lo que ya está listo

- ✅ Modales en HTML (Notas, Editar Detalle, Historial)
- ✅ Botones en modal de detalle
- ✅ JavaScript para manejar clicks
- ✅ Estilos CSS

---

## 🧪 Testing

1. **Notas**: Click botón "Notas" → escribe texto → "Guardar Nota"
2. **Historial**: Click botón "Historial" → ver timeline de cambios
3. **Editar**: (si pendiente) Click "Editar" → cambiar cantidad/precio → "Guardar Cambios"

---

## 📝 Admin (opcional)

Para administrar desde Django admin:

```python
# proveedores/admin.py

@admin.register(HistorialOrden)
class HistorialOrdenAdmin(admin.ModelAdmin):
    list_display = ('orden', 'evento', 'usuario', 'fecha')
    list_filter = ('evento', 'fecha', 'usuario')
    search_fields = ('orden__id', 'descripcion')
    readonly_fields = ('fecha', 'usuario')
```

---

**Última actualización:** 2026-07-02
