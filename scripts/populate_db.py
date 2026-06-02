#!/usr/bin/env python
import os
import sys
import django
import random
from decimal import Decimal
from datetime import timedelta

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.utils import timezone
from django.db import transaction

# Model Imports
from usuarios.models import Usuario
from productos.models import Categoria, Producto, PresentacionProducto, Inventario as InventarioProducto
from inventario.models import Lote, Inventario as InventarioMovimiento, SesionConteo, ConteoProducto, ResultadoInventario, AgendaInventario
from ventas.models import Cliente, Venta, DetalleVenta, AperturaCaja, CierreCaja, Devolucion, DetalleDevolucion
from reportes.models import ReporteGenerado

def run():
    print("Iniciando la población de la base de datos de Proyecto Licorera...")
    
    try:
        with transaction.atomic():
            # ----------------------------------------------------
            # CLEANING DATABASE
            # ----------------------------------------------------
            print("Limpiando datos existentes...")
            ReporteGenerado.objects.all().delete()
            DetalleDevolucion.objects.all().delete()
            Devolucion.objects.all().delete()
            CierreCaja.objects.all().delete()
            AperturaCaja.objects.all().delete()
            DetalleVenta.objects.all().delete()
            Venta.objects.all().delete()
            Cliente.objects.all().delete()
            AgendaInventario.objects.all().delete()
            ResultadoInventario.objects.all().delete()
            ConteoProducto.objects.all().delete()
            SesionConteo.objects.all().delete()
            InventarioMovimiento.objects.all().delete()
            Lote.objects.all().delete()
            InventarioProducto.objects.all().delete()
            PresentacionProducto.objects.all().delete()
            Producto.objects.all().delete()
            Categoria.objects.all().delete()
            
            # Delete all users
            Usuario.objects.all().delete()
            
            # Create a base global superuser
            superuser = Usuario.objects.create_superuser(
                username='admin_global',
                email='admin@licorera.com',
                password='admin123',
                identificacion='9999999999'
            )
            print("Superusuario 'admin_global' creado con contraseña 'admin123'.")
            
            # ----------------------------------------------------
            # 1. USUARIOS (10 Usuarios)
            # ----------------------------------------------------
            print("Creando 10 Usuarios...")
            usuarios_data = [
                ("0000000000", "Administrador", "Principal", "admin", "CC", "0000000000", "3000000000"),
                ("carlos_cajero", "Carlos", "Gómez", "cajero", "CC", "1002345671", "3001234561"),
                ("maria_admin", "María", "Rodríguez", "admin", "CC", "1002345672", "3001234562"),
                ("juan_empleado", "Juan", "Pérez", "empleado", "CC", "1002345673", "3001234563"),
                ("andrea_cajera", "Andrea", "Sánchez", "cajero", "CC", "1002345674", "3001234564"),
                ("luis_empleado", "Luis", "Martínez", "empleado", "CE", "9002345675", "3001234565"),
                ("sofia_admin", "Sofía", "López", "admin", "CC", "1002345676", "3001234566"),
                ("diego_cajero", "Diego", "Hernández", "cajero", "PA", "8002345677", "3001234567"),
                ("laura_empleado", "Laura", "Díaz", "empleado", "CC", "1002345678", "3001234568"),
                ("jorge_cajero", "Jorge", "Torres", "cajero", "TI", "1002345679", "3001234569"),
                ("ana_empleado", "Ana", "Ramírez", "empleado", "PT", "1002345680", "3001234570"),
            ]
            
            users = []
            
            for username, first_name, last_name, rol, tipo_id, identificacion, telefono in usuarios_data:
                is_admin = (rol == 'admin')
                is_super = (username == "0000000000")
                user = Usuario.objects.create_user(
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    email=f"{username}@licorera.com",
                    is_staff=is_admin or is_super,
                    is_superuser=is_super,
                    tipo_id=tipo_id,
                    identificacion=identificacion,
                    telefono=telefono,
                    rol=rol,
                    activo=True
                )
                if username == "0000000000":
                    user.set_password("@dmin123")
                else:
                    user.set_password("pass12345")
                user.save()
                users.append(user)
            
            print(f"-> Creados exitosamente {len(users)} usuarios.")

            # ----------------------------------------------------
            # 2. CATEGORIAS (10 Categorías)
            # ----------------------------------------------------
            print("Creando 10 Categorías...")
            categorias_nombres = [
                ("Aguardiente", "CAT001", "Licores tradicionales de anís"),
                ("Ron", "CAT002", "Licores destilados de caña de azúcar"),
                ("Whisky", "CAT003", "Licores de malta y granos envejecidos"),
                ("Tequila", "CAT004", "Destilados de agave azul"),
                ("Vodka", "CAT005", "Destilados neutros de grano"),
                ("Cerveza", "CAT006", "Cervezas nacionales e importadas"),
                ("Vino", "CAT007", "Vinos tintos, blancos y rosados"),
                ("Ginebra", "CAT008", "Destilados aromatizados con enebro"),
                ("Licores Dulces", "CAT009", "Cremas y digestivos dulces"),
                ("Coñac", "CAT010", "Brandis de alta calidad"),
            ]
            
            categorias = []
            for nombre, codigo, descripcion in categorias_nombres:
                cat = Categoria.objects.create(
                    codigo=codigo,
                    nombre=nombre,
                    descripcion=descripcion
                )
                categorias.append(cat)
            
            print(f"-> Creadas exitosamente {len(categorias)} categorías.")

            # ----------------------------------------------------
            # 3. PRODUCTOS (10 Productos)
            # ----------------------------------------------------
            print("Creando 10 Productos...")
            productos_data = [
                ("Aguardiente Antioqueño Sin Azúcar", "PROD001", "El tradicional aguardiente antioqueño en versión sin azúcar.", 50, Decimal("45000.00"), categorias[0]),
                ("Ron Medellín Añejo 3 Años", "PROD002", "Ron suave y madurado en barricas de roble.", 60, Decimal("50000.00"), categorias[1]),
                ("Whisky Buchanan's Deluxe 12 Años", "PROD003", "Whisky blend premium de alta calidad y sabor suave.", 25, Decimal("145000.00"), categorias[2]),
                ("Tequila José Cuervo Especial Gold", "PROD004", "Tequila reposado de gran tradición mexicana.", 30, Decimal("85000.00"), categorias[3]),
                ("Vodka Absolut Original", "PROD005", "Vodka sueco de pureza excepcional.", 40, Decimal("70000.00"), categorias[4]),
                ("Cerveza Club Colombia Dorada", "PROD006", "Cerveza tipo premium nacional tipo lager.", 120, Decimal("4000.00"), categorias[5]),
                ("Vino Tinto Gato Negro Cabernet Sauvignon", "PROD007", "Vino chileno joven de mesa con notas frutales.", 35, Decimal("35000.00"), categorias[6]),
                ("Ginebra Hendrick's Premium", "PROD008", "Ginebra escocesa infundida con pepino y rosas.", 15, Decimal("190000.00"), categorias[7]),
                ("Baileys Crema Irlandesa Original", "PROD009", "Licor cremoso a base de whisky irlandés y crema de leche.", 20, Decimal("75000.00"), categorias[8]),
                ("Coñac Hennessy VS Very Special", "PROD010", "Coñac francés de renombre con notas frutales y roble.", 10, Decimal("260000.00"), categorias[9]),
            ]
            
            productos = []
            for nombre, codigo, descripcion, cant, precio, cat in productos_data:
                prod = Producto.objects.create(
                    codigo=codigo,
                    nombre=nombre,
                    descripcion=descripcion,
                    cantidad_disponible=cant,
                    precio_unitario=precio,
                    categoria=cat
                )
                productos.append(prod)
            
            print(f"-> Creados exitosamente {len(productos)} productos.")

            # ----------------------------------------------------
            # 4. PRESENTACIONES DE PRODUCTO (10 Presentaciones)
            # ----------------------------------------------------
            print("Creando 10 Presentaciones de Producto...")
            presentaciones = []
            # Create at least 1-2 presentations per product to get 10+ presentations
            presentaciones_config = [
                (productos[0], "Botella 750ml", 1, 40, Decimal("45000.00")),
                (productos[0], "Media Botella 375ml", 1, 20, Decimal("25000.00")),
                (productos[1], "Botella 750ml", 1, 35, Decimal("50000.00")),
                (productos[2], "Botella 750ml", 1, 15, Decimal("145000.00")),
                (productos[3], "Botella 750ml", 1, 18, Decimal("85000.00")),
                (productos[4], "Botella 750ml", 1, 22, Decimal("70000.00")),
                (productos[5], "Lata 330ml", 1, 100, Decimal("4000.00")),
                (productos[5], "Six-Pack Latas", 6, 20, Decimal("22000.00")),
                (productos[6], "Botella 750ml", 1, 30, Decimal("35000.00")),
                (productos[7], "Botella 750ml", 1, 12, Decimal("190000.00")),
                (productos[8], "Botella 750ml", 1, 15, Decimal("75000.00")),
                (productos[9], "Botella 700ml", 1, 8, Decimal("260000.00")),
            ]
            
            for prod, nombre, uds, cant, precio in presentaciones_config:
                pres = PresentacionProducto.objects.create(
                    producto=prod,
                    nombre=nombre,
                    unidades=uds,
                    cantidad=cant,
                    precio=precio
                )
                presentaciones.append(pres)
                
            print(f"-> Creadas exitosamente {len(presentaciones)} presentaciones.")

            # ----------------------------------------------------
            # 5. REGISTROS DE INVENTARIO (PRODUCTOS) (10 Registros)
            # ----------------------------------------------------
            print("Creando 10 Registros de Inventario en Productos...")
            movimientos_prod = []
            motivos = ["Ingreso por compra", "Ajuste de inventario inicial", "Suministro extra de distribuidor"]
            for i in range(10):
                mov_p = InventarioProducto.objects.create(
                    producto=productos[i % len(productos)],
                    tipo=random.choice(['entrada', 'salida']),
                    ubicacion=random.choice(["Bodega Principal", "Mostrador Principal", "Estantería Norte"]),
                    cantidad=random.randint(5, 30),
                    motivo=random.choice(motivos),
                )
                movimientos_prod.append(mov_p)
            print(f"-> Creados exitosamente {len(movimientos_prod)} registros de inventario de producto.")

            # ----------------------------------------------------
            # 6. LOTES (10 Lotes)
            # ----------------------------------------------------
            print("Creando 10 Lotes...")
            lotes = []
            for i in range(12):
                lote = Lote.objects.create(
                    numero_lote=f"LOTE-2026-{i+1:03d}",
                    presentacion=presentaciones[i % len(presentaciones)],
                    stock_actual=random.randint(10, 50),
                    costo_unitario=presentaciones[i % len(presentaciones)].precio * Decimal("0.70"), # 30% profit margin base
                    fecha_vencimiento=timezone.now().date() + timedelta(days=random.randint(30, 730)),
                    registrado_por=random.choice(users)
                )
                lotes.append(lote)
            print(f"-> Creados exitosamente {len(lotes)} lotes.")

            # ----------------------------------------------------
            # 7. MOVIMIENTOS DE INVENTARIO (10 Movimientos)
            # ----------------------------------------------------
            print("Creando 10 Movimientos de Inventario...")
            movimientos_inv = []
            for i in range(10):
                lote_sel = lotes[i % len(lotes)]
                mov_i = InventarioMovimiento.objects.create(
                    presentacion=lote_sel.presentacion,
                    lote=lote_sel,
                    registrado_por=random.choice(users),
                    tipo=random.choice(['entrada', 'salida', 'ajuste']),
                    cantidad=random.randint(1, 10),
                    motivo="Abastecimiento periódico de mercancía"
                )
                movimientos_inv.append(mov_i)
            print(f"-> Creados exitosamente {len(movimientos_inv)} movimientos de inventario.")

            # ----------------------------------------------------
            # 8. SESIONES DE CONTEO (10 Sesiones)
            # ----------------------------------------------------
            print("Creando 10 Sesiones de Conteo...")
            sesiones = []
            estados_conteo = ['activa', 'finalizada', 'cancelada']
            for i in range(10):
                estado = estados_conteo[i % 3]
                fin = timezone.now() if estado != 'activa' else None
                sesion = SesionConteo.objects.create(
                    estado=estado,
                    fecha_fin=fin,
                    responsable=random.choice(users)
                )
                sesiones.append(sesion)
            print(f"-> Creadas exitosamente {len(sesiones)} sesiones de conteo.")

            # ----------------------------------------------------
            # 9. CONTEOS DE PRODUCTOS (10 Conteos)
            # ----------------------------------------------------
            print("Creando 10 Conteos de Productos...")
            conteos = []
            # Make sure we use different presentations for a single session or separate sessions to respect unique constraints
            for i in range(10):
                conteo = ConteoProducto.objects.create(
                    sesion=sesiones[i % len(sesiones)],
                    presentacion=presentaciones[i % len(presentaciones)],
                    cantidad_contada=random.randint(5, 60)
                )
                conteos.append(conteo)
            print(f"-> Creados exitosamente {len(conteos)} conteos de productos.")

            # ----------------------------------------------------
            # 10. RESULTADOS DE INVENTARIO (10 Resultados)
            # ----------------------------------------------------
            print("Creando 10 Resultados de Inventario...")
            resultados = []
            for i in range(10):
                sistema = random.randint(10, 50)
                fisica = sistema + random.choice([-2, -1, 0, 1, 2])
                res = ResultadoInventario.objects.create(
                    sesion=sesiones[i % len(sesiones)],
                    presentacion=presentaciones[i % len(presentaciones)],
                    cantidad_sistema=sistema,
                    cantidad_fisica=fisica,
                    diferencia=fisica - sistema
                )
                resultados.append(res)
            print(f"-> Creados exitosamente {len(resultados)} resultados de inventario.")

            # ----------------------------------------------------
            # 11. AGENDAS DE INVENTARIO (10 Agendas)
            # ----------------------------------------------------
            print("Creando 10 Agendas de Inventario...")
            agendas = []
            estados_agenda = ['pendiente', 'en_proceso', 'completada', 'cancelada']
            for i in range(10):
                agenda = AgendaInventario.objects.create(
                    titulo=f"Conteo General Estantería {chr(65+i)}",
                    descripcion=f"Conteo rutinario de la sección de licores importados, estantería {chr(65+i)}.",
                    fecha_programada=timezone.now() + timedelta(days=random.randint(1, 15)),
                    estado=estados_agenda[i % len(estados_agenda)],
                    creado_por=random.choice(users),
                    responsable=random.choice(users)
                )
                agendas.append(agenda)
            print(f"-> Creadas exitosamente {len(agendas)} agendas de inventario.")

            # ----------------------------------------------------
            # 12. CLIENTES (10 Clientes)
            # ----------------------------------------------------
            print("Creando 10 Clientes...")
            clientes_data = [
                ("CC", "1017123456", "Juan Pérez", "3109876543", "juan.perez@email.com", "Calle 50 # 10-20"),
                ("CC", "1017123457", "Luz Marina Calle", "3119876543", "luz.calle@email.com", "Carrera 45 # 32-15"),
                ("CE", "9517123458", "Robert Smith", "3129876543", "robert.smith@email.com", "Transversal 12 # 4-8"),
                ("CC", "1017123459", "Carlos Mario Restrepo", "3139876543", "carlos.restrepo@email.com", "Avenida 30 # 70-80"),
                ("NIT", "800192831-2", "Restaurante El Portal S.A.S.", "3149876543", "compras@elportal.com", "Calle 10 # 5-25"),
                ("CC", "1017123460", "Paula Andrea Restrepo", "3159876543", "paula.restrepo@email.com", "Diagonal 45 # 12-10"),
                ("TI", "1087123461", "Mateo Valencia", "3169876543", "mateo.valencia@email.com", "Calle 80 # 30-40"),
                ("PA", "PA9827364", "Clara Schmidt", "3179876543", "clara.schmidt@email.com", "Carrera 70 # 8-12"),
                ("PT", "901239841", "Yuselis Blanco", "3189876543", "yuselis.blanco@email.com", "Calle 3 # 45-67"),
                ("CC", "1017123462", "Esteban Quintero", "3199876543", "esteban.quintero@email.com", "Carrera 15 # 22-80"),
            ]
            
            clientes = []
            for tipo_id, identificacion, nombre, telefono, email, direccion in clientes_data:
                cli = Cliente.objects.create(
                    tipo_id=tipo_id,
                    identificacion=identificacion,
                    nombre=nombre,
                    telefono=telefono,
                    email=email,
                    direccion=direccion
                )
                clientes.append(cli)
            print(f"-> Creados exitosamente {len(clientes)} clientes.")

            # ----------------------------------------------------
            # 13. VENTAS (10 Ventas)
            # ----------------------------------------------------
            print("Creando 10 Ventas...")
            ventas = []
            for i in range(10):
                descuento = Decimal(random.randint(0, 10))
                pago_e = Decimal(random.randint(20000, 100000))
                pago_t = Decimal(random.randint(0, 50000))
                total = pago_e + pago_t
                v = Venta.objects.create(
                    cliente=clientes[i % len(clientes)],
                    vendedor=random.choice(users),
                    descuento_porcentaje=descuento,
                    total_con_descuento=total,
                    pago_efectivo=pago_e,
                    pago_tarjeta=pago_t,
                    pago_transferencia=Decimal("0.00"),
                    pago_nequi=Decimal("0.00"),
                    pago_daviplata=Decimal("0.00")
                )
                ventas.append(v)
            print(f"-> Creadas exitosamente {len(ventas)} ventas.")

            # ----------------------------------------------------
            # 14. DETALLES DE VENTA (10 Detalles)
            # ----------------------------------------------------
            print("Creando 10 Detalles de Venta...")
            detalles_venta = []
            for i in range(10):
                pres_sel = presentaciones[i % len(presentaciones)]
                lote_sel = lotes[i % len(lotes)]
                dv = DetalleVenta.objects.create(
                    venta=ventas[i % len(ventas)],
                    producto=pres_sel.producto,
                    presentacion=pres_sel,
                    lote=lote_sel,
                    cantidad=random.randint(1, 4),
                    precio_unitario=pres_sel.precio
                )
                detalles_venta.append(dv)
            print(f"-> Creados exitosamente {len(detalles_venta)} detalles de venta.")

            # ----------------------------------------------------
            # 15. APERTURAS DE CAJA (10 Aperturas)
            # ----------------------------------------------------
            print("Creando 10 Aperturas de Caja...")
            aperturas = []
            for i in range(10):
                ap = AperturaCaja.objects.create(
                    fecha_apertura=timezone.now() - timedelta(days=10-i, hours=random.randint(0, 4)),
                    fecha=timezone.localdate() - timedelta(days=10-i),
                    monto_base=Decimal("150000.00") + Decimal(random.randint(0, 5) * 10000),
                    usuario=random.choice(users),
                    observacion="Apertura normal de caja con base sencilla",
                    denominaciones={"50000": 2, "20000": 3, "10000": 4, "5000": 2}
                )
                aperturas.append(ap)
            print(f"-> Creadas exitosamente {len(aperturas)} aperturas de caja.")

            # ----------------------------------------------------
            # 16. CIERRES DE CAJA (10 Cierres)
            # ----------------------------------------------------
            print("Creando 10 Cierres de Caja...")
            cierres = []
            for i in range(10):
                cc = CierreCaja.objects.create(
                    apertura=aperturas[i],
                    fecha_cierre=aperturas[i].fecha_apertura + timedelta(hours=8),
                    fecha=aperturas[i].fecha,
                    turno=1,
                    total_contado=aperturas[i].monto_base + Decimal(random.randint(150000, 500000)),
                    total_retirado=Decimal(random.randint(100000, 300000)),
                    monto_base_siguiente=Decimal("200000.00"),
                    denominaciones={"50000": 5, "20000": 8, "10000": 10, "5000": 10}
                )
                cierres.append(cc)
            print(f"-> Creados exitosamente {len(cierres)} cierres de caja.")

            # ----------------------------------------------------
            # 17. DEVOLUCIONES (10 Devoluciones)
            # ----------------------------------------------------
            print("Creando 10 Devoluciones...")
            devoluciones = []
            motivos_dev = ['defectuoso', 'equivocado', 'insatisfecho', 'otro']
            for i in range(10):
                d = Devolucion.objects.create(
                    venta=ventas[i % len(ventas)],
                    motivo=random.choice(motivos_dev),
                    observaciones="Cliente argumenta que el producto presentaba filtración de empaque.",
                    restaurar_stock=random.choice([True, False]),
                    tiene_comprobante=True,
                    total_devuelto=Decimal(random.randint(15000, 50000))
                )
                devoluciones.append(d)
            print(f"-> Creadas exitosamente {len(devoluciones)} devoluciones.")

            # ----------------------------------------------------
            # 18. DETALLES DE DEVOLUCION (10 Detalles Devolución)
            # ----------------------------------------------------
            print("Creando 10 Detalles de Devolución...")
            detalles_dev = []
            for i in range(10):
                pres_sel = presentaciones[i % len(presentaciones)]
                lote_sel = lotes[i % len(lotes)]
                dd = DetalleDevolucion.objects.create(
                    devolucion=devoluciones[i % len(devoluciones)],
                    producto=pres_sel.producto,
                    presentacion=pres_sel,
                    lote=lote_sel,
                    cantidad=1,
                    precio_unitario=pres_sel.precio
                )
                detalles_dev.append(dd)
            print(f"-> Creados exitosamente {len(detalles_dev)} detalles de devolución.")

            # ----------------------------------------------------
            # 19. REPORTES GENERADOS (10 Reportes)
            # ----------------------------------------------------
            print("Creando 10 Reportes Generados...")
            reportes = []
            tipos_rep = ['inventario', 'movimientos', 'vencimientos']
            for i in range(10):
                rep = ReporteGenerado.objects.create(
                    titulo=f"Reporte del periodo {2026} - Q{i % 4 + 1} - V{i}",
                    tipo=random.choice(tipos_rep),
                    usuario=random.choice(users),
                    archivo=None
                )
                reportes.append(rep)
            print(f"-> Creados exitosamente {len(reportes)} reportes generados.")
            
            print("\n¡Base de datos poblada exitosamente con al menos 10 registros reales en cada una de las 19 tablas!")

    except Exception as e:
        print(f"\n[ERROR] Ocurrió un problema poblando la base de datos: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run()
