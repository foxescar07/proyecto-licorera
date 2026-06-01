from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.crypto import get_random_string
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from .models import Perfil
from .forms import UsuarioForm

import ssl
import smtplib
import re

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


EMAIL_USER = 'ccanariasogamoso@gmail.com'
EMAIL_PASS = 'jmcikwsvajdmbzab'


def _enviar_correo(destinatario, asunto, cuerpo):
    mensaje = MIMEMultipart()
    mensaje['Subject'] = asunto
    mensaje['From'] = f'CYS Ltda <{EMAIL_USER}>'
    mensaje['To'] = destinatario

    mensaje.attach(MIMEText(cuerpo, 'plain'))

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    with smtplib.SMTP('smtp.gmail.com', 587) as s:
        s.ehlo()
        s.starttls(context=ctx)
        s.ehlo()
        s.login(EMAIL_USER, EMAIL_PASS)
        s.sendmail(EMAIL_USER, destinatario, mensaje.as_string())


def _validar_clave_segura(clave):
    if len(clave) < 6:
        return 'La contraseña debe tener al menos 6 caracteres.'
    if len(re.findall(r'\d', clave)) < 2:
        return 'La contraseña debe contener al menos 2 números.'
    if not re.search(r'[A-Z]', clave):
        return 'La contraseña debe contener al menos 1 mayúscula.'
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


# ── LOGIN ─────────────────────────────────────────────────────────────────────
def login_view(request):

    if request.user.is_authenticated:
        return redirect('principal')

    if request.method == 'POST':

        identificacion = request.POST.get('usuario_input', '').strip()
        clave          = request.POST.get('clave_input', '')
        es_ajax        = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        try:
            perfil = Perfil.objects.select_related('user').get(
                identificacion=identificacion,
                activo=True
            )
            user = authenticate(request, username=perfil.user.username, password=clave)

            if user:
                login(request, user)
                _set_session(request, perfil)
                if es_ajax:
                    return JsonResponse({'ok': True, 'redirect': '/'})
                return redirect('principal')
            else:
                if es_ajax:
                    return JsonResponse({'ok': False, 'error': 'Número de identificación o contraseña incorrectos.'})
                messages.error(request, 'Número de identificación o contraseña incorrectos.')

        except Perfil.DoesNotExist:
            if es_ajax:
                return JsonResponse({'ok': False, 'error': 'Número de identificación o contraseña incorrectos.'})
            messages.error(request, 'Número de identificación o contraseña incorrectos.')

    return render(request, 'usuario.html')


# ── LOGOUT ────────────────────────────────────────────────────────────────────
def logout_view(request):
    logout(request)
    request.session.flush()
    response = redirect('login')
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
    response['Pragma']        = 'no-cache'
    response['Expires']       = '0'
    return response


# ── LISTA USUARIOS ────────────────────────────────────────────────────────────
def lista_usuarios(request):

    if not request.user.is_authenticated:
        return redirect('login')

    list(messages.get_messages(request))

    usuarios = Perfil.objects.select_related('user').order_by('-user__date_joined')

    return render(request, 'usuarios_lista.html', {'usuarios': usuarios})


# ── CREAR USUARIO ─────────────────────────────────────────────────────────────
def crear_usuario(request):

    form = UsuarioForm()

    if request.method == 'POST':
        form = UsuarioForm(request.POST)
        if form.is_valid():
            perfil = form.save()
            return render(request, 'crear_usuario.html', {
                'form': form,
                'usuario_creado': True,
                'nuevo_usuario': perfil.usuario,
            })
        else:
            for campo, errores in form.errors.items():
                for error in errores:
                    messages.error(request, error)

    return render(request, 'crear_usuario.html', {'form': form})


# ── EDITAR USUARIO ────────────────────────────────────────────────────────────
def editar_usuario(request, pk):

    if not request.user.is_authenticated:
        return redirect('login')

    if not _solo_admin(request):
        return JsonResponse({'ok': False, 'error': 'Sin permisos.'}, status=403)

    perfil = get_object_or_404(Perfil, pk=pk)

    if request.method == 'GET' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'ok':             True,
            'pk':             perfil.pk,
            'nombre':         perfil.nombre,
            'apellidos':      perfil.apellidos,
            'email':          perfil.email or '',
            'usuario':        perfil.usuario,
            'rol':            perfil.rol,
            'activo':         perfil.activo,
            'fecha_registro': perfil.fecha_registro.strftime('%d/%m/%Y'),
        })

    if request.method == 'POST':

        es_ajax   = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        nombre    = request.POST.get('nombre', '').strip()
        apellidos = request.POST.get('apellidos', '').strip()
        email     = request.POST.get('email', '').strip().lower()
        rol       = request.POST.get('rol', '').strip()
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

        if clave_nueva and not error:
            error = _validar_clave_segura(clave_nueva)

        if error:
            if es_ajax:
                return JsonResponse({'ok': False, 'error': error})
            messages.error(request, error)
            return render(request, 'editar_usuario.html', {'perfil': perfil})

        perfil.user.first_name = nombre
        perfil.user.last_name  = apellidos
        perfil.user.email      = email or ''
        perfil.user.save(update_fields=['first_name', 'last_name', 'email'])

        perfil.rol = rol
        perfil.save(update_fields=['rol'])

        if clave_nueva:
            perfil.user.set_password(clave_nueva)
            perfil.user.save(update_fields=['password'])

        if es_ajax:
            return JsonResponse({
                'ok':            True,
                'mensaje':       f'Usuario {perfil.usuario} actualizado.',
                'nombre_completo': perfil.nombre_completo,
                'rol_label':     perfil.get_rol_display(),
            })

        messages.success(request, f'Usuario {perfil.usuario} actualizado correctamente.')
        return redirect('usuario')

    return render(request, 'editar_usuario.html', {'perfil': perfil})


# ── PERFIL DATOS (JSON) ───────────────────────────────────────────────────────
def perfil_datos(request):

    if not request.user.is_authenticated:
        return JsonResponse({'ok': False, 'error': 'Sin sesión.'})

    perfil = request.user.perfil

    return JsonResponse({
        'ok':             True,
        'nombre':         perfil.nombre,
        'apellidos':      perfil.apellidos,
        'usuario':        perfil.usuario,
        'email':          perfil.email or '',
        'tipo_id':        perfil.tipo_id,
        'tipo_id_label':  perfil.get_tipo_id_display(),
        'identificacion': perfil.identificacion,
        'rol':            perfil.rol,
        'rol_label':      perfil.get_rol_display(),
        'fecha_registro': perfil.fecha_registro.strftime('%d/%m/%Y'),
    })


# ── PERFIL EDITAR (JSON) ──────────────────────────────────────────────────────
def perfil_editar(request):

    if not request.user.is_authenticated:
        return JsonResponse({'ok': False, 'error': 'Sin sesión.'})

    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido.'})

    perfil      = request.user.perfil
    nombre      = request.POST.get('nombre', '').strip()
    apellidos   = request.POST.get('apellidos', '').strip()
    email       = request.POST.get('email', '').strip().lower()
    clave_nueva = request.POST.get('clave_nueva', '').strip()
    clave_actual = request.POST.get('clave_actual', '').strip()

    if not nombre or not apellidos:
        return JsonResponse({'ok': False, 'error': 'Nombre y apellidos son obligatorios.'})
    if any(c.isdigit() for c in nombre):
        return JsonResponse({'ok': False, 'error': 'El nombre no debe contener números.'})
    if any(c.isdigit() for c in apellidos):
        return JsonResponse({'ok': False, 'error': 'Los apellidos no deben contener números.'})

    if email and email != (perfil.email or '').lower():
        if User.objects.filter(email__iexact=email).exclude(pk=perfil.user.pk).exists():
            return JsonResponse({'ok': False, 'error': 'Este correo ya está en uso.'})

    if clave_nueva:
        if not clave_actual:
            return JsonResponse({'ok': False, 'error': 'Ingresa tu contraseña actual.'})
        if not perfil.user.check_password(clave_actual):
            return JsonResponse({'ok': False, 'error': 'La contraseña actual es incorrecta.'})
        err = _validar_clave_segura(clave_nueva)
        if err:
            return JsonResponse({'ok': False, 'error': err})

    perfil.user.first_name = nombre
    perfil.user.last_name  = apellidos
    perfil.user.email      = email or ''
    perfil.user.save(update_fields=['first_name', 'last_name', 'email'])

    if clave_nueva:
        perfil.user.set_password(clave_nueva)
        perfil.user.save(update_fields=['password'])
        update_session_auth_hash(request, perfil.user)

    request.session['usuario_nombre'] = perfil.nombre_completo

    return JsonResponse({
        'ok':             True,
        'mensaje':        'Perfil actualizado correctamente.',
        'nombre_completo': perfil.nombre_completo,
    })


# ── RECUPERAR CLAVE ───────────────────────────────────────────────────────────
def solicitar_recuperacion(request):

    if request.method == 'POST':

        es_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        correo  = request.POST.get('correo', '').strip().lower()

        try:
            user   = User.objects.get(email__iexact=correo, is_active=True)
            perfil = Perfil.objects.get(user=user, activo=True)
        except (User.DoesNotExist, Perfil.DoesNotExist):
            if es_ajax:
                return JsonResponse({'ok': False, 'error': 'No existe una cuenta activa con ese correo.'})
            messages.error(request, 'No existe una cuenta activa con ese correo.')
            return redirect('login')

        token  = get_random_string(32)
        expira = timezone.now() + timedelta(minutes=15)

        perfil.reset_token        = token
        perfil.reset_token_expira = expira
        perfil.save(update_fields=['reset_token', 'reset_token_expira'])

        link  = request.build_absolute_uri(f'/usuarios/restablecer/{token}/')
        cuerpo = (
            f'Hola {perfil.nombre},\n\n'
            f'Haz clic en el siguiente enlace:\n\n'
            f'{link}\n\n'
            f'El enlace expirará en 15 minutos.\n\n'
            f'CYS Ltda'
        )

        try:
            _enviar_correo(perfil.user.email, 'Recuperación de contraseña - CYS Ltda', cuerpo)
            if es_ajax:
                return JsonResponse({'ok': True, 'mensaje': f'Enlace enviado a {perfil.user.email}'})
            messages.success(request, f'Enlace enviado a {perfil.user.email}')
        except Exception as e:
            if es_ajax:
                return JsonResponse({'ok': False, 'error': str(e)})
            messages.error(request, str(e))

    return redirect('login')


# ── RESTABLECER CLAVE ─────────────────────────────────────────────────────────
def restablecer_clave(request, token):

    try:
        perfil = Perfil.objects.select_related('user').get(reset_token=token, activo=True)
    except Perfil.DoesNotExist:
        return render(request, 'restablecer_clave.html', {'error': 'El enlace no es válido o ya fue utilizado.'})

    if timezone.now() > perfil.reset_token_expira:
        Perfil.objects.filter(pk=perfil.pk).update(reset_token=None, reset_token_expira=None)
        return render(request, 'restablecer_clave.html', {'error': 'El enlace expiró. Solicita uno nuevo.'})

    if request.method == 'POST':

        nueva     = request.POST.get('nueva_clave', '')
        confirmar = request.POST.get('confirmar', '')
        error     = _validar_clave_segura(nueva)

        if error:
            return render(request, 'restablecer_clave.html', {'token': token, 'error': error})

        if nueva != confirmar:
            return render(request, 'restablecer_clave.html', {'token': token, 'error': 'Las contraseñas no coinciden.'})

        perfil.user.set_password(nueva)
        perfil.user.save(update_fields=['password'])
        Perfil.objects.filter(pk=perfil.pk).update(reset_token=None, reset_token_expira=None)

        return render(request, 'restablecer_clave.html', {'exito': True})

    return render(request, 'restablecer_clave.html', {'token': token})


# ── TOGGLE ACTIVO ─────────────────────────────────────────────────────────────
def toggle_activo(request, pk):

    if not request.user.is_authenticated:
        return redirect('login')

    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido.'})

    perfil          = get_object_or_404(Perfil, pk=pk)
    perfil.activo   = not perfil.activo
    perfil.user.is_active = perfil.activo
    perfil.save()
    perfil.user.save()

    return JsonResponse({'ok': True, 'activo': perfil.activo})


# ── ELIMINAR USUARIO ──────────────────────────────────────────────────────────
def eliminar_usuario(request, pk):

    if not request.user.is_authenticated:
        return redirect('login')

    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido.'})

    perfil = get_object_or_404(Perfil, pk=pk)

    if perfil.pk == request.session.get('usuario_id'):
        return JsonResponse({'ok': False, 'error': 'No puedes eliminar tu propia cuenta.'})

    perfil.user.delete()

    return JsonResponse({'ok': True, 'mensaje': 'Usuario eliminado correctamente.'})


# ── PERFIL PÁGINA ─────────────────────────────────────────────────────────────
@login_required
def perfil_pagina(request):

    perfil = request.user.perfil

    ctx = {
        'nombre':         request.user.first_name,
        'apellidos':      request.user.last_name,
        'usuario':        request.user.username,
        'email':          request.user.email,
        'rol':            perfil.rol,
        'rol_label':      perfil.get_rol_display(),
        'tipo_id':        perfil.tipo_id,
        'tipo_id_label':  perfil.get_tipo_id_display(),
        'fecha_registro': request.user.date_joined.strftime('%d/%m/%Y'),
        'identificacion': perfil.identificacion,
        'telefono':       getattr(perfil, 'telefono', None) or '—',
    }

    return render(request, 'perfil.html', ctx)