from django import forms
from django.core.exceptions import ValidationError
import re
from .models import Proveedor, ProveedorCategoria, Compra, OrdenCompra, DetalleCompra
from productos.models import Producto, Categoria, PresentacionProducto
from inventario.models import Lote

class ProveedorForm(forms.ModelForm):
    """Formulario para crear y editar proveedores con validaciones."""

    categorias = forms.ModelMultipleChoiceField(
        queryset=Categoria.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        label='Categorías que surte'
    )

    class Meta:
        model = Proveedor
        fields = ['nombre_empresa', 'nit', 'nombre_contacto', 'email', 'telefono', 'tipo_proveedor']
        widgets = {
            'nombre_empresa': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la empresa',
                'required': True,
                'maxlength': '200'
            }),
            'nit': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 123456789-1',
                'required': True,
                'maxlength': '50'
            }),
            'nombre_contacto': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Juan Pérez',
                'maxlength': '200'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@empresa.com',
                'required': True
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+56 9 1234 5678',
                'pattern': r'^\d{7,15}$'
            }),
            'tipo_proveedor': forms.Select(attrs={
                'class': 'form-select'
            }),
        }

    def clean_nombre_empresa(self):
        """Validar que el nombre sea único y válido."""
        nombre = self.cleaned_data.get('nombre_empresa')
        if not nombre or len(nombre.strip()) == 0:
            raise ValidationError('El nombre de la empresa no puede estar vacío')

        if Proveedor.objects.filter(nombre_empresa=nombre).exclude(
            pk=self.instance.pk if self.instance else None
        ).exists():
            raise ValidationError('Este nombre de empresa ya está registrado')

        return nombre.strip()

    def clean_nit(self):
        """Validar que el NIT sea único y válido."""
        nit = self.cleaned_data.get('nit')
        if not nit or len(nit.strip()) == 0:
            raise ValidationError('El NIT no puede estar vacío')

        if Proveedor.objects.filter(nit=nit).exclude(
            pk=self.instance.pk if self.instance else None
        ).exists():
            raise ValidationError('Este NIT ya está registrado en el sistema')

        return nit.strip()

    def clean_email(self):
        """Validar que el email sea único y válido."""
        email = self.cleaned_data.get('email')
        if not email:
            raise ValidationError('El email es obligatorio')

        if Proveedor.objects.filter(email=email).exclude(
            pk=self.instance.pk if self.instance else None
        ).exists():
            raise ValidationError('Este email ya está registrado en el sistema')

        return email.lower()

    def clean_telefono(self):
        """Validar formato de teléfono."""
        telefono = self.cleaned_data.get('telefono')
        if telefono and not re.match(r'^\d{7,15}$', telefono):
            raise ValidationError('Teléfono debe contener 7-15 dígitos')
        return telefono

    def clean(self):
        """Validación a nivel de formulario."""
        cleaned_data = super().clean()
        estado = cleaned_data.get('estado')
        motivo_sancion = cleaned_data.get('motivo_sancion')

        if estado == 'sancionado' and not motivo_sancion:
            raise ValidationError('Debe indicar el motivo si marca como sancionado')

        return cleaned_data

    def save(self, commit=True):
        """Guardar proveedor y sus categorías."""
        proveedor = super().save(commit=commit)
        if commit:
            categorias = self.cleaned_data.get('categorias', [])
            ProveedorCategoria.objects.filter(proveedor=proveedor).delete()
            for categoria in categorias:
                ProveedorCategoria.objects.create(proveedor=proveedor, categoria=categoria)
        return proveedor

class OrdenCompraForm(forms.ModelForm):
    """Formulario para crear órdenes de compra."""

    class Meta:
        model = OrdenCompra
        fields = ['proveedor']
        widgets = {
            'proveedor': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
        }

    def clean_proveedor(self):
        """Validar que el proveedor exista y esté activo."""
        proveedor = self.cleaned_data.get('proveedor')
        if not proveedor:
            raise ValidationError('Debe seleccionar un proveedor')
        if proveedor.estado == 'sancionado':
            raise ValidationError(f'No puedes comprar a {proveedor.nombre_empresa} (está sancionado)')
        return proveedor


class DetalleCompraForm(forms.ModelForm):
    """Formulario para agregar detalles a una orden de compra."""

    class Meta:
        model = DetalleCompra
        fields = ['presentacion', 'cantidad', 'precio_unitario']
        widgets = {
            'presentacion': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'cantidad': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'required': True,
                'type': 'number'
            }),
            'precio_unitario': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'required': True,
                'type': 'number'
            }),
        }

    def clean_cantidad(self):
        """Validar cantidad positiva."""
        cantidad = self.cleaned_data.get('cantidad')
        if not cantidad or cantidad <= 0:
            raise ValidationError('La cantidad debe ser mayor a 0')
        return cantidad

    def clean_precio_unitario(self):
        """Validar precio positivo."""
        precio = self.cleaned_data.get('precio_unitario')
        if precio is None or precio <= 0:
            raise ValidationError('El precio debe ser mayor a 0')
        return precio

    def clean(self):
        """Validaciones generales."""
        cleaned_data = super().clean()
        presentacion = cleaned_data.get('presentacion')
        if not presentacion:
            raise ValidationError('Debe seleccionar una presentación')
        return cleaned_data


class LoteForm(forms.ModelForm):
    class Meta:
        model = Lote
        fields = ['numero_lote', 'presentacion', 'stock_actual', 'costo_unitario', 'fecha_vencimiento']
        widgets = {
            'numero_lote': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: LOTE-2024-001'
            }),
            'presentacion': forms.Select(attrs={
                'class': 'form-select'
            }),
            'stock_actual': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'costo_unitario': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'fecha_vencimiento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'detalle_compra': forms.Select(attrs={
                'class': 'form-select'
            }),
        }


class CompraForm(forms.ModelForm):
    """Formulario para registrar compras a proveedores (heredado)"""
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.all(),
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'selectProducto'
        }),
        label='Selecciona Producto'
    )

    cantidad = forms.IntegerField(
        required=True,
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 10',
            'id': 'inputCantidad'
        }),
        label='Cantidad'
    )

    precio_unitario = forms.DecimalField(
        required=False,
        decimal_places=0,
        max_digits=10,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 15000',
            'id': 'inputPrecio',
            'step': '1000',
            'title': 'Precio en pesos colombianos (COP)'
        }),
        label='Precio Unitario en COP (Opcional)'
    )

    lote = forms.ModelChoiceField(
        queryset=Lote.objects.all(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'selectLote'
        }),
        label='Lote (Opcional)'
    )

    class Meta:
        model = Compra
        fields = ['producto', 'cantidad', 'precio_unitario', 'lote']
