from django import forms # type: ignore
from .models import Venta, DetalleVenta, Devolucion
from productos.models import Producto


class VentaForm(forms.ModelForm):
    cliente = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'cys-input form-control', 'placeholder': 'Nombre del cliente'}),
        label="Cliente"
    )
    class Meta:
        model  = Venta
        fields = ['cliente']


class DetalleVentaForm(forms.ModelForm):
    cantidad = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'cys-input form-control', 'placeholder': '0', 'id': 'id_cantidad'}),
        label="Cantidad"
    )
    precio_unitario = forms.DecimalField(
        max_digits=12, decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'cys-input form-control', 'placeholder': '0', 'id': 'id_precio_unitario'}),
        label="Precio Unitario"
    )
    class Meta:
        model  = DetalleVenta
        fields = ['cantidad', 'precio_unitario']


class DevolucionForm(forms.ModelForm):
    class Meta:
        model = Devolucion
        fields = [
            'motivo', 'tipo_reembolso', 'observaciones', 
            'producto_cambio', 'cantidad_cambio', 'metodo_pago_devolucion'
        ]
        widgets = {
            'motivo': forms.RadioSelect(attrs={'class': 'd-none'}),
            'tipo_reembolso': forms.RadioSelect(attrs={'class': 'd-none'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe el problema con detalle...'}),
            'producto_cambio': forms.Select(attrs={'class': 'form-select dev-select-premium'}),
            'cantidad_cambio': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1', 'min': '1'}),
            'metodo_pago_devolucion': forms.Select(attrs={'class': 'form-select dev-select-premium'}),
        }
        labels = {
            'motivo': 'Motivo de devolución', 'tipo_reembolso': 'Tipo de reembolso', 'observaciones': 'Observaciones adicionales',
            'producto_cambio': 'Producto de reemplazo', 'cantidad_cambio': 'Cantidad de cambio', 'metodo_pago_devolucion': 'Método de reembolso',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['producto_cambio'].required = False
        self.fields['cantidad_cambio'].required = False
        self.fields['metodo_pago_devolucion'].required = False
        self.fields['metodo_pago_devolucion'].choices = [('', '-- Selecciona método --')] + list(
            self.instance._meta.get_field('metodo_pago_devolucion').choices
        )