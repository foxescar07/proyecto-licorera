# Guía de Implementación: Mejoras en Órdenes de Compra

## ✅ Cambios Realizados en Frontend

### 1. **Alineación de Tabla (ARREGLADO)**
- Se agregaron estilos CSS específicos para `.cys-td`, `.cys-td--muted`, `.cys-td--bold`
- Se definió alineación correcta por columna:
  - Columna 1 (#): Centrada
  - Columna 2 (Proveedor): Izquierda
  - Columna 3 (Fecha): Izquierda
  - Columna 4 (Estado): Centrada
  - Columna 5 (Pago): Centrada ← **NUEVA**
  - Columna 6 (Total): Derecha
  - Columna 7 (Acciones): Centrada

### 2. **Exportación de Datos**
Se agregaron 3 opciones de exportación:
- **Excel** (`exportarExcel()`) - genera .xlsx con formato
- **PDF** (`exportarPDF()`) - genera .pdf en orientación landscape
- **Imprimir** (`window.print()`) - abre diálogo de impresión

**Librerías agregadas:**
- XLSX (librería CDN) para Excel
- html2pdf (librería CDN) para PDF

### 3. **Método y Estado de Pago**
Se agregó una nueva columna "Pago" con:
- Badge visual del estado de pago (Pagada/Pago Parcial/Pendiente)
- Filtro en la parte superior para filtrar por estado de pago
- Campo "Método de Pago" en el modal de nueva orden (dropdown)
- Sección "Información de Pago" en el modal de detalle

## 🔧 Lo que Necesitas Implementar en Django

### 1. **Modelo (models.py)**

Agregar campos a tu modelo `OrdenCompra`:

```python
class OrdenCompra(models.Model):
    # ... campos existentes ...
    
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
    
    fecha_pago = models.DateTimeField(null=True, blank=True)  # Opcional: cuándo se pagó
    monto_pagado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0  # Para pagos parciales
    )
```

**Pasos:**
1. Agrega estos campos al modelo
2. Ejecuta: `python manage.py makemigrations`
3. Ejecuta: `python manage.py migrate`

### 2. **Formulario (forms.py)**

Agregar campos al formulario de creación/edición:

```python
class OrdenCompraForm(forms.ModelForm):
    class Meta:
        model = OrdenCompra
        fields = [
            'proveedor',
            'metodo_pago',
            'estado_pago',
            # ... otros campos existentes ...
        ]
        widgets = {
            'metodo_pago': forms.Select(attrs={
                'class': 'form-select',
                'style': 'background: #02224a !important; color: #E2E8F0 !important;'
            }),
            'estado_pago': forms.Select(attrs={
                'class': 'form-select',
                'style': 'background: #02224a !important; color: #E2E8F0 !important;'
            }),
        }
```

### 3. **Vista (views.py)**

Actualiza tu vista para:

1. **Pasar datos de pago al contexto:**
```python
def listar_ordenes(request):
    ordenes = OrdenCompra.objects.all()
    
    # FILTRO POR ESTADO DE PAGO (nuevo)
    estado_pago = request.GET.get('estado_pago')
    if estado_pago:
        ordenes = ordenes.filter(estado_pago=estado_pago)
    
    context = {
        'ordenes': ordenes,
        # ... otros datos existentes ...
    }
    return render(request, 'proveedores/orden_compra.html', context)
```

2. **En crear_orden():**
```python
def crear_orden(request):
    if request.method == 'POST':
        form = OrdenCompraForm(request.POST)
        if form.is_valid():
            orden = form.save(commit=False)
            orden.registrado_por = request.user
            orden.metodo_pago = request.POST.get('metodo_pago', 'transferencia')
            orden.estado_pago = 'pendiente'  # Por defecto
            orden.save()
            # ... resto del código ...
```

### 4. **Plantilla Context (lo que ya está en orden_compra.html)**

Asegúrate que tu vista pase estos datos en `context`:
```python
context = {
    'ordenes': ordenes,
    'total_ordenes': OrdenCompra.objects.count(),
    'ordenes_pendientes': OrdenCompra.objects.filter(estado='pendiente').count(),
    'ordenes_confirmadas': OrdenCompra.objects.filter(estado='confirmada').count(),
    'ordenes_recibidas': OrdenCompra.objects.filter(estado='recibida').count(),
}
```

## 📋 Funcionalidades Listas pero sin Backend

### Exportación a Excel/PDF
- ✅ Botones en interfaz
- ✅ JavaScript para generar archivos
- ❌ **No necesita backend** - funciona completamente en el cliente

### Filtro por Estado de Pago
- ✅ Dropdown en interfaz
- ✅ Función `aplicarFiltro()`
- ✅ Parámetro URL `?estado_pago=pagada`
- ⚠️ **Necesita:** Lógica de filtro en `listar_ordenes()` (views.py)

### Campo Método de Pago
- ✅ Dropdown en modal
- ✅ Visualización en modal de detalle
- ⚠️ **Necesita:** Campo en modelo + formulario

### Badge de Estado de Pago
- ✅ Estilos CSS
- ✅ Condicionales en template
- ⚠️ **Necesita:** Campo `estado_pago` en modelo

## 🧪 Cómo Testear (sin implementar backend aún)

1. Abre `orden_compra.html` en el navegador
2. Los botones de exportación funcionarán de inmediato:
   - Haz clic en Excel/PDF/Imprimir
   - Se descargará/imprimirá la tabla actual
3. El filtro de pago no hará nada hasta que agregues la lógica en views.py
4. El campo de método de pago se mostrará pero no se guardará hasta que agregues el campo en modelo

## 📦 Resumen de Tareas Pendientes

- [ ] Agregar campos a modelo `OrdenCompra` (metodo_pago, estado_pago, etc)
- [ ] Ejecutar migraciones Django
- [ ] Actualizar formulario con nuevos campos
- [ ] Implementar filtro por estado de pago en vista `listar_ordenes()`
- [ ] Guardar método de pago en `crear_orden()`
- [ ] (Opcional) Crear vista para cambiar estado de pago
- [ ] (Opcional) Agregar historial de pagos

## 💡 Mejoras Futuras Sugeridas

1. **Historial de cambios de pago** - registro de cuándo se pagó/cambió estado
2. **Recordatorio automático** - notificar si orden sin pagar después de X días
3. **Reporte de Deuda** - monto pendiente por proveedor
4. **Estado de pago por línea** - si parcialmente recibida, controlar pago por producto
5. **Integración contable** - crear asientos automáticos cuando se marca como pagada
