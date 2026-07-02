# 🛠️ Guía: Implementar Método y Estado de Pago en Compra

## 📍 Ubicación: Modelo `Compra`

El método de pago debe ir en el modelo **`Compra`** (no en `OrdenCompra`).

**Razón:** El método de pago se define cuando **se recibe efectivamente la factura/compra**, no cuando se crea la orden inicial.

---

## ✅ Cambios a Realizar

### 1. **Actualizar Modelo `Compra` (proveedores/models.py)**

Agreggar estos campos a la clase `Compra`:

```python
class Compra(models.Model):
    """Modelo para registrar compras a proveedores."""

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
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, ...)
    producto = models.ForeignKey('productos.Producto', on_delete=models.CASCADE, ...)
    cantidad = models.IntegerField(...)
    precio_unitario = models.DecimalField(...)
    fecha_registro = models.DateTimeField(auto_now_add=True, ...)
    recibida = models.BooleanField(default=False, ...)
    
    # ✅ AGREGAR ESTOS CAMPOS:
    metodo_pago = models.CharField(
        max_length=20,
        choices=METODO_PAGO_CHOICES,
        null=True,
        blank=True,
        default='transferencia',
        help_text="Método de pago utilizado"
    )
    
    estado_pago = models.CharField(
        max_length=20,
        choices=ESTADO_PAGO_CHOICES,
        default='pendiente',
        help_text="Estado del pago"
    )
    
    fecha_pago = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha en que se efectuó el pago"
    )
    
    monto_pagado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Monto pagado (útil para pagos parciales)"
    )
    
    numero_factura = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Número de factura del proveedor"
    )

    class Meta:
        ordering = ['-fecha_registro']
        verbose_name = 'Compra'
        verbose_name_plural = 'Compras'

    def __str__(self):
        return f"{self.proveedor.nombre_empresa} → {self.producto.nombre} ({self.cantidad} uds)"

    @property
    def total(self):
        """Calcula el total de la compra."""
        if self.precio_unitario:
            return self.cantidad * self.precio_unitario
        return None
```

### 2. **Ejecutar Migraciones**

```bash
python manage.py makemigrations
python manage.py migrate
```

### 3. **Actualizar Admin (opcional pero recomendado)**

En `proveedores/admin.py`:

```python
from django.contrib import admin
from .models import Compra

@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ('id', 'proveedor', 'producto', 'cantidad', 'metodo_pago', 'estado_pago', 'fecha_registro')
    list_filter = ('metodo_pago', 'estado_pago', 'fecha_registro', 'proveedor')
    search_fields = ('proveedor__nombre_empresa', 'producto__nombre', 'numero_factura')
    readonly_fields = ('fecha_registro',)
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('proveedor', 'producto', 'cantidad', 'precio_unitario', 'numero_factura')
        }),
        ('Recepción', {
            'fields': ('lote', 'recibida', 'fecha_registro')
        }),
        ('Pago', {
            'fields': ('metodo_pago', 'estado_pago', 'monto_pagado', 'fecha_pago')
        }),
    )
```

---

## 📝 Opciones por Campo

### `metodo_pago`
- Transferencia Bancaria
- Efectivo
- Cheque
- Tarjeta de Crédito
- Crédito a 30 días
- Otro

### `estado_pago`
- **Pendiente de Pago** - Factura recibida, aún no pagada
- **Pagada** - Factura completamente pagada
- **Pago Parcial** - Se pagó parte, falta el resto

---

## 🎯 Flujo Esperado

```
1. Se crea OrdenCompra (sin info de pago)
   ↓
2. Se recibe la orden → se crea Compra
   ↓
3. En Compra se ingresa:
   - Método de Pago
   - Estado de Pago (inicialmente: pendiente)
   ↓
4. Cuando se paga:
   - Se actualiza estado_pago a "pagada" o "parcial"
   - Se registra fecha_pago
   - Se registra monto_pagado
```

---

## 💻 Template / Vistas

Cuando tengas que mostrar/editar compras en una vista, podrías hacer algo como:

```django
<!-- Mostrar estado de pago -->
{% if compra.estado_pago == 'pagada' %}
    <span class="badge bg-success">✓ Pagada</span>
{% elif compra.estado_pago == 'parcial' %}
    <span class="badge bg-warning">⊘ Pago Parcial</span>
{% else %}
    <span class="badge bg-secondary">⏳ Pendiente</span>
{% endif %}

<!-- Mostrar método de pago -->
{{ compra.get_metodo_pago_display }}

<!-- Monto pagado -->
${{ compra.monto_pagado|floatformat:0 }}
```

---

## 🔍 Consultas Útiles

```python
# Obtener todas las compras pendientes de pago
Compra.objects.filter(estado_pago='pendiente')

# Obtener total pendiente por proveedor
from django.db.models import Sum, F, DecimalField
from django.db.models import ExpressionWrapper

Compra.objects.filter(
    estado_pago__in=['pendiente', 'parcial']
).values('proveedor__nombre_empresa').annotate(
    pendiente=ExpressionWrapper(
        F('cantidad') * F('precio_unitario') - F('monto_pagado'),
        output_field=DecimalField()
    )
)

# Obtener compras pagadas por transferencia
Compra.objects.filter(estado_pago='pagada', metodo_pago='transferencia')
```

---

## ✨ Mejoras Futuras (Opcionales)

1. **Historial de cambios** - registrar quién y cuándo cambió estado de pago
2. **Notificaciones** - alertar si hay compras pendientes hace 30+ días
3. **Reportes** - deuda por proveedor, dinero a pagar mensualmente
4. **Asiento contable automático** - crear asiento en contabilidad al marcar pagada
5. **Documento adjunto** - guardar PDF/imagen de la factura

---

## 📋 Checklist

- [ ] Agregar campos a modelo `Compra`
- [ ] Ejecutar `makemigrations` y `migrate`
- [ ] (Opcional) Actualizar admin
- [ ] Crear vista para ver/editar compras
- [ ] Crear template para mostrar estado de pago
- [ ] (Futuro) Agregar filtros/reportes por método de pago

---

**Última actualización:** 2026-07-02
