#!/usr/bin/env python
import os
import sys
import shutil

# ANSI colors for beautiful terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def get_project_root():
    # The script is in project_root/scripts/
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def find_files_to_purge():
    project_root = get_project_root()
    migrations_files = []
    pycache_dirs = []
    database_files = []

    # Common virtual environment and system directories to ignore (case-insensitive)
    ignored_dir_names = {
        '.git', '.venv', 'venv', 'env', '.vscode', 'node_modules', 
        'lib', 'libs', 'site-packages', 'include', 'bin', 'share', 'obj'
    }

    for root, dirs, files in os.walk(project_root):
        # Filter directories to avoid traversing virtual envs and system folders
        filtered_dirs = []
        for d in dirs:
            # Check if directory name is in ignored names (case-insensitive)
            if d.lower() in ignored_dir_names:
                continue
            # Check if directory looks like a virtual env (contains pyvenv.cfg)
            if os.path.exists(os.path.join(root, d, 'pyvenv.cfg')):
                continue
            filtered_dirs.append(d)
        
        dirs[:] = filtered_dirs

        # Check for database files in the root folder
        if root == project_root:
            for file in files:
                if file.endswith('.sqlite3'):
                    database_files.append(os.path.join(root, file))

        # Check for migration files
        parts = os.path.split(root)
        if parts[-1] == 'migrations':
            for file in files:
                if file.endswith('.py') and file != '__init__.py':
                    migrations_files.append(os.path.join(root, file))

        # Track __pycache__ directories inside migration folders to clean them up too
        if parts[-1] == '__pycache__' and len(parts) > 1 and os.path.split(parts[0])[-1] == 'migrations':
            pycache_dirs.append(root)

    return database_files, migrations_files, pycache_dirs

def main():
    print(f"{Colors.HEADER}{Colors.BOLD}=== PURGADOR DE MIGRACIONES Y BASE DE DATOS ==={Colors.ENDC}\n")

    db_files, mig_files, pycache_dirs = find_files_to_purge()
    project_root = get_project_root()

    if not db_files and not mig_files:
        print(f"{Colors.GREEN}No se encontraron bases de datos ni archivos de migración para purgar.{Colors.ENDC}")
        return

    # List database files found
    if db_files:
        print(f"{Colors.WARNING}{Colors.BOLD}Bases de datos encontradas:{Colors.ENDC}")
        for db in db_files:
            rel_path = os.path.relpath(db, project_root)
            size_kb = os.path.getsize(db) / 1024
            print(f"  • {Colors.CYAN}{rel_path}{Colors.ENDC} ({size_kb:.2f} KB)")
        print()

    # List migration files found
    if mig_files:
        print(f"{Colors.WARNING}{Colors.BOLD}Archivos de migración encontrados:{Colors.ENDC}")
        
        # Group migrations by app
        app_migrations = {}
        for mig in mig_files:
            rel_path = os.path.relpath(mig, project_root)
            parts = rel_path.split(os.sep)
            # Typically: app_name/migrations/file.py
            app_name = parts[0] if len(parts) >= 3 else "Otros"
            if app_name not in app_migrations:
                app_migrations[app_name] = []
            app_migrations[app_name].append(parts[-1])

        for app_name, files in sorted(app_migrations.items()):
            print(f"  {Colors.BOLD}{app_name}:{Colors.ENDC}")
            for f in sorted(files):
                print(f"    - {Colors.BLUE}{f}{Colors.ENDC}")
        print()

    # Ask for confirmation
    confirm_msg = (
        f"{Colors.FAIL}{Colors.BOLD}¡ADVERTENCIA!{Colors.ENDC} Esta acción eliminará permanentemente la base de datos "
        f"y todas las migraciones listadas arriba.\n"
        f"¿Está seguro de que desea continuar? [s/N]: "
    )
    
    try:
        confirm = input(confirm_msg).strip().lower()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Operación cancelada por el usuario.{Colors.ENDC}")
        sys.exit(0)

    if confirm not in ('s', 'si', 'y', 'yes'):
        print(f"\n{Colors.GREEN}Operación cancelada.{Colors.ENDC}")
        return

    print(f"\n{Colors.BOLD}Procediendo con la purga...{Colors.ENDC}\n")

    # Delete database files
    for db in db_files:
        try:
            os.remove(db)
            print(f"[{Colors.GREEN}ELIMINADO{Colors.ENDC}] Base de datos: {os.path.relpath(db, project_root)}")
        except Exception as e:
            print(f"[{Colors.FAIL}ERROR{Colors.ENDC}] No se pudo eliminar {os.path.relpath(db, project_root)}: {e}")

    # Delete migration files
    for mig in mig_files:
        try:
            os.remove(mig)
            print(f"[{Colors.GREEN}ELIMINADO{Colors.ENDC}] Migración: {os.path.relpath(mig, project_root)}")
        except Exception as e:
            print(f"[{Colors.FAIL}ERROR{Colors.ENDC}] No se pudo eliminar {os.path.relpath(mig, project_root)}: {e}")

    # Delete __pycache__ directories inside migration folders
    for pyc in pycache_dirs:
        try:
            shutil.rmtree(pyc)
            print(f"[{Colors.GREEN}ELIMINADO{Colors.ENDC}] Pycache de migraciones: {os.path.relpath(pyc, project_root)}")
        except Exception as e:
            pass

    print(f"\n{Colors.GREEN}{Colors.BOLD}¡Purga completada con éxito!{Colors.ENDC}")
    print(f"\nPara reconstruir la base de datos y poblada de nuevo, ejecute:")
    print(f"  {Colors.CYAN}python manage.py makemigrations{Colors.ENDC}")
    print(f"  {Colors.CYAN}python manage.py migrate{Colors.ENDC}")
    print(f"  {Colors.CYAN}python scripts/populate_db.py{Colors.ENDC}")

if __name__ == '__main__':
    main()
