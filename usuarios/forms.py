from django import forms
from django.contrib.auth.models import User
from .models import Perfil
import re


class UsuarioForm(forms.Form):
    tipo_id        = forms.ChoiceField(choices=Perfil.TIPO_ID_CHOICES)
    identificacion = forms.CharField(max_length=20)
    nombre         = forms.CharField(max_length=100)
    apellidos      = forms.CharField(max_length=100)
    email          = forms.EmailField(required=False)
    telefono       = forms.CharField(max_length=15, required=False)
    rol            = forms.ChoiceField(choices=Perfil.ROL_CHOICES)
    clave          = forms.CharField(widget=forms.PasswordInput, min_length=6)

    def clean_identificacion(self):
        val = self.cleaned_data['identificacion']
        if Perfil.objects.filter(identificacion=val).exists():
            raise forms.ValidationError('Ya existe un usuario con esa identificación.')
        return val

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Este correo ya está en uso.')
        return email

    def clean_nombre(self):
        val = self.cleaned_data['nombre']
        if any(c.isdigit() for c in val):
            raise forms.ValidationError('El nombre no debe contener números.')
        return val

    def clean_apellidos(self):
        val = self.cleaned_data['apellidos']
        if any(c.isdigit() for c in val):
            raise forms.ValidationError('Los apellidos no deben contener números.')
        return val

    def clean_clave(self):
        clave = self.cleaned_data['clave']
        if len(re.findall(r'\d', clave)) < 2:
            raise forms.ValidationError('La contraseña debe contener al menos 2 números.')
        if not re.search(r'[A-Z]', clave):
            raise forms.ValidationError('La contraseña debe contener al menos 1 letra mayúscula.')
        return clave

    def save(self):
        data = self.cleaned_data
        identificacion = data['identificacion']

        # username = identificacion
        user = User.objects.create_user(
            username   = identificacion,
            password   = data['clave'],
            first_name = data['nombre'],
            last_name  = data['apellidos'],
            email      = data.get('email') or '',
        )
        perfil = Perfil.objects.create(
            user           = user,
            tipo_id        = data['tipo_id'],
            identificacion = identificacion,
            telefono       = data.get('telefono') or None,
            rol            = data['rol'],
            activo         = True,
        )
        return perfil