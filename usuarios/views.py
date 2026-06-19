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
    """Contexto mínimo compartido: datos del usuario en sesión."""
    u = request.user
    if not u.is_authenticated:
        return {}
    return {
        'session_nombre': u.nombre_completo,
        'session_rol':    u.rol,
        'session_usuario': u.usuario,
    }


# ── LOGIN ──────────────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('principal')

    if request.method == 'POST':
        identificacion = request.POST.get('usuario_input', '').strip()
        clave          = request.POST.get('clave_input', '')
        es_ajax        = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        try:
            usuario = Usuario.objects.get(identificacion=identificacion, activo=True)
            user    = authenticate(request, username=usuario.username, password=clave)
            if user:
                login(request, user)
                _set_session(request, usuario)
                if es_ajax:
                    return JsonResponse({'ok': True, 'redirect': '/'})
                return redirect('principal')
            else:
                err = 'Número de identificación o contraseña incorrectos.'
                if es_ajax:
                    return JsonResponse({'ok': False, 'error': err})
                messages.error(request, err)
        except Usuario.DoesNotExist:
            err = 'Número de identificación o contraseña incorrectos.'
            if es_ajax:
                return JsonResponse({'ok': False, 'error': err})
            messages.error(request, err)

    ctx = {}
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
        'usuarios': usuarios,
        'total_usuarios': usuarios.count(),
    }
    return render(request, 'usuarios_lista.html', ctx)


# ── CREAR USUARIO ──────────────────────────────────────────────────────────────

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
            }
            return render(request, 'crear_usuario.html', ctx)
        else:
            for campo, errores in form.errors.items():
                for error in errores:
                    messages.error(request, error)

    ctx = {
        **_ctx_base(request),
        'form': form,
    }
    return render(request, 'crear_usuario.html', ctx)


# ── EDITAR USUARIO ─────────────────────────────────────────────────────────────

def editar_usuario(request, pk):
    if not request.user.is_authenticated:
        return redirect('login')
    if not _solo_admin(request):
        return JsonResponse({'ok': False, 'error': 'Sin permisos.'}, status=403)

    usuario = get_object_or_404(Usuario, pk=pk)

    # GET AJAX → devuelve JSON con datos del usuario
    if request.method == 'GET' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'ok':             True,
            'pk':             usuario.pk,
            'nombre':         usuario.nombre,
            'apellidos':      usuario.apellidos,
            'email':          usuario.email or '',
            'usuario':        usuario.usuario,
            'rol':            usuario.rol,
            'activo':         usuario.activo,
            'fecha_registro': usuario.fecha_registro.strftime('%d/%m/%Y'),
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
        elif rol not in ['admin', 'cajero', 'empleado']:
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
            ctx = {
                **_ctx_base(request),
                'perfil': usuario,
            }
            return render(request, 'editar_usuario.html', ctx)

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
                'ok':            True,
                'mensaje':       f'Usuario {usuario.usuario} actualizado.',
                'nombre_completo': usuario.nombre_completo,
                'rol_label':     usuario.get_rol_display(),
            })

        messages.success(request, f'Usuario {usuario.usuario} actualizado correctamente.')
        return redirect('usuario')

    ctx = {
        **_ctx_base(request),
        'perfil': usuario,
    }
    return render(request, 'editar_usuario.html', ctx)


# ── PERFIL DATOS (JSON) ────────────────────────────────────────────────────────

def perfil_datos(request):
    if not request.user.is_authenticated:
        return JsonResponse({'ok': False, 'error': 'Sin sesión.'})

    u = request.user
    return JsonResponse({
        'ok':           True,
        'nombre':       u.nombre,
        'apellidos':    u.apellidos,
        'usuario':      u.usuario,
        'email':        u.email or '',
        'tipo_id':      u.tipo_id,
        'tipo_id_label': u.get_tipo_id_display(),
        'identificacion': u.identificacion,
        'rol':          u.rol,
        'rol_label':    u.get_rol_display(),
        'fecha_registro': u.fecha_registro.strftime('%d/%m/%Y'),
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
        request.session['usuario_nombre'] = usuario.nombre_completo
        return JsonResponse({'ok': True, 'nombre_completo': usuario.nombre_completo})

    return JsonResponse({'ok': False, 'error': 'Acción no reconocida.'})


# ── RECUPERAR CLAVE (CORREO) ───────────────────────────────────────────────────

def solicitar_recuperacion(request):
    if request.method == 'POST':
        es_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        correo  = request.POST.get('correo', '').strip().lower()

        try:
            usuario = Usuario.objects.get(email__iexact=correo, activo=True)
        except Usuario.DoesNotExist:
            if es_ajax:
                return JsonResponse({'ok': False, 'error': 'No existe una cuenta activa con ese correo.'})
            messages.error(request, 'No existe una cuenta activa con ese correo.')
            return redirect('login')

        token  = get_random_string(32)
        expira = timezone.now() + timedelta(minutes=15)
        usuario.reset_token        = token
        usuario.reset_token_expira = expira
        usuario.save(update_fields=['reset_token', 'reset_token_expira'])

        link   = request.build_absolute_uri(f'/usuarios/restablecer/{token}/')
        cuerpo = (
            f'Hola {usuario.nombre},\n\n'
            f'Recibimos una solicitud para restablecer la contraseña de tu cuenta en CYS Ltda.\n\n'
            f'Haz clic en el siguiente enlace para crear una nueva contraseña:\n\n{link}\n\n'
            f'Este enlace expirará en 15 minutos.\n\n'
            f'Si no solicitaste este cambio, ignora este mensaje.\n\n'
            f'CYS Ltda'
        )

        try:
            _enviar_correo(usuario.email, 'Recuperación de contraseña — CYS Ltda', cuerpo)
            if es_ajax:
                return JsonResponse({'ok': True, 'mensaje': f'Enlace enviado a {usuario.email}'})
            messages.success(request, f'Enlace enviado a {usuario.email}')
        except Exception as e:
            logger.error(f'[CYS EMAIL] Error al enviar correo a {usuario.email}: {e}')
            if es_ajax:
                return JsonResponse({'ok': False, 'error': 'No se pudo enviar el correo. Intenta más tarde.'})
            messages.error(request, 'No se pudo enviar el correo. Intenta más tarde.')

    return redirect('login')


# ── RECUPERAR CLAVE (TELÉFONO) ─────────────────────────────────────────────────

def recuperar_por_telefono(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido.'})

    telefono       = request.POST.get('telefono', '').strip()
    identificacion = request.POST.get('identificacion', '').strip()

    if not telefono or not identificacion:
        return JsonResponse({'ok': False, 'error': 'Ingresa tu número de teléfono e identificación.'})

    try:
        usuario = Usuario.objects.get(
            telefono=telefono,
            identificacion=identificacion,
            activo=True,
        )
    except Usuario.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'No existe una cuenta activa con esos datos.'})

    codigo = str(random.randint(100000, 999999))
    expira = timezone.now() + timedelta(minutes=15)

    usuario.reset_token        = codigo
    usuario.reset_token_expira = expira
    usuario.save(update_fields=['reset_token', 'reset_token_expira'])

    logger.warning(
        f'[CYS RESET] Código para {usuario.nombre_completo} '
        f'(ID: {usuario.identificacion}, Tel: {usuario.telefono}): {codigo} '
        f'— expira en 15 min'
    )
    print(f'\n🔑 CÓDIGO DE RECUPERACIÓN para {usuario.nombre_completo}: {codigo}\n')

    return JsonResponse({
        'ok':     True,
        'mensaje': 'Código generado. El administrador te lo comunicará en breve.',
    })


# ── VERIFICAR CÓDIGO TELÉFONO ──────────────────────────────────────────────────

def verificar_codigo_telefono(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido.'})

    telefono       = request.POST.get('telefono', '').strip()
    identificacion = request.POST.get('identificacion', '').strip()
    codigo         = request.POST.get('codigo', '').strip()

    if not telefono or not identificacion or not codigo:
        return JsonResponse({'ok': False, 'error': 'Datos incompletos.'})

    try:
        usuario = Usuario.objects.get(
            telefono=telefono,
            identificacion=identificacion,
            reset_token=codigo,
            activo=True,
        )
    except Usuario.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Código incorrecto.'})

    if timezone.now() > usuario.reset_token_expira:
        Usuario.objects.filter(pk=usuario.pk).update(reset_token=None, reset_token_expira=None)
        return JsonResponse({'ok': False, 'error': 'El código expiró. Solicita uno nuevo.'})

    token  = get_random_string(32)
    expira = timezone.now() + timedelta(minutes=10)
    usuario.reset_token        = token
    usuario.reset_token_expira = expira
    usuario.save(update_fields=['reset_token', 'reset_token_expira'])

    return JsonResponse({'ok': True, 'redirect': f'/usuarios/restablecer/{token}/'})


# ── RESTABLECER CLAVE ──────────────────────────────────────────────────────────

def restablecer_clave(request, token):
    try:
        usuario = Usuario.objects.get(reset_token=token, activo=True)
    except Usuario.DoesNotExist:
        ctx = {'error': 'El enlace no es válido o ya fue utilizado.'}
        return render(request, 'restablecer_clave.html', ctx)

    if timezone.now() > usuario.reset_token_expira:
        Usuario.objects.filter(pk=usuario.pk).update(reset_token=None, reset_token_expira=None)
        ctx = {'error': 'El enlace expiró. Solicita uno nuevo.'}
        return render(request, 'restablecer_clave.html', ctx)

    if request.method == 'POST':
        nueva     = request.POST.get('nueva_clave', '')
        confirmar = request.POST.get('confirmar', '')
        error     = _validar_clave_segura(nueva)

        if error:
            ctx = {'token': token, 'error': error}
            return render(request, 'restablecer_clave.html', ctx)
        if nueva != confirmar:
            ctx = {'token': token, 'error': 'Las contraseñas no coinciden.'}
            return render(request, 'restablecer_clave.html', ctx)

        usuario.set_password(nueva)
        usuario.save(update_fields=['password'])
        Usuario.objects.filter(pk=usuario.pk).update(reset_token=None, reset_token_expira=None)
        ctx = {'exito': True}
        return render(request, 'restablecer_clave.html', ctx)

    ctx = {'token': token}
    return render(request, 'restablecer_clave.html', ctx)


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
    if usuario.pk == request.session.get('usuario_id'):
        return JsonResponse({'ok': False, 'error': 'No puedes eliminar tu propia cuenta.'})

    usuario.delete()
    return JsonResponse({'ok': True, 'mensaje': 'Usuario eliminado correctamente.'})


# ── PERFIL PÁGINA ──────────────────────────────────────────────────────────────

@login_required
def perfil_pagina(request):
    u = request.user
    ctx = {
        **_ctx_base(request),
        'nombre':          u.first_name,
        'apellidos':       u.last_name,
        'usuario':         u.username,
        'email':           u.email,
        'rol':             u.rol,
        'rol_label':       u.get_rol_display(),
        'tipo_id':         u.tipo_id,
        'tipo_id_label':   u.get_tipo_id_display(),
        'fecha_registro':  u.date_joined.strftime('%d/%m/%Y'),
        'identificacion':  u.identificacion,
        'telefono':        u.telefono or '—',
        'tiene_foto':      bool(u.foto),
        'foto_url':        u.foto.url if u.foto else None,
        'avatar_name':     u.avatar_name,
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