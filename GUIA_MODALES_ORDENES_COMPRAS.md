# 🎯 Guía: Modales Organizados para OrdenCompra y Compra

## 📍 Estructura de Modales Implementados

### En **OrdenCompra** (orden_compra.html):

```
Modal de Detalle (ya existía)
├─ 📝 NOTAS INTERNAS (modal nuevo)
│  └─ Guardar comentarios contextuales
├─ ✏️ EDITAR DETALLE (modal nuevo)
│  ├─ Editar cantidad/precio (solo si pendiente)
│  └─ Eliminar línea
├─ 📋 DUPLICAR ORDEN (modal nuevo)
│  ├─ Copiar productos
│  └─ Multiplicar cantidades
└─ ⏱️ HISTORIAL (modal nuevo)
   └─ Timeline de cambios (creada, confirmada, recibida, etc)
```

### En **Compra** (modelo legacy):
```
Modal de INFORMACIÓN DE PAGO (modal nuevo)
├─ 💳 Método de Pago
├─ 🔢 Número de Factura
├─ 💰 Estado de Pago (Pendiente/Parcial/Pagada)
├─ 📊 Monto Pagado
└─ 📅 Fecha de Pago
```

---

## ⚙️ Implementación en Django

### 1. **Modelo OrdenCompra** (proveedores/models.py)

Agregar campo de notas:

```python
class OrdenCompra(models.Model):
    # ... campos existentes ...
    
    notas = models.TextField(
        blank=True,
        null=True,
        help_text="Notas internas sobre la orden"
    )
```

### 2. **Modelo HistorialOrden** (NUEVO - para timeline)

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

### 3. **Modelo Compra** (proveedores/models.py)

Agregar campos de pago (como indicamos en guía anterior):

```python
class Compra(models.Model):
    METODO_PAGO_CHOICES = [
        ('transferencia', 'Transferencia Bancaria'),
        ('efectivo', 'Efectivo'),
        ('cheque', 'Cheque'),
        ('tarjeta', 'Tarjeta de Crédito'),
        ('credito', 'Crédito a 30 días'),
        ('otro', 'Otro'),
    ]
    
    ESTADO_PAGO_CHOICES = [
        ('pendiente', 'Pendiente de Pago'),
        ('pagada', 'Pagada'),
        ('parcial', 'Pago Parcial'),
    ]
    
    # ... campos existentes ...
    
    numero_factura = models.CharField(max_length=50, null=True, blank=True)
    metodo_pago = models.CharField(
        max_length=20,
        choices=METODO_PAGO_CHOICES,
        null=True,
        blank=True,
        default='transferencia'
    )
    estado_pago = models.CharField(
        max_length=20,
        choices=ESTADO_PAGO_CHOICES,
        default='pendiente'
    )
    monto_pagado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    fecha_pago = models.DateTimeField(null=True, blank=True)
```

### 4. **Migraciones**

```bash
python manage.py makemigrations
python manage.py migrate
```

---

## 🛣️ Vistas (views.py)

### Modal de Notas

```python
@login_required
def guardar_nota_orden(request, pk):
    if request.method == 'POST':
        orden = get_object_or_404(OrdenCompra, id=pk)
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
    return HttpResponseBadRequest()
```

### Modal de Editar Detalle

```python
@login_required
def editar_detalle_orden(request, detalle_id):
    if request.method == 'POST':
        detalle = get_object_or_404(DetalleCompra, id=detalle_id)
        
        # Solo si la orden está en pendiente
        if detalle.orden_compra.estado != 'pendiente':
            return HttpResponseBadRequest('No se puede editar orden que no está pendiente')
        
        detalle.cantidad = int(request.POST.get('cantidad'))
        detalle.precio_unitario = Decimal(request.POST.get('precio_unitario'))
        detalle.save()
        
        # Recalcular total de la orden
        detalle.orden_compra.calcular_total()
        
        # Registrar en historial
        HistorialOrden.objects.create(
            orden=detalle.orden_compra,
            evento='editada',
            usuario=request.user,
            descripcion=f"Línea editada: {detalle.presentacion.nombre}"
        )
        
        return JsonResponse({
            'status': 'ok',
            'subtotal': str(detalle.subtotal)
        })
```

### Modal de Duplicar Orden

```python
@login_required
def duplicar_orden(request, pk):
    if request.method == 'POST':
        orden_original = get_object_or_404(OrdenCompra, id=pk)
        multiplicador = int(request.POST.get('multiplicador', 1))
        
        # Crear nueva orden
        nueva_orden = OrdenCompra.objects.create(
            proveedor=orden_original.proveedor,
            registrado_por=request.user,
            estado='pendiente'
        )
        
        # Copiar detalles
        for detalle in orden_original.detalles.all():
            DetalleCompra.objects.create(
                orden_compra=nueva_orden,
                presentacion=detalle.presentacion,
                cantidad=detalle.cantidad * multiplicador,
                precio_unitario=detalle.precio_unitario
            )
        
        # Calcular total
        nueva_orden.calcular_total()
        
        # Registrar en historial
        HistorialOrden.objects.create(
            orden=nueva_orden,
            evento='creada',
            usuario=request.user,
            descripcion=f"Duplicada de orden #{orden_original.id}"
        )
        
        return JsonResponse({
            'status': 'ok',
            'orden_id': nueva_orden.id,
            'redirect': f'/ordenes/?mostrar_orden={nueva_orden.id}'
        })
```

### Modal de Historial

```python
@login_required
def obtener_historial_orden(request, pk):
    orden = get_object_or_404(OrdenCompra, id=pk)
    historial = orden.historial.all()
    
    datos = [{
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
    } for h in historial]
    
    return JsonResponse({'historial': datos})
```

### Modal de Pago (Compra)

```python
@login_required
def guardar_pago_compra(request, compra_id):
    if request.method == 'POST':
        compra = get_object_or_404(Compra, id=compra_id)
        
        compra.numero_factura = request.POST.get('numero_factura', '')
        compra.metodo_pago = request.POST.get('metodo_pago')
        compra.estado_pago = request.POST.get('estado_pago')
        compra.monto_pagado = Decimal(request.POST.get('monto_pagado', 0))
        
        fecha_pago = request.POST.get('fecha_pago')
        if fecha_pago:
            compra.fecha_pago = parse_datetime(fecha_pago)
        
        compra.save()
        
        return JsonResponse({'status': 'ok', 'message': 'Pago registrado'})
```

---

## 🔗 URLs (urls.py)

```python
path('ordenes/<int:pk>/notas/', views.guardar_nota_orden, name='guardar_nota_orden'),
path('detalles/<int:detalle_id>/editar/', views.editar_detalle_orden, name='editar_detalle'),
path('ordenes/<int:pk>/duplicar/', views.duplicar_orden, name='duplicar_orden'),
path('ordenes/<int:pk>/historial/', views.obtener_historial_orden, name='historial_orden'),
path('compras/<int:compra_id>/pago/', views.guardar_pago_compra, name='guardar_pago'),
```

---

## 🧠 JavaScript para Conectar Modales

```javascript
// NOTAS
document.getElementById('formNotas')?.addEventListener('submit', function(e) {
    e.preventDefault();
    const ordenId = document.getElementById('ordenIdNotas').value;
    const notas = document.getElementById('notasTexto').value;
    
    fetch(`/ordenes/${ordenId}/notas/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
        body: new FormData(this)
    })
    .then(r => r.json())
    .then(d => {
        alert('Nota guardada');
        bootstrap.Modal.getInstance(document.getElementById('modalNotas')).hide();
    });
});

// EDITAR DETALLE
function abrirEditarDetalle(detalleId, producto, cantidad, precio) {
    document.getElementById('detalleId').value = detalleId;
    document.getElementById('detalleProducto').value = producto;
    document.getElementById('detalleCantidad').value = cantidad;
    document.getElementById('detallePrecio').value = precio;
    
    // Actualizar subtotal en tiempo real
    document.getElementById('detalleCantidad').addEventListener('input', actualizarSubtotal);
    document.getElementById('detallePrecio').addEventListener('input', actualizarSubtotal);
}

function actualizarSubtotal() {
    const cant = parseFloat(document.getElementById('detalleCantidad').value) || 0;
    const precio = parseFloat(document.getElementById('detallePrecio').value) || 0;
    document.getElementById('detalleSubtotal').innerText = (cant * precio).toFixed(2);
}

// DUPLICAR
function abrirDuplicarOrden(ordenId, productos) {
    document.getElementById('ordenIdDuplicar').value = ordenId;
    const lista = document.getElementById('listaDuplicados');
    lista.innerHTML = productos.map(p => 
        `<div style="padding:6px; border-bottom:1px solid rgba(77,168,218,0.1);">
            ${p.nombre} × ${p.cantidad}
        </div>`
    ).join('');
}

// HISTORIAL
function abrirHistorial(ordenId) {
    fetch(`/ordenes/${ordenId}/historial/`)
        .then(r => r.json())
        .then(d => {
            const timeline = d.historial.map(h => `
                <div style="margin-bottom:16px; padding-bottom:16px; border-bottom:1px solid rgba(77,168,218,0.1);">
                    <div style="display:flex; gap:10px;">
                        <div style="width:12px; height:12px; background:${h.color}; border-radius:50%; margin-top:2px; flex-shrink:0;"></div>
                        <div>
                            <p style="margin:0; color:#E2E8F0; font-weight:600;">${h.evento}</p>
                            <small style="color:#8FA3B1;">${h.usuario} • ${h.fecha}</small>
                            ${h.descripcion ? `<p style="margin:4px 0 0 0; color:#E2E8F0; font-size:0.9rem;">${h.descripcion}</p>` : ''}
                        </div>
                    </div>
                </div>
            `).join('');
            document.getElementById('timelineContent').innerHTML = timeline;
        });
}
```

---

## ✅ Checklist de Implementación

### Backend
- [ ] Agregar campo `notas` a `OrdenCompra`
- [ ] Crear modelo `HistorialOrden`
- [ ] Agregar campos de pago a `Compra`
- [ ] Crear 5 vistas (notas, editar, duplicar, historial, pago)
- [ ] Agregar URLs
- [ ] Hacer migraciones
- [ ] Agregar JavaScript para conectar modales

### Testing
- [ ] Probar guardar notas
- [ ] Probar editar detalle (solo si pendiente)
- [ ] Probar duplicar orden
- [ ] Probar historial se actualiza
- [ ] Probar guardar pago en Compra

---

## 💡 Mejoras Futuras

1. **Alertas automáticas** - notificar si orden lleva 5+ días sin recibirse
2. **Recepción parcial** - recibir solo parte de los productos
3. **Adjuntar archivos** - subir PDF de factura al modal de pago
4. **Aprobaciones** - si orden > cierto monto, requiere aprobación
5. **Reportes** - gasto por proveedor, métodos de pago usados, etc.

---

**Última actualización:** 2026-07-02
