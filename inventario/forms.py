from django import forms
from .models import Lote, MovimientoInventario

class LoteForm(forms.ModelForm):
    class Meta:
        model = Lote
        fields = [
            'numero_lote',
            'presentacion',
            'stock_actual',
            'costo_unitario',
            'fecha_vencimiento'
        ]
        widgets = {
            'numero_lote': forms.TextInput(attrs={'class': 'form-control'}),
            'presentacion': forms.Select(attrs={'class': 'form-select'}),
            'stock_actual': forms.NumberInput(attrs={'class': 'form-control'}),
            'costo_unitario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'fecha_vencimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

class MovimientoInventarioForm(forms.ModelForm):
    class Meta:
        model = MovimientoInventario
        fields = [
            'inventario',
            'lote',
            'tipo',
            'cantidad',
            'motivo',
        ]
        widgets = {
            'inventario': forms.Select(attrs={'class': 'form-select'}),
            'lote': forms.Select(attrs={'class': 'form-select'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control'}),
            'motivo': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_cantidad(self):
        cantidad = self.cleaned_data['cantidad']
        if cantidad <= 0:
            raise forms.ValidationError('La cantidad debe ser mayor a 0.')
        return cantidad