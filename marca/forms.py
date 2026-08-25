from django import forms
from .models import Marca


class MarcaForm(forms.ModelForm):
    class Meta:
        model = Marca
        fields = ["nombre", "descripcion", "activo"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "cys-input"}),
            "descripcion": forms.Textarea(attrs={"class": "cys-textarea", "rows": 3}),
            "activo": forms.CheckboxInput(attrs={"class": "cys-checkbox"}),
        }