from django import forms
from .models import Proveedor, Compra
from productos.models import Producto
from inventario.models import Lote

class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['nombre_empresa', 'nombre_contacto', 'email', 'telefono', 'categorias_surtidas']
        widgets = {
            'nombre_empresa': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la empresa',
                'required': True
            }),
            'nombre_contacto': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Responsable/Contacto',
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
            'categorias_surtidas': forms.CheckboxSelectMultiple(attrs={
                'class': 'form-check-input'
            }),
        }

class CompraForm(forms.ModelForm):
    """Formulario para registrar compras a proveedores"""
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
