import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection
cursor = connection.cursor()

cursor.execute("PRAGMA table_info(inventario_movimientoinventario)")
print("Columnas en inventario_movimientoinventario:")
for row in cursor.fetchall():
    print(row)
