from django import forms
from django.core.exceptions import ValidationError

from .models import (
    Venta,
    DetalleVenta,
    Devolucion,
    DetalleDevolucion,
)


# ════════════════════════════════════════
# VENTAS
# ════════════════════════════════════════


# ════════════════════════════════════════
# DEVOLUCIONES
# ════════════════════════════════════════

class DevolucionForm(forms.ModelForm):

    class Meta:
        model  = Devolucion
        fields = [
            'motivo',
            'tipo_reembolso',
            'observaciones',
        ]
        widgets = {
            'motivo': forms.Select(attrs={
                'class':    'form-select form-select-dark',
                'required': True,
            }),
            'tipo_reembolso': forms.Select(attrs={
                'class':    'form-select form-select-dark',
                'required': True,
            }),
            'observaciones': forms.Textarea(attrs={
                'class':       'form-control form-control-dark',
                'rows':        3,
                'placeholder': 'Observaciones adicionales (opcional)',
            }),
        }

    def clean_motivo(self):
        motivo = self.cleaned_data.get('motivo')
        if not motivo:
            raise ValidationError('Debes seleccionar un motivo de devolución.')
        return motivo

    def clean_tipo_reembolso(self):
        tipo_reembolso = self.cleaned_data.get('tipo_reembolso')
        if not tipo_reembolso:
            raise ValidationError('Debes seleccionar un tipo de reembolso.')
        return tipo_reembolso


class DetalleDevolucionForm(forms.ModelForm):

    class Meta:
        model  = DetalleDevolucion
        fields = '__all__'

    def clean(self):
        cleaned_data  = super().clean()
        detalle_venta = cleaned_data.get('detalle_venta')

        ya_devuelto = DetalleDevolucion.objects.filter(
            detalle_venta=detalle_venta
        ).exists()

        if ya_devuelto:
            raise forms.ValidationError(
                'Este producto ya fue devuelto.'
            )

        return cleaned_data