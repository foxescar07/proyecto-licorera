import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection

def main():
    with connection.cursor() as cursor:
        # Check applied migrations
        cursor.execute("SELECT app, name, applied FROM django_migrations ORDER BY applied ASC")
        rows = cursor.fetchall()
        print("All migrations in active database:")
        for row in rows:
            print(f" - {row[0]}.{row[1]} (applied at {row[2]})")
            
        # Check active tables
        cursor.execute("SHOW TABLES")
        tables = sorted([row[0] for row in cursor.fetchall()])
        print("\nTables in active database:")
        for t in tables:
            print(f" - {t}")

if __name__ == '__main__':
    main()
