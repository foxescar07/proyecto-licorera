from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils.crypto import get_random_string
from django.utils import timezone
from datetime import timedelta
from .models import Perfil
from .forms import UsuarioForm
import ssl, smtplib, re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

EMAIL_USER = 'ccanariasogamoso@gmail.com'
EMAIL_PASS = 'jmcikwsvajdmbzab'


def _enviar_correo(destinatario, asunto, cuerpo):
    mensaje = MIMEMultipart()
    mensaje['Subject'] = asunto
    mensaje['From']    = f'CYS Ltda <{EMAIL_USER}>'
    mensaje['To']      = destinatario
    mensaje.attach(MIMEText(cuerpo, 'plain'))
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode    = ssl.CERT_NONE
    with smtplib.SMTP('smtp.gmail.com', 587) as s:
        s.ehlo(); s.starttls(context=ctx); s.ehlo()
        s.login(EMAIL_USER, EMAIL_PASS)
        s.sendmail(EMAIL_USER, destinatario, mensaje.as_string())


def _validar_clave_segura(clave):
    if len(clave) < 6:
        return 'La contraseña debe tener al menos 6 caracteres.'
    if len(re.findall(r'\d', clave)) < 2:
        return 'La contraseña debe contener al menos 2 números.'
    if not re.search(r'[A-Z]', clave):
        return 'La contraseña debe contener al menos 1 letra mayúscula.'
    return None


def _solo_admin(request):
    return (
        request.user.is_authenticated
        and hasattr(request.user, 'perfil')
        and request.user.perfil.rol == 'admin'
    )


def _set_session(request, perfil):
    request.session['usuario_id']     = perfil.pk
    request.session['usuario_nombre'] = perfil.nombre_completo
    request.session['usuario_rol']    = perfil.rol
    request.session['usuario_user']   = perfil.usuario


# ── LOGIN / LOGOUT ─────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    from django.contrib.auth.forms import AuthenticationForm
    form = AuthenticationForm(request, data=request.POST or None)

    if request.method == 'POST':
        identificacion = request.POST.get('username', '').strip()
        clave          = request.POST.get('password', '')
        try:
            perfil = Perfil.objects.select_related('user').get(
                identificacion=identificacion, activo=True
            )
            user = authenticate(request, username=perfil.user.username, password=clave)
            if user:
                login(request, user)
                _set_session(request, perfil)
                return redirect('home')
            else:
                messages.error(request, 'Número de identificación o contraseña incorrectos.')
        except Perfil.DoesNotExist:
            messages.error(request, 'Número de identificación o contraseña incorrectos.')

    return render(request, 'usuarios/usuario.html', {'form': form})


def logout_view(request):
    logout(request)
    request.session.flush()
    response = redirect('login')
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
    response['Pragma']  = 'no-cache'
    response['Expires'] = '0'
    return response


# ── LISTA / CREAR ──────────────────────────────────────────────

def lista_usuarios(request):
    if not request.user.is_authenticated:
        return redirect('login')
    list(messages.get_messages(request))
    usuarios = Perfil.objects.select_related('user').order_by('-user__date_joined')
    return render(request, 'usuarios/usuarios_lista.html', {'usuarios': usuarios})


def crear_usuario(request):
    form = UsuarioForm()
    if request.method == 'POST':
        form = UsuarioForm(request.POST)
        if form.is_valid():
            perfil = form.save()
            return render(request, 'usuarios/crear_usuario.html', {
                'form': form,
                'usuario_creado': True,
                'nuevo_usuario': perfil.usuario,
            })
        else:
            for campo, errores in form.errors.items():
                for error in errores:
                    messages.error(request, error)
    return render(request, 'usuarios/crear_usuario.html', {'form': form})


# ── EDITAR ─────────────────────────────────────────────────────

def editar_usuario(request, pk):
    if not request.user.is_authenticated:
        return redirect('login')
    if not _solo_admin(request):
        messages.error(request, 'Sin permisos.')
        return redirect('usuario')

    perfil = get_object_or_404(Perfil, pk=pk)

    if request.method == 'POST':
        nombre      = request.POST.get('nombre', '').strip()
        apellidos   = request.POST.get('apellidos', '').strip()
        email       = request.POST.get('email', '').strip().lower()
        rol         = request.POST.get('rol', '').strip()
        clave_nueva = request.POST.get('clave_nueva', '').strip()

        error = None
        if not nombre or not apellidos:
            error = 'Nombre y apellidos son obligatorios.'
        elif any(c.isdigit() for c in nombre):
            error = 'El nombre no debe contener números.'
        elif any(c.isdigit() for c in apellidos):
            error = 'Los apellidos no deben contener números.'
        elif rol not in ['admin', 'cajero', 'empleado']:
            error = 'Rol inválido.'
        elif email and email != (perfil.email or '').lower():
            if User.objects.filter(email__iexact=email).exclude(pk=perfil.user.pk).exists():
                error = 'Este correo ya está en uso.'

        if error:
            messages.error(request, error)
        else:
            perfil.user.first_name = nombre
            perfil.user.last_name  = apellidos
            perfil.user.email      = email or ''
            perfil.user.save(update_fields=['first_name', 'last_name', 'email'])
            perfil.rol = rol
            perfil.save(update_fields=['rol'])

            if clave_nueva:
                err = _validar_clave_segura(clave_nueva)
                if err:
                    messages.error(request, err)
                else:
                    perfil.user.set_password(clave_nueva)
                    perfil.user.save(update_fields=['password'])

            if not messages.get_messages(request):
                messages.success(request, f'Usuario {perfil.usuario} actualizado correctamente.')
                return redirect('usuario')

    return render(request, 'usuarios/editar_usuario.html', {'perfil': perfil})


# ── TOGGLE / ELIMINAR ──────────────────────────────────────────

def toggle_activo(request, pk):
    if not request.user.is_authenticated:
        return redirect('login')
    if not _solo_admin(request) or request.method != 'POST':
        return redirect('usuario')

    perfil = get_object_or_404(Perfil, pk=pk)

    if perfil.pk == request.session.get('usuario_id'):
        messages.error(request, 'No puedes desactivar tu propia cuenta.')
        return redirect('usuario')

    perfil.activo         = not perfil.activo
    perfil.user.is_active = perfil.activo
    perfil.save(update_fields=['activo'])
    perfil.user.save(update_fields=['is_active'])
    return redirect('usuario')


def eliminar_usuario(request, pk):
    if not _solo_admin(request) or request.method != 'POST':
        return redirect('usuario')

    perfil = get_object_or_404(Perfil, pk=pk)

    if perfil.activo:
        messages.error(request, 'Solo se pueden eliminar usuarios inactivos.')
        return redirect('usuario')
    if perfil.pk == request.session.get('usuario_id'):
        messages.error(request, 'No puedes eliminarte a ti mismo.')
        return redirect('usuario')

    perfil.user.delete()
    messages.success(request, 'Usuario eliminado correctamente.')
    return redirect('usuario')


# ── PERFIL ─────────────────────────────────────────────────────

def perfil_view(request):
    if not request.user.is_authenticated:
        return redirect('login')

    perfil = request.user.perfil

    if request.method == 'POST':
        nombre       = request.POST.get('nombre', '').strip()
        apellidos    = request.POST.get('apellidos', '').strip()
        email        = request.POST.get('email', '').strip().lower()
        clave_nueva  = request.POST.get('clave_nueva', '').strip()
        clave_actual = request.POST.get('clave_actual', '').strip()

        error = None
        if not nombre or not apellidos:
            error = 'Nombre y apellidos son obligatorios.'
        elif any(c.isdigit() for c in nombre):
            error = 'El nombre no debe contener números.'
        elif any(c.isdigit() for c in apellidos):
            error = 'Los apellidos no deben contener números.'
        elif clave_nueva and not clave_actual:
            error = 'Ingresa tu contraseña actual para cambiarla.'
        elif clave_nueva and not request.user.check_password(clave_actual):
            error = 'La contraseña actual es incorrecta.'
        elif clave_nueva:
            error = _validar_clave_segura(clave_nueva)

        if error:
            messages.error(request, error)
        else:
            perfil.user.first_name = nombre
            perfil.user.last_name  = apellidos
            perfil.user.email      = email or ''
            perfil.user.save(update_fields=['first_name', 'last_name', 'email'])

            if clave_nueva:
                perfil.user.set_password(clave_nueva)
                perfil.user.save(update_fields=['password'])
                update_session_auth_hash(request, perfil.user)

            request.session['usuario_nombre'] = perfil.nombre_completo
            messages.success(request, 'Perfil actualizado correctamente.')
            return redirect('perfil')

    return render(request, 'usuarios/perfil.html', {'perfil': perfil})


# ── RECUPERACIÓN DE CONTRASEÑA ─────────────────────────────────

def solicitar_recuperacion(request):
    if request.method == 'POST':
        correo = request.POST.get('correo', '').strip().lower()
        try:
            perfil = Perfil.objects.select_related('user').get(
                user__email__iexact=correo, activo=True
            )
        except Perfil.DoesNotExist:
            messages.error(request, 'No existe una cuenta activa con ese correo.')
            return redirect('login')

        token  = get_random_string(32)
        expira = timezone.now() + timedelta(minutes=15)
        perfil.reset_token        = token
        perfil.reset_token_expira = expira
        perfil.save(update_fields=['reset_token', 'reset_token_expira'])

        link   = request.build_absolute_uri(f'/usuarios/restablecer/{token}/')
        cuerpo = (
            f'Hola {perfil.nombre},\n\n'
            f'Haz clic en el siguiente enlace (válido por 15 minutos):\n{link}\n\n'
            f'— Equipo CYS Ltda'
        )
        try:
            _enviar_correo(perfil.email, 'Recuperación de contraseña — CYS Ltda', cuerpo)
            messages.success(request, f'Enviamos un enlace a {perfil.email}. Válido por 15 minutos.')
        except Exception as e:
            messages.error(request, f'Error al enviar el correo: {e}')

    return redirect('login')


def restablecer_clave(request, token):
    try:
        perfil = Perfil.objects.select_related('user').get(reset_token=token, activo=True)
    except Perfil.DoesNotExist:
        return render(request, 'usuarios/restablecer_clave.html', {'error': 'El enlace no es válido o ya fue utilizado.'})

    if timezone.now() > perfil.reset_token_expira:
        Perfil.objects.filter(pk=perfil.pk).update(reset_token=None, reset_token_expira=None)
        return render(request, 'usuarios/restablecer_clave.html', {'error': 'El enlace expiró. Solicita uno nuevo.'})

    if request.method == 'POST':
        nueva     = request.POST.get('nueva_clave', '')