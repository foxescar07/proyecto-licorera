import pandas as pd
import mysql.connector
from mysql.connector import Error

# CONFIGURACIÓN DE CONEXIÓN A MYSQL
config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'vanessaaza2005*',
    'database': 'proyecto_licorera',
    'port': 3307
}

# RUTA DEL ARCHIVO EXCEL
archivo_excel = r"C:\Users\Asus\Downloads\FEB 2026 (1).xlsx"

try:
    # Conectar a MySQL
    conexion = mysql.connector.connect(**config)
    cursor = conexion.cursor()
    print("✓ Conexión a MySQL exitosa")

    # Leer el Excel (hoja PLAZA)
    print("\n📂 Leyendo archivo Excel...")
    df = pd.read_excel(archivo_excel, sheet_name='PLAZA')

    # Limpiar datos
    df = df.dropna(how='all')  # Eliminar filas vacías
    df = df.fillna('')  # Reemplazar NaN con vacío

    # Extraer datos de productos (columnas A y B tienen categoría y nombre)
    productos_insertados = 0
    productos_saltados = 0

    print(f"\n📊 Procesando {len(df)} filas...")

    for idx, fila in df.iterrows():
        # Columna A = Categoría, Columna B = Nombre del producto
        categoria = str(fila.iloc[0]).strip() if pd.notna(fila.iloc[0]) else ""
        nombre = str(fila.iloc[1]).strip() if pd.notna(fila.iloc[1]) else ""

        # Saltar filas sin nombre de producto
        if not nombre or nombre.lower() in ['', 'nan', 'none']:
            productos_saltados += 1
            continue

        # Obtener cantidad total (usualmente en columna con nombre "CANTIDAD TOTAL")
        cantidad = 0
        precio = 0

        try:
            # Buscar columna de CANTIDAD TOTAL
            for col_idx, valor in enumerate(fila):
                if pd.notna(valor) and isinstance(valor, (int, float)) and valor > 0:
                    cantidad += int(valor)
        except:
            cantidad = 0

        # Crear código del producto (categoria_nombre)
        codigo = f"{categoria[:10]}_{nombre[:10]}".replace(" ", "_").upper()[:30]

        try:
            # Insertar en la base de datos
            sql = """
            INSERT INTO productos_producto
            (codigo, nombre, descripcion, cantidad_disponible, precio_unitario, unidad, categoria_id, activo)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """

            valores = (
                codigo,  # codigo
                nombre,  # nombre
                f"Categoría: {categoria}",  # descripcion
                cantidad,  # cantidad_disponible
                0.00,  # precio_unitario (lo puedes actualizar después)
                "unidad",  # unidad
                1,  # categoria_id (ajusta según tu categoría)
                1  # activo
            )

            cursor.execute(sql, valores)
            productos_insertados += 1

        except Error as err:
            if "Duplicate entry" in str(err):
                print(f"⚠️  Producto duplicado: {nombre}")
            else:
                print(f"❌ Error al insertar {nombre}: {err}")
            productos_saltados += 1

    # Confirmar cambios
    conexion.commit()

    print(f"\n✅ IMPORTACIÓN COMPLETADA")
    print(f"   ✓ Productos insertados: {productos_insertados}")
    print(f"   ⚠️  Productos saltados: {productos_saltados}")

except Error as err:
    print(f"❌ Error de conexión a MySQL: {err}")
except Exception as err:
    print(f"❌ Error general: {err}")
finally:
    if conexion.is_connected():
        cursor.close()
        conexion.close()
        print("\n✓ Conexión cerrada")
