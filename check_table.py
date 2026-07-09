import sqlite3

conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()
cur.execute("PRAGMA table_info(proveedores_compra)")
print("Columnas actuales en proveedores_compra:")
for row in cur.fetchall():
    print(f"  {row[1]}: {row[2]}")
