from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import (
    authenticate, login, logout,
    update_session_auth_hash, get_user_model,
)
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.crypto import get_random_string
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse, NoReverseMatch
from datetime import timedelta
from django.http import JsonResponse
from .forms import UsuarioForm
import random
import logging
import re

logger = logging.getLogger(__name__)

Usuario = get_user_model()


# ── HELPERS PRIVADOS ───────────────────────────────────────────────────────────

def _enviar_correo(destinatario, asunto, cuerpo):
    send_mail(
        subject=asunto,
        message=cuerpo,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[destinatario],
        fail_silently=False,
    )


def _validar_clave_segura(clave):
    if len(clave) < 6:
        return 'La contraseña debe tener al menos 6 caracteres.'
    if len(re.findall(r'\d', clave)) < 2:
        return 'La contraseña debe contener al menos 2 números.'
    if not re.search(r'[A-Z]', clave):
        return 'La contraseña debe contener al menos 1 mayúscula.'
    return None


def _solo_admin(request):
    return request.user.is_authenticated and request.user.rol == 'admin'


def _set_session(request, usuario):
    request.session['usuario_id']     = usuario.pk
    request.session['usuario_nombre'] = usuario.nombre_completo
    request.session['usuario_rol']    = usuario.rol
    request.session['usuario_user']   = usuario.usuario


def _ctx_base(request):
    u = request.user
    if not u.is_authenticated:
        return {}
    return {
        'session_nombre':  u.nombre_completo,
        'session_rol':     u.rol,
        'session_usuario': u.usuario,
    }


def _destino_post_login(request):
    """
    Lee la cookie 'cys_pagina_inicio' (guardada desde Configuración) y
    devuelve la URL a la que se debe redirigir tras iniciar sesión.
    Si no existe la cookie o el valor no es válido, cae a 'principal' (Tablero).
    """
    pagina = request.COOKIES.get('cys_pagina_inicio', 'tablero')
    mapa_urls = {
        'tablero':   'principal',
        'ventas':    'ventas:ventas_lista',
        'productos': 'lista_productos',
    }
    nombre_url = mapa_urls.get(pagina, 'principal')
    try:
        return reverse(nombre_url)
    except NoReverseMatch:
        return reverse('principal')


# ── LOGIN ──────────────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect(_destino_post_login(request))

    seccion       = request.GET.get('action', 'login')
    usuario_input = ''

    if request.method == 'POST':
        identificacion = request.POST.get('usuario_input', '').strip()
        clave          = request.POST.get('clave_input', '')
        usuario_input  = identificacion
        es_ajax        = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        usuario = None

        try:
            candidato = Usuario.objects.get(identificacion=identificacion, activo=True)
            if candidato.username == candidato.identificacion:
                usuario = candidato
        except Usuario.DoesNotExist:
            pass

        if usuario is None:
            try:
                usuario = Usuario.objects.get(username__iexact=identificacion, activo=True)
            except Usuario.DoesNotExist:
                pass

        if usuario:
            user = authenticate(request, username=usuario.username, password=clave)
            if user:
                login(request, user)
                _set_session(request, usuario)
                destino = _destino_post_login(request)
                if es_ajax:
                    return JsonResponse({'ok': True, 'redirect': destino})
                return redirect(destino)

        err = 'Usuario o contraseña incorrectos.'
        if es_ajax:
            return JsonResponse({'ok': False, 'error': err})
        messages.error(request, err)
        seccion = 'login'

    ctx = {
        'seccion':       seccion,
        'usuario_input': usuario_input,
    }
    return render(request, 'usuario.html', ctx)


# ── LOGOUT ─────────────────────────────────────────────────────────────────────

def logout_view(request):
    logout(request)
    request.session.flush()
    response = redirect('login')
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
    response['Pragma']        = 'no-cache'
    response['Expires']       = '0'
    return response


# ── LISTA USUARIOS ─────────────────────────────────────────────────────────────

def lista_usuarios(request):
    if not request.user.is_authenticated:
        return redirect('login')

    list(messages.get_messages(request))
    usuarios = Usuario.objects.all().order_by('-date_joined')

    ctx = {
        **_ctx_base(request),
        'usuarios':          usuarios,
        'usuarios_activos':   usuarios.filter(is_active=True).count(),
        'usuarios_inactivos': usuarios.filter(is_active=False).count(),
        'total_usuarios':    usuarios.count(),
        'tipo_id_choices':   Usuario.TIPO_ID_CHOICES,
        'rol_choices':       Usuario.ROL_CHOICES,
        'breadcrumb_items': [
            {'nombre': 'Usuarios', 'url': None},
        ],
    }
    return render(request, 'usuarios_lista.html', ctx)


# ── CREAR USUARIO (página pública) ────────────────────────────────────────────

def crear_usuario(request):
    form = UsuarioForm()

    if request.method == 'POST':
        form = UsuarioForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            ctx = {
                **_ctx_base(request),
                'form':           form,
                'usuario_creado': True,
                'nuevo_usuario':  usuario.usuario,
                'breadcrumb_items': [
                    {'nombre': 'Usuarios', 'url': reverse('usuario')},  # ← confirma este nombre
                    {'nombre': 'Crear Usuario', 'url': None},
                ],
            }
            return render(request, 'crear_usuario.html', ctx)
        else:
            for campo, errores in form.errors.items():
                for error in errores:
                    messages.error(request, error)

    ctx = {
        **_ctx_base(request),
        'form': form,
        'breadcrumb_items': [
            {'nombre': 'Usuarios', 'url': reverse('usuario')},
            {'nombre': 'Crear Usuario', 'url': None},
        ],
    }
    return render(request, 'crear_usuario.html', ctx)


# ── CREAR USUARIO AJAX (desde modal en lista) ─────────────────────────────────

def crear_usuario_ajax(request):
    if not request.user.is_authenticated:
        return JsonResponse({'ok': False, 'error': 'Sin sesión.'}, status=403)
    if not _solo_admin(request):
        return JsonResponse({'ok': False, 'error': 'Sin permisos.'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido.'})

    import json
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, Exception):
        return JsonResponse({'ok': False, 'error': 'Datos inválidos.'})

    tipo_id        = data.get('tipo_identificacion', '').strip()
    identificacion = data.get('identificacion', '').strip()
    nombre         = data.get('first_name', '').strip()
    apellidos      = data.get('last_name', '').strip()
    email          = data.get('email', '').strip().lower()
    telefono       = data.get('telefono', '').strip()
    username       = data.get('username', '').strip()
    rol            = data.get('rol', '').strip()
    password1      = data.get('password1', '')
    password2      = data.get('password2', '')

    # Validaciones
    if not all([tipo_id, identificacion, nombre, apellidos, username, rol, password1]):
        return JsonResponse({'ok': False, 'error': 'Completa todos los campos obligatorios.'})
    if any(c.isdigit() for c in nombre):
        return JsonResponse({'ok': False, 'error': 'El nombre no debe contener números.'})
    if any(c.isdigit() for c in apellidos):
        return JsonResponse({'ok': False, 'error': 'Los apellidos no deben contener números.'})
    if password1 != password2:
        return JsonResponse({'ok': False, 'error': 'Las contraseñas no coinciden.'})

    err_clave = _validar_clave_segura(password1)
    if err_clave:
        return JsonResponse({'ok': False, 'error': err_clave})

    TIPOS_VALIDOS = ['CC', 'TI', 'CE', 'PA', 'NIT']
    if tipo_id not in TIPOS_VALIDOS:
        return JsonResponse({'ok': False, 'error': 'Tipo de identificación inválido.'})

    ROLES_VALIDOS = [ 'cajero', 'empleado']
    if rol not in ROLES_VALIDOS:
        return JsonResponse({'ok': False, 'error': 'Rol inválido.'})

    if Usuario.objects.filter(identificacion=identificacion).exists():
        return JsonResponse({'ok': False, 'error': 'Ya existe un usuario con esa identificación.'})
    if Usuario.objects.filter(username__iexact=username).exists():
        return JsonResponse({'ok': False, 'error': 'Ese nombre de usuario ya está en uso.'})
    if email and Usuario.objects.filter(email__iexact=email).exists():
        return JsonResponse({'ok': False, 'error': 'Ese correo ya está en uso.'})

    usuario = Usuario(
        username       = username,
        first_name     = nombre,
        last_name      = apellidos,
        email          = email or '',
        identificacion = identificacion,
        tipo_id        = tipo_id,
        telefono       = telefono or None,
        rol            = rol,
        activo         = True,
        is_active      = True,
    )
    usuario.set_password(password1)
    usuario.save()

    return JsonResponse({
        'ok':              True,
        'mensaje':         f'Usuario {usuario.username} creado correctamente.',
        'usuario': {
            'pk':              usuario.pk,
            'nombre_completo': usuario.get_full_name(),
            'username':        usuario.username,
            'email':           usuario.email or '',
            'rol':             usuario.rol,
            'rol_label':       usuario.get_rol_display(),
            'identificacion':  usuario.identificacion,
            'tipo_id_label':   usuario.get_tipo_id_display(),
            'fecha_registro':  usuario.date_joined.strftime('%d/%m/%Y'),
            'activo':          usuario.activo,
        }
    })


# ── FRAGMENTO MODAL CREAR USUARIO ─────────────────────────────────────────────

# views.py — función crear_usuario_modal
@login_required
def crear_usuario_modal(request):
    if not _solo_admin(request):
        return JsonResponse({'ok': False, 'error': 'Sin permisos.'}, status=403)

    if request.headers.get('X-Modal-Request') == 'true':
        return render(request, 'crear_usuario_modal.html')  # ← sin subcarpeta

    return redirect('usuario')


# ── EDITAR USUARIO ─────────────────────────────────────────────────────────────

def editar_usuario(request, pk):
    if not request.user.is_authenticated:
        return redirect('login')
    if not _solo_admin(request):
        return JsonResponse({'ok': False, 'error': 'Sin permisos.'}, status=403)

    usuario = get_object_or_404(Usuario, pk=pk)

    if request.method == 'GET' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'ok':             True,
            'pk':             usuario.pk,
            'nombre':         usuario.first_name,
            'apellidos':      usuario.last_name,
            'email':          usuario.email or '',
            'usuario':        usuario.username,
            'rol':            usuario.rol,
            'activo':         usuario.activo,
            'fecha_registro': usuario.date_joined.strftime('%d/%m/%Y'),
        })

    if request.method == 'POST':
        es_ajax     = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        nombre      = request.POST.get('nombre', '').strip()
        apellidos   = request.POST.get('apellidos', '').strip()
        email       = request.POST.get('email', '').strip().lower()
        rol         = request.POST.get('rol', '').strip()
        clave_nueva = request.POST.get('clave_nueva', '').strip()
        error       = None

        if not nombre or not apellidos:
            error = 'Nombre y apellidos son obligatorios.'
        elif any(c.isdigit() for c in nombre):
            error = 'El nombre no debe contener números.'
        elif any(c.isdigit() for c in apellidos):
            error = 'Los apellidos no deben contener números.'
        elif rol not in [ 'cajero', 'empleado']:
            error = 'Rol inválido.'
        elif email and email != (usuario.email or '').lower():
            if Usuario.objects.filter(email__iexact=email).exclude(pk=usuario.pk).exists():
                error = 'Este correo ya está en uso.'

        if clave_nueva and not error:
            error = _validar_clave_segura(clave_nueva)

        if error:
            if es_ajax:
                return JsonResponse({'ok': False, 'error': error})
            messages.error(request, error)
            return render(request, 'editar_usuario.html', {
        **_ctx_base(request),
        'perfil': usuario,
        'breadcrumb_items': [
            {'nombre': 'Usuarios', 'url': reverse('usuario')},  # ← confirma este nombre
            {'nombre': f'Editar: {usuario.first_name}', 'url': None},
        ],
    })

        usuario.first_name = nombre
        usuario.last_name  = apellidos
        usuario.email      = email or ''
        usuario.rol        = rol
        usuario.save(update_fields=['first_name', 'last_name', 'email', 'rol'])

        if clave_nueva:
            usuario.set_password(clave_nueva)
            usuario.save(update_fields=['password'])

        if es_ajax:
            return JsonResponse({
                'ok':              True,
                'mensaje':         f'Usuario {usuario.username} actualizado.',
                'nombre_completo': usuario.get_full_name(),
                'rol_label':       usuario.get_rol_display(),
            })

        messages.success(request, f'Usuario {usuario.username} actualizado correctamente.')
        return redirect('usuario')

    return render(request, 'editar_usuario.html', {
        **_ctx_base(request), 
        
            'perfil': usuario,
            'breadcrumb_items': [
            {'nombre': 'Usuarios', 'url': reverse('usuario')},  # ← confirma este nombre
            {'nombre': f'Editar: {usuario.first_name}', 'url': None},
        ],
    })


# ── PERFIL DATOS (JSON) ────────────────────────────────────────────────────────

def perfil_datos(request):
    if not request.user.is_authenticated:
        return JsonResponse({'ok': False, 'error': 'Sin sesión.'})

    u = request.user
    return JsonResponse({
        'ok':             True,
        'nombre':         u.first_name,
        'apellidos':      u.last_name,
        'usuario':        u.username,
        'email':          u.email or '',
        'tipo_id':        u.tipo_id,
        'tipo_id_label':  u.get_tipo_id_display(),
        'identificacion': u.identificacion,
        'rol':            u.rol,
        'rol_label':      u.get_rol_display(),
        'fecha_registro': u.date_joined.strftime('%d/%m/%Y'),
    })


# ── PERFIL EDITAR (JSON) ───────────────────────────────────────────────────────

def perfil_editar(request):
    if not request.user.is_authenticated:
        return JsonResponse({'ok': False, 'error': 'Sin sesión.'})
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido.'})

    usuario = request.user
    accion  = request.POST.get('accion', '')

    if accion == 'verificar_clave':
        clave = request.POST.get('clave_actual', '')
        if not clave:
            return JsonResponse({'ok': False, 'error': 'Ingresa tu contraseña actual.'})
        if not usuario.check_password(clave):
            return JsonResponse({'ok': False, 'error': 'La contraseña actual es incorrecta.'})
        return JsonResponse({'ok': True})

    if accion == 'cambiar_usuario':
        nuevo = request.POST.get('usuario', '').strip()
        if not nuevo:
            return JsonResponse({'ok': False, 'error': 'Escribe el nuevo nombre de usuario.'})
        if not re.match(r'^[a-zA-Z0-9_]{3,30}$', nuevo):
            return JsonResponse({'ok': False, 'error': 'Solo letras, números y _ (3–30 caracteres).'})
        if Usuario.objects.filter(username=nuevo).exclude(pk=usuario.pk).exists():
            return JsonResponse({'ok': False, 'error': 'Ese nombre de usuario ya está en uso.'})
        usuario.username = nuevo
        usuario.save(update_fields=['username'])
        request.session['usuario_user'] = nuevo
        return JsonResponse({'ok': True})

    if accion == 'cambiar_clave':
        nueva = request.POST.get('clave_nueva', '')
        if not nueva:
            return JsonResponse({'ok': False, 'error': 'Escribe la nueva contraseña.'})
        err = _validar_clave_segura(nueva)
        if err:
            return JsonResponse({'ok': False, 'error': err})
        usuario.set_password(nueva)
        usuario.save(update_fields=['password'])
        update_session_auth_hash(request, usuario)
        return JsonResponse({'ok': True})

    if accion == 'info':
        nombre    = request.POST.get('nombre', '').strip()
        apellidos = request.POST.get('apellidos', '').strip()
        email     = request.POST.get('email', '').strip().lower()
        telefono  = request.POST.get('telefono', '').strip()

        if not nombre or not apellidos:
            return JsonResponse({'ok': False, 'error': 'Nombre y apellidos son obligatorios.'})
        if any(c.isdigit() for c in nombre):
            return JsonResponse({'ok': False, 'error': 'El nombre no debe contener números.'})
        if any(c.isdigit() for c in apellidos):
            return JsonResponse({'ok': False, 'error': 'Los apellidos no deben contener números.'})
        if email and email != (usuario.email or '').lower():
            if Usuario.objects.filter(email__iexact=email).exclude(pk=usuario.pk).exists():
                return JsonResponse({'ok': False, 'error': 'Este correo ya está en uso.'})

        usuario.first_name = nombre
        usuario.last_name  = apellidos
        usuario.email      = email or ''
        usuario.telefono   = telefono or None
        usuario.save(update_fields=['first_name', 'last_name', 'email', 'telefono'])
        request.session['usuario_nombre'] = usuario.get_full_name()
        return JsonResponse({'ok': True, 'nombre_completo': usuario.get_full_name()})

    return JsonResponse({'ok': False, 'error': 'Acción no reconocida.'})


# ── RECUPERAR CLAVE (ENLACE POR CORREO) ───────────────────────────────────────

def solicitar_recuperacion(request):
    if request.method == 'POST':
        correo = request.POST.get('correo', '').strip().lower()

        try:
            usuario = Usuario.objects.get(email__iexact=correo, activo=True)
        except Usuario.DoesNotExist:
            messages.error(request, 'No existe una cuenta activa con ese correo.')
            return redirect('/usuarios/login/?action=correo')

        token  = get_random_string(32)
        expira = timezone.now() + timedelta(minutes=15)
        usuario.reset_token        = token
        usuario.reset_token_expira = expira
        usuario.save(update_fields=['reset_token', 'reset_token_expira'])

        link   = request.build_absolute_uri(f'/usuarios/restablecer/{token}/')
        cuerpo = (
            f'Hola {usuario.first_name},\n\n'
            f'Recibimos una solicitud para restablecer la contraseña de tu cuenta en CYS Ltda.\n\n'
            f'Haz clic en el siguiente enlace para crear una nueva contraseña:\n\n{link}\n\n'
            f'Este enlace expirará en 15 minutos.\n\n'
            f'Si no solicitaste este cambio, ignora este mensaje.\n\n'
            f'CYS Ltda'
        )

        try:
            _enviar_correo(usuario.email, 'Recuperación de contraseña — CYS Ltda', cuerpo)
            messages.success(request, f'Enlace enviado a {usuario.email}')
        except Exception as e:
            logger.error(f'[CYS EMAIL] Error al enviar correo a {usuario.email}: {e}')
            messages.error(request, 'No se pudo enviar el correo. Intenta más tarde.')

        return redirect('/usuarios/login/?action=correo')

    return redirect('login')


# ── RECUPERAR CLAVE (CÓDIGO OTP POR CORREO) ───────────────────────────────────

def solicitar_otp_correo(request):
    if request.method != 'POST':
        return redirect('login')

    correo = request.POST.get('correo', '').strip().lower()

    if not correo:
        messages.error(request, 'Ingresa tu correo electrónico.')
        return redirect('/usuarios/login/?action=otp')

    try:
        usuario = Usuario.objects.get(email__iexact=correo, activo=True)
    except Usuario.DoesNotExist:
        messages.success(request, 'Si el correo está registrado, recibirás un código en breve.')
        return redirect('/usuarios/login/?action=otp')

    codigo = str(random.randint(100000, 999999))
    expira = timezone.now() + timedelta(minutes=10)

    usuario.reset_token        = codigo
    usuario.reset_token_expira = expira
    usuario.save(update_fields=['reset_token', 'reset_token_expira'])

    cuerpo = (
        f'Hola {usuario.first_name},\n\n'
        f'Tu código de verificación para restablecer tu contraseña en CYS Ltda es:\n\n'
        f'        {codigo}\n\n'
        f'Este código expira en 10 minutos.\n'
        f'Si no solicitaste esto, ignora este mensaje.\n\n'
        f'CYS Ltda'
    )

    try:
        _enviar_correo(usuario.email, f'Código de verificación: {codigo} — CYS Ltda', cuerpo)
    except Exception as e:
        logger.error(f'[CYS OTP] Error al enviar código a {usuario.email}: {e}')
        messages.error(request, 'No se pudo enviar el correo. Intenta más tarde.')
        return redirect('/usuarios/login/?action=otp')

    request.session['otp_correo'] = correo
    messages.success(request, f'Código enviado a {correo}')
    return redirect('/usuarios/login/?action=otp_verificar')


def verificar_otp_correo(request):
    if request.method != 'POST':
        return redirect('login')

    correo = request.POST.get('correo', '').strip().lower() or request.session.get('otp_correo', '')
    codigo = request.POST.get('codigo', '').strip()

    if not correo or not codigo:
        messages.error(request, 'Datos incompletos.')
        return redirect('/usuarios/login/?action=otp_verificar')

    try:
        usuario = Usuario.objects.get(
            email__iexact=correo,
            reset_token=codigo,
            activo=True,
        )
    except Usuario.DoesNotExist:
        messages.error(request, 'Código incorrecto. Verifica e intenta de nuevo.')
        return redirect('/usuarios/login/?action=otp_verificar')

    if timezone.now() > usuario.reset_token_expira:
        Usuario.objects.filter(pk=usuario.pk).update(reset_token=None, reset_token_expira=None)
        request.session.pop('otp_correo', None)
        messages.error(request, 'El código expiró. Solicita uno nuevo.')
        return redirect('/usuarios/login/?action=otp')

    token  = get_random_string(32)
    expira = timezone.now() + timedelta(minutes=10)
    usuario.reset_token        = token
    usuario.reset_token_expira = expira
    usuario.save(update_fields=['reset_token', 'reset_token_expira'])

    request.session.pop('otp_correo', None)
    return redirect(f'/usuarios/restablecer/{token}/')


# ── RESTABLECER CLAVE ──────────────────────────────────────────────────────────

def restablecer_clave(request, token):
    try:
        usuario = Usuario.objects.get(reset_token=token, activo=True)
    except Usuario.DoesNotExist:
        return render(request, 'restablecer_clave.html', {
            'error': 'El enlace o código no es válido o ya fue utilizado.'
        })

    if timezone.now() > usuario.reset_token_expira:
        Usuario.objects.filter(pk=usuario.pk).update(reset_token=None, reset_token_expira=None)
        return render(request, 'restablecer_clave.html', {
            'error': 'El enlace o código expiró. Solicita uno nuevo.'
        })

    if request.method == 'POST':
        nueva     = request.POST.get('nueva_clave', '')
        confirmar = request.POST.get('confirmar', '')
        error     = _validar_clave_segura(nueva)

        if error:
            return render(request, 'restablecer_clave.html', {'token': token, 'error': error})
        if nueva != confirmar:
            return render(request, 'restablecer_clave.html', {
                'token': token, 'error': 'Las contraseñas no coinciden.'
            })

        usuario.set_password(nueva)
        usuario.save(update_fields=['password'])
        Usuario.objects.filter(pk=usuario.pk).update(reset_token=None, reset_token_expira=None)
        return render(request, 'restablecer_clave.html', {'exito': True})

    return render(request, 'restablecer_clave.html', {'token': token})


# ── TOGGLE ACTIVO ──────────────────────────────────────────────────────────────

def toggle_activo(request, pk):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido.'})

    usuario           = get_object_or_404(Usuario, pk=pk)
    usuario.activo    = not usuario.activo
    usuario.is_active = usuario.activo
    usuario.save()
    return JsonResponse({'ok': True, 'activo': usuario.activo})


# ── ELIMINAR USUARIO ───────────────────────────────────────────────────────────

def eliminar_usuario(request, pk):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido.'})

    usuario = get_object_or_404(Usuario, pk=pk)
    if usuario.pk == request.user.pk:
        return JsonResponse({'ok': False, 'error': 'No puedes eliminar tu propia cuenta.'})

    usuario.delete()
    return JsonResponse({'ok': True, 'mensaje': 'Usuario eliminado correctamente.'})


# ── PERFIL PÁGINA ──────────────────────────────────────────────────────────────

@login_required
def perfil_pagina(request):
    u = request.user
    ctx = {
        **_ctx_base(request),
        'nombre':         u.first_name,
        'apellidos':      u.last_name,
        'usuario':        u.username,
        'email':          u.email,
        'rol':            u.rol,
        'rol_label':      u.get_rol_display(),
        'tipo_id':        u.tipo_id,
        'tipo_id_label':  u.get_tipo_id_display(),
        'fecha_registro': u.date_joined.strftime('%d/%m/%Y'),
        'identificacion': u.identificacion,
        'telefono':       u.telefono or '—',
        'tiene_foto':     bool(u.foto),
        'foto_url':       u.foto.url if u.foto else None,
        'avatar_name':    u.avatar_name,
        'breadcrumb_items': [
            {'nombre': 'Mi Perfil', 'url': None},
        ],
    }
    return render(request, 'perfil.html', ctx)


# ── ACTUALIZAR FOTO ────────────────────────────────────────────────────────────

@login_required
def actualizar_foto(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido.'})

    if request.POST.get('quitar') == '1':
        if request.user.foto:
            request.user.foto.delete(save=False)
            request.user.foto = None
            request.user.save(update_fields=['foto'])
        return JsonResponse({'ok': True})

    foto = request.FILES.get('foto')
    if not foto:
        return JsonResponse({'ok': False, 'error': 'No se recibió ninguna imagen.'})
    if foto.content_type not in ['image/jpeg', 'image/png', 'image/webp', 'image/gif']:
        return JsonResponse({'ok': False, 'error': 'Formato no permitido. Usa JPG, PNG o WEBP.'})
    if foto.size > 5 * 1024 * 1024:
        return JsonResponse({'ok': False, 'error': 'La imagen no debe superar 5 MB.'})

    if request.user.foto:
        request.user.foto.delete(save=False)
    request.user.foto = foto
    request.user.save(update_fields=['foto'])
    return JsonResponse({'ok': True, 'url': request.user.foto.url})


# ── CREAR USUARIO DESDE ADMIN (AJAX — formulario clásico POST) ────────────────

def crear_usuario_admin(request):
    if not request.user.is_authenticated:
        return JsonResponse({'ok': False, 'error': 'Sin sesión.'}, status=401)
    if request.user.rol != 'admin':
        return JsonResponse({'ok': False, 'error': 'Sin permisos.'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido.'}, status=405)

    tipo_id        = request.POST.get('tipo_id', '').strip()
    identificacion = request.POST.get('identificacion', '').strip()
    nombre         = request.POST.get('nombre', '').strip()
    apellidos      = request.POST.get('apellidos', '').strip()
    email          = request.POST.get('email', '').strip().lower()
    telefono       = request.POST.get('telefono', '').strip()
    clave          = request.POST.get('clave', '').strip()

    if not all([tipo_id, identificacion, nombre, apellidos, clave]):
        return JsonResponse({'ok': False, 'error': 'Completa todos los campos obligatorios.'})
    if any(c.isdigit() for c in nombre):
        return JsonResponse({'ok': False, 'error': 'El nombre no debe contener números.'})
    if any(c.isdigit() for c in apellidos):
        return JsonResponse({'ok': False, 'error': 'Los apellidos no deben contener números.'})

    err_clave = _validar_clave_segura(clave)
    if err_clave:
        return JsonResponse({'ok': False, 'error': err_clave})

    if Usuario.objects.filter(identificacion=identificacion).exists():
        return JsonResponse({'ok': False, 'error': 'Ya existe un usuario con esa identificación.'})
    if email and Usuario.objects.filter(email__iexact=email).exists():
        return JsonResponse({'ok': False, 'error': 'Ese correo ya está en uso.'})

    TIPOS_VALIDOS = ['CC', 'TI', 'CE', 'PA', 'NIT']
    if tipo_id not in TIPOS_VALIDOS:
        return JsonResponse({'ok': False, 'error': 'Tipo de identificación inválido.'})

    usuario = Usuario(
        username       = identificacion,
        first_name     = nombre,
        last_name      = apellidos,
        email          = email or '',
        identificacion = identificacion,
        tipo_id        = tipo_id,
        telefono       = telefono or None,
        rol            = 'empleado',
        activo         = True,
        is_active      = True,
    )
    usuario.set_password(clave)
    usuario.save()

    return JsonResponse({
        'ok':              True,
        'pk':              usuario.pk,
        'nombre_completo': usuario.get_full_name(),
        'usuario':         usuario.username,
        'email':           usuario.email,
        'identificacion':  usuario.identificacion,
        'tipo_id_display': usuario.get_tipo_id_display(),
        'fecha_registro':  usuario.date_joined.strftime('%d/%m/%Y'),
        'foto_url':        None,
    })