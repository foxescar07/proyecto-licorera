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
    motivo = forms.ChoiceField(
        choices=Devolucion.MOTIVO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Motivo de devolución'
    )
    tipo_reembolso = forms.ChoiceField(
        choices=Devolucion.REEMBOLSO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Tipo de reembolso'
    )
    observaciones = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe el problema con detalle...'}),
        label='Observaciones adicionales',
        required=False
    )
    restaurar_stock = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Restaurar stock',
        required=False
    )
    tiene_comprobante = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Tiene comprobante',
        required=False
    )

    class Meta:
        model  = Devolucion
        fields = ['motivo', 'tipo_reembolso', 'observaciones', 'restaurar_stock', 'tiene_comprobante']