from django import forms
from django.contrib.auth import get_user_model
import re
import unicodedata

Usuario = get_user_model()


def _normalizar(texto):
    """Quita tildes y caracteres especiales, deja solo a-z0-9."""
    nfkd = unicodedata.normalize('NFKD', texto)
    solo_ascii = nfkd.encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'[^a-z0-9]', '', solo_ascii.lower())


class UsuarioForm(forms.Form):
    tipo_id        = forms.ChoiceField(choices=Usuario.TIPO_ID_CHOICES, widget=forms.Select(attrs={'class': 'cys-input'}))
    identificacion = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'placeholder': 'Número de identificación', 'class': 'cys-input'}))
    nombre         = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'placeholder': 'Nombres', 'class': 'cys-input'}))
    apellidos      = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'placeholder': 'Apellidos', 'class': 'cys-input'}))
    email          = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'placeholder': 'correo@ejemplo.com', 'class': 'cys-input'}))
    telefono       = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={'placeholder': 'Ej: 3001234567', 'class': 'cys-input'}))

    clave          = forms.CharField(min_length=6, widget=forms.PasswordInput(attrs={'placeholder': 'Mín. 6 caracteres, 2 números, 1 mayúscula', 'class': 'cys-input'}))

    def clean_identificacion(self):
        val = self.cleaned_data['identificacion']
        if Usuario.objects.filter(identificacion=val).exists():
            raise forms.ValidationError('Ya existe un usuario con esa identificación.')
        return val

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if email and Usuario.objects.filter(email__iexact=email).exists():
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

    def _generar_username(self, nombre, apellidos):
        """
        Genera username como nombre.apellido, sin tildes ni espacios.
        Si ya existe, agrega sufijo numérico: nombre.apellido2, nombre.apellido3 ...
        """
        primer_nombre   = _normalizar(nombre.strip().split()[0])
        primer_apellido = _normalizar(apellidos.strip().split()[0])
        base     = f"{primer_nombre}.{primer_apellido}"
        username = base
        contador = 2
        while Usuario.objects.filter(username=username).exists():
            username = f"{base}{contador}"
            contador += 1
        return username

    def save(self):
        data           = self.cleaned_data
        identificacion = data['identificacion']
        username       = self._generar_username(data['nombre'], data['apellidos'])

        usuario = Usuario.objects.create_user(
            username=username,
            password=data['clave'],
            first_name=data['nombre'],
            last_name=data['apellidos'],
            email=data.get('email') or '',
            tipo_id=data['tipo_id'],
            identificacion=identificacion,
            telefono=data.get('telefono') or None,
            rol='empleado',
            activo=True
        )
        return usuario