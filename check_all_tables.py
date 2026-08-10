import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection
cursor = connection.cursor()

tables_to_check = [
    'inventario_lote',
    'inventario_inventario',
    'inventario_agendainventario',
    'inventario_hallazgo'
]

for table in tables_to_check:
    print(f"\n=== {table} ===")
    cursor.execute(f"PRAGMA table_info({table})")
    for row in cursor.fetchall():
        print(f"  {row[1]}: {row[2]} (pk={row[5]})")
