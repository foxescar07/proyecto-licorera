from django import forms
from django.contrib.auth.models import User
from .models import Perfil
import re


def validar_clave_segura(clave):
    if len(clave) < 6:
        raise forms.ValidationError('La contraseña debe tener al menos 6 caracteres.')
    if len(re.findall(r'\d', clave)) < 2:
        raise forms.ValidationError('La contraseña debe contener al menos 2 números.')
    if not re.search(r'[A-Z]', clave):
        raise forms.ValidationError('La contraseña debe contener al menos 1 letra mayúscula.')


class UsuarioForm(forms.Form):

    # ── Campos de User ───────────────────────────────────────────
    nombre = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control cys-input',
            'placeholder': 'Nombres'
        }),
        label='Nombres'
    )
    apellidos = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control cys-input',
            'placeholder': 'Apellidos'
        }),
        label='Apellidos'
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control cys-input',
            'placeholder': 'correo@ejemplo.com'
        }),
        label='Correo Electrónico'
    )
    usuario = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control cys-input',
            'placeholder': 'Nombre de usuario'
        }),
        label='Nombre de Usuario'
    )

    # ── Campos de Perfil ─────────────────────────────────────────
    tipo_id = forms.ChoiceField(
        choices=Perfil.TIPO_ID_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select cys-input'}),
        label='Tipo ID'
    )
    identificacion = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control cys-input',
            'placeholder': 'Número de identificación'
        }),
        label='Número de Identificación'
    )
    telefono = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control cys-input',
            'placeholder': 'Ej: 3001234567'
        }),
        label='Teléfono'
    )
    rol = forms.ChoiceField(
        choices=Perfil.ROL_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select cys-input'}),
        label='Rol'
    )

    # ── Contraseña ───────────────────────────────────────────────
    clave = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control cys-input',
            'placeholder': 'Mín. 6 caracteres, 2 números, 1 mayúscula',
        }),
        label='Contraseña'
    )
    clave_confirmar = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control cys-input',
            'placeholder': 'Confirmar contraseña',
        }),
        label='Confirmar Contraseña'
    )

    # ── Validaciones ─────────────────────────────────────────────
    def clean_identificacion(self):
        v = self.cleaned_data.get('identificacion', '')
        if not v.isdigit():
            raise forms.ValidationError('Solo debe contener números.')
        if Perfil.objects.filter(identificacion=v).exists():
            raise forms.ValidationError('Ya existe un usuario con esta identificación.')
        return v

    def clean_usuario(self):
        v = self.cleaned_data.get('usuario', '')
        if User.objects.filter(username=v).exists():
            raise forms.ValidationError('Este nombre de usuario ya está en uso.')
        return v

    def clean_email(self):
        v = self.cleaned_data.get('email', '')
        if v and User.objects.filter(email__iexact=v).exists():
            raise forms.ValidationError('Este correo ya está registrado.')
        return v

    def clean_nombre(self):
        v = self.cleaned_data.get('nombre', '')
        if any(c.isdigit() for c in v):
            raise forms.ValidationError('El nombre no debe contener números.')
        return v

    def clean_apellidos(self):
        v = self.cleaned_data.get('apellidos', '')
        if any(c.isdigit() for c in v):
            raise forms.ValidationError('Los apellidos no deben contener números.')
        return v

    def clean_telefono(self):
        v = self.cleaned_data.get('telefono', '')
        if v and not re.match(r'^\+?\d{7,15}$', v):
            raise forms.ValidationError('Ingresa un número de teléfono válido (7 a 15 dígitos).')
        return v

    def clean_clave(self):
        clave = self.cleaned_data.get('clave', '')
        validar_clave_segura(clave)
        return clave

    def clean(self):
        cleaned = super().clean()
        c1 = cleaned.get('clave')
        c2 = cleaned.get('clave_confirmar')
        if c1 and c2 and c1 != c2:
            raise forms.ValidationError('Las contraseñas no coinciden.')
        return cleaned

    def save(self):
        d = self.cleaned_data
        user = User.objects.create_user(
            username   = d['usuario'],
            password   = d['clave'],
            first_name = d['nombre'],
            last_name  = d['apellidos'],
            email      = d.get('email') or '',
        )
        perfil = Perfil.objects.create(
            user           = user,
            tipo_id        = d['tipo_id'],
            identificacion = d['identificacion'],
            telefono       = d.get('telefono') or None,
            rol            = d['rol'],
        )
        return perfil