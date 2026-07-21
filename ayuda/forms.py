from django import forms
from .models import MensajeSoporte

class MensajeSoporteForm(forms.ModelForm):
    class Meta:
        model = MensajeSoporte
        fields = ['asunto', 'mensaje']
        widgets = {
            'asunto': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Asunto'
            }),
            'mensaje': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 4,
                'placeholder': 'Describe tu duda o problema...'
            }),
        }