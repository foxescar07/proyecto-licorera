import MySQLdb

try:
    conn = MySQLdb.connect(
        host='localhost',
        user='root',
        passwd='vanesaaza2005*',
        port=3306
    )
    cursor = conn.cursor()
    cursor.execute('CREATE DATABASE IF NOT EXISTS proyecto_licorera DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
    print('✓ Base de datos creada: proyecto_licorera')
    cursor.close()
    conn.close()
except Exception as e:
    print(f'✗ Error: {e}')
