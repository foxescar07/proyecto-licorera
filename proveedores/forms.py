from django import forms
from django.core.exceptions import ValidationError
import re
from decimal import Decimal
from .models import Proveedor, ProveedorCategoria, Compra, DetalleCompra
from productos.models import Producto, Categoria, PresentacionProducto
from inventario.models import Lote


class ProveedorForm(forms.ModelForm):
    """Formulario para crear y editar proveedores con validaciones."""

    categorias = forms.ModelMultipleChoiceField(
        queryset=Categoria.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        label='Categorías que surte'
    )

    class Meta:
        model = Proveedor
        fields = ['nombre_empresa', 'nit', 'email', 'telefono']
        widgets = {
            'nombre_empresa': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la empresa',
                'required': True,
                'maxlength': '200'
            }),
            'nit': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 123456789-1',
                'maxlength': '50'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@empresa.com',
                'required': True
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 3001234567',
                'pattern': r'^\d{7,15}$'
            }),
        }

    def clean_nombre_empresa(self):
        """Validar que el nombre sea único y válido."""
        nombre = self.cleaned_data.get('nombre_empresa')
        if not nombre or len(nombre.strip()) == 0:
            raise ValidationError('El nombre de la empresa no puede estar vacío')

        if Proveedor.objects.filter(nombre_empresa=nombre).exclude(
            pk=self.instance.pk if self.instance else None
        ).exists():
            raise ValidationError('Este nombre de empresa ya está registrado')

        return nombre.strip()

    def clean_nit(self):
        """Validar que el NIT sea obligatorio y único."""
        nit = self.cleaned_data.get('nit')

        # Validar que no esté vacío
        if not nit or len(str(nit).strip()) == 0:
            raise ValidationError('El NIT es obligatorio')

        # Verificar que sea único
        if Proveedor.objects.filter(nit=nit).exclude(
            pk=self.instance.pk if self.instance else None
        ).exists():
            raise ValidationError('Este NIT ya está registrado')

        return nit.strip() if isinstance(nit, str) else nit

    def clean_email(self):
        """Validar que el email sea único y válido."""
        email = self.cleaned_data.get('email')
        if not email:
            raise ValidationError('El email es obligatorio')

        if Proveedor.objects.filter(email=email).exclude(
            pk=self.instance.pk if self.instance else None
        ).exists():
            raise ValidationError('Este email ya está registrado en el sistema')

        return email.lower()

    def clean_telefono(self):
        """Validar que el teléfono sea obligatorio, con formato correcto y único."""
        telefono = self.cleaned_data.get('telefono')

        # Validar que no esté vacío
        if not telefono or len(str(telefono).strip()) == 0:
            raise ValidationError('El teléfono es obligatorio')

        # Validar formato
        if not re.match(r'^\d{7,15}$', str(telefono)):
            raise ValidationError('Teléfono debe contener 7-15 dígitos')

        # Validar unicidad
        if Proveedor.objects.filter(telefono=telefono).exclude(
            pk=self.instance.pk if self.instance else None
        ).exists():
            raise ValidationError('Este teléfono ya está registrado')

        return telefono

    def clean(self):
        """Validación a nivel de formulario."""
        cleaned_data = super().clean()
        return cleaned_data

    def save(self, commit=True):
        """Guardar proveedor y sus categorías."""
        proveedor = super().save(commit=commit)
        if commit:
            categorias = self.cleaned_data.get('categorias', [])
            ProveedorCategoria.objects.filter(proveedor=proveedor).delete()
            for categoria in categorias:
                ProveedorCategoria.objects.create(proveedor=proveedor, categoria=categoria)
        return proveedor


class DetalleCompraForm(forms.ModelForm):
    """Formulario para agregar detalles a una orden de compra."""

    class Meta:
        model = DetalleCompra
        fields = ['presentacion', 'cantidad', 'precio_unitario']
        widgets = {
            'presentacion': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'cantidad': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'required': True,
                'type': 'number'
            }),
            'precio_unitario': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'required': True,
                'type': 'number'
            }),
        }

    def clean_cantidad(self):
        """Validar cantidad positiva."""
        cantidad = self.cleaned_data.get('cantidad')
        if not cantidad or cantidad <= 0:
            raise ValidationError('La cantidad debe ser mayor a 0')
        return cantidad

    def clean_precio_unitario(self):
        """Validar precio positivo."""
        precio = self.cleaned_data.get('precio_unitario')
        if precio is None or precio <= 0:
            raise ValidationError('El precio debe ser mayor a 0')
        return precio

    def clean(self):
        """Validaciones generales."""
        cleaned_data = super().clean()
        presentacion = cleaned_data.get('presentacion')
        if not presentacion:
            raise ValidationError('Debe seleccionar una presentación')
        return cleaned_data


class LoteForm(forms.ModelForm):
    class Meta:
        model = Lote
        fields = ['numero_lote', 'presentacion', 'stock_actual', 'costo_unitario', 'fecha_vencimiento']
        widgets = {
            'numero_lote': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: LOTE-2024-001'
            }),
            'presentacion': forms.Select(attrs={
                'class': 'form-select'
            }),
            'stock_actual': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'costo_unitario': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'fecha_vencimiento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'detalle_compra': forms.Select(attrs={
                'class': 'form-select'
            }),
        }


class NuevaCompraForm(forms.Form):
    """Formulario para registrar una nueva compra rápida."""

    producto = forms.ModelChoiceField(
        queryset=Producto.objects.all(),
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': True
        }),
        label='Producto'
    )

    lote = forms.ModelChoiceField(
        queryset=Lote.objects.all(),
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': True
        }),
        label='Lote',
        required=False
    )

    cantidad = forms.IntegerField(
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'required': True,
            'type': 'number'
        }),
        label='Cantidad',
        min_value=1
    )

    precio_unitario = forms.DecimalField(
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0.01',
            'required': True,
            'type': 'number'
        }),
        label='Precio Unitario',
        decimal_places=2,
        min_value=0.01
    )


class CompraForm(forms.ModelForm):
    """Formulario para registrar compras a proveedores."""

    class Meta:
        model = Compra
        fields = ['proveedor', 'valor', 'saldo', 'motivo_pago', 'observacion']
        widgets = {
            'proveedor': forms.Select(attrs={
                'class': 'form-select'
            }),
            'valor': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Valor total'
            }),
            'saldo': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Saldo pendiente'
            }),
            'motivo_pago': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Motivo o nota del pago'
            }),
            'observacion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observaciones adicionales'
            }),
        }


class DevolucionProveedorForm(forms.Form):
    """Formulario para registrar una devolución a proveedor."""

    proveedor = forms.ModelChoiceField(
        queryset=None,  # Se asigna en __init__
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': True,
            'id': 'id_devprov_proveedor',
        }),
        label='Proveedor',
    )

    compra = forms.ModelChoiceField(
        queryset=Compra.objects.none(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_devprov_compra',
        }),
        label='Compra original (opcional)',
        help_text='Selecciona la compra a la que pertenece la devolución',
    )

    motivo = forms.ChoiceField(
        choices=[
            ('defectuoso',     'Producto defectuoso'),
            ('equivocado',     'Producto equivocado'),
            ('vencido',        'Producto vencido'),
            ('empaque_danado', 'Empaque dañado'),
            ('exceso',         'Exceso de pedido'),
            ('otro',           'Otro motivo'),
        ],
        widget=forms.Select(attrs={'class': 'form-select', 'required': True}),
        label='Motivo',
        initial='otro',
    )

    tipo_resolucion = forms.ChoiceField(
        choices=[
            ('nota_credito', 'Nota crédito'),
            ('reembolso',    'Reembolso en efectivo'),
            ('reposicion',   'Reposición de producto'),
        ],
        widget=forms.Select(attrs={'class': 'form-select', 'required': True}),
        label='Tipo de resolución',
        initial='nota_credito',
    )

    observaciones = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Observaciones adicionales sobre la devolución',
        }),
        label='Observaciones',
    )

    # Campos del detalle (un solo producto por vez vía modal)
    presentacion = forms.ModelChoiceField(
        queryset=PresentacionProducto.objects.select_related('producto').all(),
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': True,
            'id': 'id_devprov_presentacion',
        }),
        label='Producto / Presentación',
    )

    cantidad = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'required': True,
            'id': 'id_devprov_cantidad',
        }),
        label='Cantidad',
    )

    precio_unitario = forms.DecimalField(
        min_value=Decimal('0.01'),
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0.01',
            'required': True,
            'id': 'id_devprov_precio',
        }),
        label='Precio unitario de compra',
    )

    def __init__(self, *args, **kwargs):
        from .models import Proveedor
        super().__init__(*args, **kwargs)
        self.fields['proveedor'].queryset = Proveedor.objects.filter(estado='activo').order_by('nombre_empresa')

    def clean_cantidad(self):
        cant = self.cleaned_data.get('cantidad')
        if cant is None or cant <= 0:
            raise ValidationError('La cantidad debe ser mayor a 0')
        return cant

    def clean_precio_unitario(self):
        precio = self.cleaned_data.get('precio_unitario')
        if precio is None or precio <= Decimal('0'):
            raise ValidationError('El precio debe ser mayor a 0')
        return precio

