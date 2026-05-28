from django import forms
from .models import Producto, Categoria, PresentacionProducto
from inventario.models import AgendaInventario


class ProductoRegistroForm(forms.ModelForm):
    class Meta:
        model  = Producto
        fields = ['codigo', 'nombre', 'categoria']
        widgets = {
            'codigo': forms.TextInput(attrs={
                'class':       'np-input',
                'placeholder': 'Ej: CRV-001',
            }),
            'nombre': forms.TextInput(attrs={
                'class':       'np-input',
                'placeholder': 'Ej: Cerveza Club Colombia',
            }),
            'categoria': forms.Select(attrs={
                'class': 'np-input',
            }),
        }


class ProductoForm(forms.ModelForm):
    class Meta:
        model  = Producto
        fields = ['codigo', 'nombre', 'descripcion', 'precio_unitario', 'unidad', 'categoria']
        widgets = {
            'codigo': forms.TextInput(attrs={
                'class':       'gp-input',
                'placeholder': 'Ej: CRV-001',
            }),
            'nombre': forms.TextInput(attrs={
                'class':       'gp-input',
                'placeholder': 'Ej: Cerveza Club Colombia',
            }),
            'descripcion': forms.Textarea(attrs={
                'class':       'gp-input',
                'rows':        2,
                'placeholder': 'Descripción opcional…',
            }),
            'precio_unitario': forms.NumberInput(attrs={
                'class':       'gp-input',
                'placeholder': 'Ej: 2500',
                'step':        '0.01',
            }),
            'unidad': forms.TextInput(attrs={
                'class':       'gp-input',
                'placeholder': 'Ej: UND, KG, L',
            }),
            'categoria': forms.Select(attrs={
                'class': 'gp-input',
            }),
        }


class PresentacionForm(forms.ModelForm):
    class Meta:
        model  = PresentacionProducto
        fields = ['nombre', 'unidades', 'precio']
        widgets = {
            'nombre':   forms.TextInput(attrs={'class': 'gp-input', 'placeholder': 'Ej: Six-pack'}),
            'unidades': forms.NumberInput(attrs={'class': 'gp-input', 'min': '1'}),
            'precio':   forms.NumberInput(attrs={'class': 'gp-input', 'min': '0', 'step': '0.01'}),
        }


class AgendaInventarioForm(forms.ModelForm):
    class Meta:
        model  = AgendaInventario
        fields = ['titulo', 'descripcion', 'fecha_programada', 'estado']
        widgets = {
            'titulo':           forms.TextInput(attrs={'class': 'gp-input'}),
            'descripcion':      forms.Textarea(attrs={'class': 'gp-input', 'rows': 2}),
            'fecha_programada': forms.DateTimeInput(attrs={'class': 'gp-input', 'type': 'datetime-local'}),
            'estado':           forms.Select(attrs={'class': 'gp-input'}),
        }