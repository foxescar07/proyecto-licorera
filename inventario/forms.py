from django import forms

from .models import AgendaInventario, Hallazgo, Lote, MovimientoInventario


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


class AgendaInventarioForm(forms.ModelForm):
    class Meta:
        model = AgendaInventario
        fields = [
            'titulo',
            'descripcion',
            'fecha',
            'tipo',
            'estado',
            'responsable',
        ]
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'fecha': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'tipo': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'responsable': forms.Select(attrs={'class': 'form-select'}),
        }


class HallazgoForm(forms.ModelForm):
    class Meta:
        model = Hallazgo
        fields = [
            'producto',
            'cantidad_sistema',
            'cantidad_fisica',
            'sesion_conteo',
            'resultado_inventario',
            'observaciones',
        ]
        widgets = {
            'producto': forms.Select(attrs={'class': 'form-select'}),
            'cantidad_sistema': forms.NumberInput(attrs={'class': 'form-control'}),
            'cantidad_fisica': forms.NumberInput(attrs={'class': 'form-control'}),
            'sesion_conteo': forms.TextInput(attrs={'class': 'form-control'}),
            'resultado_inventario': forms.TextInput(attrs={'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }