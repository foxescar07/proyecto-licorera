from django import forms
from .models import Proveedor, ProveedorCategoria, Compra, OrdenCompra, DetalleCompra
from productos.models import Producto, Categoria, PresentacionProducto
from inventario.models import Lote

class ProveedorForm(forms.ModelForm):
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
        fields = ['nombre_empresa', 'email', 'telefono', 'tipo_proveedor', 'estado']
        widgets = {
            'nombre_empresa': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la empresa',
                'required': True
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@empresa.com',
                'required': True
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+56 9 1234 5678'
            }),
            'tipo_proveedor': forms.Select(attrs={
                'class': 'form-select'
            }),
            'estado': forms.Select(attrs={
                'class': 'form-select'
            }),
        }

    def save(self, commit=True):
        proveedor = super().save(commit=commit)
        if commit:
            categorias = self.cleaned_data.get('categorias', [])
            ProveedorCategoria.objects.filter(proveedor=proveedor).delete()
            for categoria in categorias:
                ProveedorCategoria.objects.create(proveedor=proveedor, categoria=categoria)
        return proveedor

class OrdenCompraForm(forms.ModelForm):
    class Meta:
        model = OrdenCompra
        fields = ['proveedor', 'estado']
        widgets = {
            'proveedor': forms.Select(attrs={
                'class': 'form-select'
            }),
            'estado': forms.Select(attrs={
                'class': 'form-select'
            }),
        }


class DetalleCompraForm(forms.ModelForm):
    class Meta:
        model = DetalleCompra
        fields = ['presentacion', 'cantidad', 'precio_unitario']
        widgets = {
            'presentacion': forms.Select(attrs={
                'class': 'form-select',
                'queryset': PresentacionProducto.objects.all()
            }),
            'cantidad': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            }),
            'precio_unitario': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
        }


class LoteForm(forms.ModelForm):
    class Meta:
        model = Lote
        fields = ['numero_lote', 'presentacion', 'stock_actual', 'costo_unitario', 'fecha_vencimiento', 'detalle_compra']
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
        decimal_places=2,
        max_digits=10,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '15000',
            'id': 'inputPrecio',
            'step': '1'
        }),
        label='Precio Unitario (Opcional)'
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
