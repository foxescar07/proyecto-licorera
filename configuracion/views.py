import os
import shutil
from datetime import datetime
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db import connection

from .models import ConfiguracionEmpresa, BackupRegistro


# ── Helpers ────────────────────────────────────────────────

def _db_stats():
    """Estadísticas básicas de la base de datos SQLite."""
    stats = {'registros': 0, 'tablas': 0, 'tamaño': '—'}
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            stats['tablas'] = cur.fetchone()[0]

            tables = connection.introspection.table_names()
            total  = 0
            for t in tables:
                try:
                    cur.execute(f'SELECT COUNT(*) FROM "{t}"')
                    total += cur.fetchone()[0]
                except Exception:
                    pass
            stats['registros'] = total

        db_path = settings.DATABASES['default']['NAME']
        if os.path.exists(db_path):
            size_bytes = os.path.getsize(db_path)
            if size_bytes < 1024 * 1024:
                stats['tamaño'] = f'{size_bytes / 1024:.1f} KB'
            else:
                stats['tamaño'] = f'{size_bytes / (1024 * 1024):.2f} MB'
    except Exception:
        pass
    return stats


def _es_admin(request):
    return request.user.is_authenticated and request.user.rol == 'admin'


# ── Vistas ─────────────────────────────────────────────────

@login_required
def index(request):
    config  = ConfiguracionEmpresa.get_config()
    backups = BackupRegistro.objects.all()[:10]

    # La sección de "info de empresa" siempre arranca bloqueada en cada
    # carga de página, sin importar si ya se desbloqueó antes en la sesión.
    request.session.pop('empresa_desbloqueada', None)

    context = {
        'config':   config,
        'db_stats': _db_stats(),
        'backups':  backups,
        'es_admin_empresa': _es_admin(request),
        'breadcrumb_items': [
            {'nombre': 'Configuración', 'url': None},
        ],
    }
    return render(request, 'configuracion.html', context)


@login_required
@require_POST
def verificar_clave_empresa(request):
    """Valida la contraseña del admin y, si es correcta, entrega los
    datos reales de la empresa junto con el permiso de sesión para
    poder guardarlos después."""
    if not _es_admin(request):
        return JsonResponse({'ok': False, 'error': 'Solo el administrador puede ver esta información.'}, status=403)

    clave = request.POST.get('clave', '')
    if not clave:
        return JsonResponse({'ok': False, 'error': 'Ingresa tu contraseña.'})

    if not request.user.check_password(clave):
        return JsonResponse({'ok': False, 'error': 'Contraseña incorrecta.'})

    request.session['empresa_desbloqueada'] = True

    config = ConfiguracionEmpresa.get_config()
    return JsonResponse({
        'ok': True,
        'empresa': {
            'nombre_empresa': config.nombre_empresa,
            'nit':            config.nit,
            'direccion':      config.direccion,
            'telefono':       config.telefono,
            'email':          config.email,
        }
    })


@login_required
@require_POST
def bloquear_empresa(request):
    """Vuelve a bloquear la sección sin necesidad de recargar la página."""
    request.session.pop('empresa_desbloqueada', None)
    return JsonResponse({'ok': True})


@login_required
@require_POST
def guardar_empresa(request):
    if not _es_admin(request):
        return JsonResponse({'ok': False, 'error': 'Solo el administrador puede editar esta información.'}, status=403)

    if not request.session.get('empresa_desbloqueada'):
        return JsonResponse({'ok': False, 'error': 'Debes verificar tu contraseña antes de guardar.'}, status=403)

    config = ConfiguracionEmpresa.get_config()
    config.nombre_empresa = request.POST.get('nombre_empresa', config.nombre_empresa).strip()
    config.nit            = request.POST.get('nit',       config.nit).strip()
    config.direccion      = request.POST.get('direccion', config.direccion).strip()
    config.telefono       = request.POST.get('telefono',  config.telefono).strip()
    config.email          = request.POST.get('email',     config.email).strip()
    config.save()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def guardar_impuestos(request):
    config = ConfiguracionEmpresa.get_config()
    try:
        config.iva_porcentaje = float(request.POST.get('iva_porcentaje', config.iva_porcentaje))
    except (ValueError, TypeError):
        pass
    config.moneda = request.POST.get('moneda', config.moneda)

    # Las unidades vienen como lista de valores desde el JS (ver nota en urls)
    unidades = request.POST.getlist('unidades[]')
    if unidades:
        config.unidades_medida = [u.strip() for u in unidades if u.strip()]
    config.save()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def crear_backup(request):
    try:
        db_path = settings.DATABASES['default']['NAME']
        if not os.path.exists(db_path):
            return JsonResponse({'ok': False, 'error': 'BD no encontrada'})

        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)

        timestamp   = datetime.now().strftime('%Y%m%d_%H%M%S')
        nombre      = f'backup_{timestamp}.sqlite3'
        dest_path   = os.path.join(backup_dir, nombre)

        shutil.copy2(db_path, dest_path)

        size_bytes = os.path.getsize(dest_path)
        if size_bytes < 1024 * 1024:
            tamaño_str = f'{size_bytes / 1024:.1f} KB'
        else:
            tamaño_str = f'{size_bytes / (1024 * 1024):.2f} MB'

        registro = BackupRegistro.objects.create(
            nombre    = nombre,
            ruta      = dest_path,
            tamaño_mb = round(size_bytes / (1024 * 1024), 4),
        )

        return JsonResponse({
            'ok':    True,
            'nombre': nombre,
            'fecha':  registro.fecha.strftime('%d/%m/%Y %H:%M'),
            'tamaño': tamaño_str,
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})