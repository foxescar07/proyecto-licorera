from django import forms
from inventario.models import Lote


class LoteForm(forms.ModelForm):
    class Meta:
        model = Lote
        fields = [
            'numero_lote',
            'presentacion',
            'stock_actual',
            'costo_unitario',
            'fecha_vencimiento',
        ]
        widgets = {
            'numero_lote': forms.TextInput(attrs={'class': 'form-control'}),
            'presentacion': forms.Select(attrs={'class': 'form-select'}),
            'stock_actual': forms.NumberInput(attrs={'class': 'form-control'}),
            'costo_unitario': forms.NumberInput(attrs={'class': 'form-control'}),
            'fecha_vencimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }