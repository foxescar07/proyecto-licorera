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
            'motivo', 'observaciones', 'restaurar_stock', 'tiene_comprobante'
        ]
        widgets = {
            'motivo': forms.Select(attrs={'class': 'form-select'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe el problema con detalle...'}),
            'restaurar_stock': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tiene_comprobante': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'motivo': 'Motivo de devolución',
            'observaciones': 'Observaciones adicionales',
            'restaurar_stock': 'Restaurar stock',
            'tiene_comprobante': 'Tiene comprobante',
        }