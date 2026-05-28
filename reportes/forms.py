from django import forms

class FiltroReporteForm(forms.Form):
    fecha_inicio = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'inv-input'}),
        required=True,
        label="Desde"
    )
    fecha_fin = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'inv-input'}),
        required=True,
        label="Hasta"
    )
    tipo_reporte = forms.ChoiceField(
        choices=[('general', 'General'), ('entradas', 'Solo Entradas'), ('salidas', 'Solo Salidas')],
        widget=forms.Select(attrs={'class': 'inv-input'}),
        label="Tipo de Movimiento"
    )