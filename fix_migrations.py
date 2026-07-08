#!/usr/bin/env python
"""
Script para arreglar la inconsistencia de migraciones en Django.
Marca las migraciones faltantes como aplicadas en la tabla django_migrations.
"""
import os
import django
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection
from django.db.migrations.recorder import MigrationRecorder

# Las migraciones que necesitan estar marcadas como aplicadas
missing_migrations = [
    ('productos', '0002_producto_activo_delete_inventario'),
    ('ventas', '0003_alter_cierrecaja_apertura'),
]

recorder = MigrationRecorder(connection)

print("Migraciones que necesitan ser marcadas como aplicadas:")
for app, migration in missing_migrations:
    print(f"  - {app}.{migration}")

print("\nMarcando migraciones como aplicadas...")
for app, migration in missing_migrations:
    try:
        # Verificar si ya está registrada
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT 1 FROM django_migrations WHERE app = %s AND name = %s',
                [app, migration]
            )
            if not cursor.fetchone():
                recorder.record_applied(app, migration)
                print(f"✓ Aplicada: {app}.{migration}")
            else:
                print(f"✓ Ya estaba aplicada: {app}.{migration}")
    except Exception as e:
        print(f"✗ Error al aplicar {app}.{migration}: {e}")

print("\nHecho! Ahora puedes ejecutar: python manage.py migrate")
