from django import forms
from .models import Venta, DetalleVenta, Devolucion, DetalleDevolucion
from productos.models import Producto


class VentaForm(forms.ModelForm):
    cliente = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'cys-input form-control',
            'placeholder': 'Nombre del cliente'
        }),
        label="Cliente"
    )

    class Meta:
        model  = Venta
        fields = ['cliente']


class DetalleVentaForm(forms.ModelForm):
    cantidad = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'cys-input form-control',
            'placeholder': '0',
            'id': 'id_cantidad'
        }),
        label="Cantidad"
    )
    precio_unitario = forms.DecimalField(
        max_digits=12, decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'cys-input form-control',
            'placeholder': '0',
            'id': 'id_precio_unitario'
        }),
        label="Precio Unitario"
    )

    class Meta:
        model  = DetalleVenta
        fields = ['cantidad', 'precio_unitario']


class DevolucionForm(forms.ModelForm):
    """Formulario para registrar devoluciones"""

    class Meta:
        model = Devolucion
        fields = ['motivo', 'tipo_reembolso', 'observaciones']
        widgets = {
            'motivo': forms.RadioSelect(attrs={
                'class': 'd-none',
            }),
            'tipo_reembolso': forms.RadioSelect(attrs={
                'class': 'd-none',
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe el problema con detalle...',
            }),
        }
        labels = {
            'motivo': 'Motivo de devolución',
            'tipo_reembolso': 'Tipo de reembolso',
            'observaciones': 'Observaciones adicionales',
        }
