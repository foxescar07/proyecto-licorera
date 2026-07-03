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
from productos.models import Categoria, Producto, PresentacionProducto
from proveedores.models import Proveedor, ProveedorCategoria, OrdenCompra, DetalleCompra, Compra as CompraLegacy, HistorialOrden
from inventario.models import Lote, Inventario as InventarioMovimiento, SesionConteo, ConteoProducto, ResultadoInventario, AgendaInventario
from ventas.models import Cliente, Venta, DetalleVenta, AperturaCaja, CierreCaja, Devolucion, DetalleDevolucion
from reportes.models import ReporteVenta, ReporteInventario, ReporteCaja, ReporteCompra, ReporteDevolucion, ReporteLote

def run():
    print("Iniciando la población de la base de datos de Proyecto Licorera...")
    
    try:
        with transaction.atomic():
            # ----------------------------------------------------
            # CLEANING DATABASE
            # ----------------------------------------------------
            print("Limpiando datos existentes...")
            ReporteLote.objects.all().delete()
            ReporteDevolucion.objects.all().delete()
            ReporteCompra.objects.all().delete()
            ReporteCaja.objects.all().delete()
            ReporteInventario.objects.all().delete()
            ReporteVenta.objects.all().delete()
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
            HistorialOrden.objects.all().delete()
            DetalleCompra.objects.all().delete()
            OrdenCompra.objects.all().delete()
            CompraLegacy.objects.all().delete()
            ProveedorCategoria.objects.all().delete()
            Proveedor.objects.all().delete()
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
            print("Creando Presentaciones de Producto...")
            presentaciones = []
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
            # 5. PROVEEDORES & RELACIONES (10 Proveedores)
            # ----------------------------------------------------
            print("Creando 10 Proveedores...")
            proveedores = []
            proveedores_data = [
                ("Distribuidora de Licores del Norte", "contacto@licoresnorte.com", "3007654321", "distribuidor"),
                ("Bodegas del Valle", "valle@bodegas.com", "3117654321", "fabricante"),
                ("Importaciones Premier", "premier@importaciones.com", "3127654321", "importador"),
                ("Alianza Cervecera", "alianza@cervecera.com", "3137654321", "distribuidor"),
                ("Destilerías de Caldas", "caldas@destilerias.com", "3147654321", "fabricante"),
                ("Comercializadora del Sur", "contacto@comercialsur.com", "3157654321", "distribuidor"),
                ("Vinos y Viñedos de América", "contacto@vinosamerica.com", "3167654321", "importador"),
                ("Grupo Diageo Colombia", "contacto@diageocol.com", "3177654321", "importador"),
                ("Industria de Licores de Antioquia", "ila@licoresantioquia.com", "3187654321", "fabricante"),
                ("Licores y Abarrotes del Eje", "eje@licores.com", "3197654321", "distribuidor"),
            ]
            for nombre, email, telefono, tipo in proveedores_data:
                prov = Proveedor.objects.create(
                    nombre_empresa=nombre,
                    email=email,
                    telefono=telefono,
                    tipo_proveedor=tipo,
                    estado='activo',
                    registrado_por=random.choice(users)
                )
                proveedores.append(prov)
            
            for i in range(10):
                ProveedorCategoria.objects.create(
                    proveedor=proveedores[i],
                    categoria=categorias[i % len(categorias)]
                )
            print(f"-> Creados exitosamente {len(proveedores)} proveedores.")

            # ----------------------------------------------------
            # 6. ORDENES DE COMPRA & DETALLES (10 Órdenes)
            # ----------------------------------------------------
            print("Creando 10 Órdenes de Compra...")
            ordenes = []
            detalles_compra = []
            for i in range(10):
                orden = OrdenCompra.objects.create(
                    proveedor=proveedores[i],
                    registrado_por=random.choice(users),
                    estado='recibida',
                    total=Decimal("0.00")
                )
                ordenes.append(orden)
                
                pres_sel = presentaciones[i % len(presentaciones)]
                detalle = DetalleCompra.objects.create(
                    orden_compra=orden,
                    presentacion=pres_sel,
                    cantidad=random.randint(10, 50),
                    precio_unitario=pres_sel.precio * Decimal("0.70")
                )
                detalles_compra.append(detalle)
                orden.calcular_total()
            print(f"-> Creadas exitosamente {len(ordenes)} órdenes de compra.")

            # ----------------------------------------------------
            # 7. COMPRAS LEGACY (10 Compras)
            # ----------------------------------------------------
            print("Creando 10 Compras Legacy...")
            compras_legacy = []
            for i in range(10):
                comp = CompraLegacy.objects.create(
                    proveedor=proveedores[i],
                    producto=productos[i % len(productos)],
                    cantidad=random.randint(10, 50),
                    precio_unitario=productos[i % len(productos)].precio_unitario * Decimal("0.70"),
                    recibida=True,
                    estado_pago='pagada',
                    monto_pagado=Decimal("100000.00"),
                )
                compras_legacy.append(comp)
            print(f"-> Creadas exitosamente {len(compras_legacy)} compras legacy.")

            # ----------------------------------------------------
            # 8. LOTES (12 Lotes)
            # ----------------------------------------------------
            print("Creando 12 Lotes...")
            lotes = []
            for i in range(12):
                lote = Lote.objects.create(
                    numero_lote=f"LOTE-2026-{i+1:03d}",
                    presentacion=presentaciones[i % len(presentaciones)],
                    detalle_compra=detalles_compra[i % len(detalles_compra)],
                    stock_actual=random.randint(10, 50),
                    costo_unitario=presentaciones[i % len(presentaciones)].precio * Decimal("0.70"),
                    fecha_vencimiento=timezone.now().date() + timedelta(days=random.randint(30, 730)),
                    registrado_por=random.choice(users)
                )
                lotes.append(lote)
            print(f"-> Creados exitosamente {len(lotes)} lotes.")

            # ----------------------------------------------------
            # 9. MOVIMIENTOS DE INVENTARIO (10 Movimientos)
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
            # 10. SESIONES DE CONTEO (10 Sesiones)
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
            # 11. CONTEOS DE PRODUCTOS (10 Conteos)
            # ----------------------------------------------------
            print("Creando 10 Conteos de Productos...")
            conteos = []
            for i in range(10):
                conteo = ConteoProducto.objects.create(
                    sesion=sesiones[i % len(sesiones)],
                    presentacion=presentaciones[i % len(presentaciones)],
                    cantidad_contada=random.randint(5, 60)
                )
                conteos.append(conteo)
            print(f"-> Creados exitosamente {len(conteos)} conteos de productos.")

            # ----------------------------------------------------
            # 12. RESULTADOS DE INVENTARIO (10 Resultados)
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
            # 13. AGENDAS DE INVENTARIO (10 Agendas)
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
            # 14. CLIENTES (10 Clientes)
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
            # 15. VENTAS (10 Ventas)
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
            # 16. DETALLES DE VENTA (10 Detalles)
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
            # 17. APERTURAS DE CAJA (10 Aperturas)
            # ----------------------------------------------------
            print("Creando 10 Aperturas de Caja...")
            aperturas = []
            for i in range(10):
                ap = AperturaCaja.objects.create(
                    fecha=timezone.localdate() - timedelta(days=10-i),
                    monto_base=Decimal("150000.00") + Decimal(random.randint(0, 5) * 10000),
                    usuario=random.choice(users),
                    observacion="Apertura normal de caja con base sencilla",
                    denominaciones={"50000": 2, "20000": 3, "10000": 4, "5000": 2}
                )
                aperturas.append(ap)
            print(f"-> Creadas exitosamente {len(aperturas)} aperturas de caja.")

            # ----------------------------------------------------
            # 18. CIERRES DE CAJA (10 Cierres)
            # ----------------------------------------------------
            print("Creando 10 Cierres de Caja...")
            cierres = []
            for i in range(10):
                cc = CierreCaja.objects.create(
                    apertura=aperturas[i],
                    fecha=aperturas[i].fecha,
                    usuario=aperturas[i].usuario,
                    total_contado=aperturas[i].monto_base + Decimal(random.randint(150000, 500000)),
                    total_retirado=Decimal(random.randint(100000, 300000)),
                    monto_base_siguiente=Decimal("200000.00"),
                    denominaciones={"50000": 5, "20000": 8, "10000": 10, "5000": 10}
                )
                cierres.append(cc)
            print(f"-> Creados exitosamente {len(cierres)} cierres de caja.")

            # ----------------------------------------------------
            # 19. DEVOLUCIONES (10 Devoluciones)
            # ----------------------------------------------------
            print("Creando 10 Devoluciones...")
            devoluciones = []
            motivos_dev = ['defectuoso', 'equivocado', 'insatisfecho', 'otro']
            for i in range(10):
                d = Devolucion.objects.create(
                    venta=ventas[i % len(ventas)],
                    registrado_por=random.choice(users),
                    motivo=random.choice(motivos_dev),
                    observaciones="Cliente argumenta que el producto presentaba filtración de empaque.",
                    restaurar_stock=random.choice([True, False]),
                    tiene_comprobante=True,
                    total_devuelto=Decimal(random.randint(15000, 50000))
                )
                devoluciones.append(d)
            print(f"-> Creadas exitosamente {len(devoluciones)} devoluciones.")

            # ----------------------------------------------------
            # 20. DETALLES DE DEVOLUCION (10 Detalles Devolución)
            # ----------------------------------------------------
            print("Creando 10 Detalles de Devolución...")
            detalles_dev = []
            for i in range(10):
                pres_sel = presentaciones[i % len(presentaciones)]
                lote_sel = lotes[i % len(lotes)]
                dd = DetalleDevolucion.objects.create(
                    devolucion=devoluciones[i % len(devoluciones)],
                    presentacion=pres_sel,
                    lote=lote_sel,
                    cantidad=1,
                    precio_unitario=pres_sel.precio
                )
                detalles_dev.append(dd)
            print(f"-> Creados exitosamente {len(detalles_dev)} detalles de devolución.")

            # ----------------------------------------------------
            # 21. REPORTES (10 Registros en cada una de las 6 tablas reales)
            # ----------------------------------------------------
            print("Creando Reportes en las 6 tablas de reportes...")
            
            # Reportes de Ventas
            for i in range(10):
                v = ventas[i]
                dv = detalles_venta[i]
                ReporteVenta.objects.create(
                    venta_id=v,
                    cliente_id=v.cliente,
                    presentacion_id=dv.presentacion,
                    vendedor_id=v.vendedor,
                    total=v.total_venta,
                    fecha=v.fecha
                )
            
            # Reportes de Inventario
            for i in range(10):
                l = lotes[i]
                ReporteInventario.objects.create(
                    presentacion_id=l.presentacion,
                    lote_id=l,
                    sesion_conteo_id=sesiones[i % len(sesiones)],
                    stock_sistema=l.stock_actual,
                    stock_fisico=l.stock_actual,
                    diferencia=0,
                    estado_lote='disponible',
                    fecha_vencimiento=l.fecha_vencimiento
                )
            
            # Reportes de Caja
            for i in range(10):
                ReporteCaja.objects.create(
                    apertura_id=aperturas[i],
                    cierre_id=cierres[i],
                    usuario_id=aperturas[i].usuario,
                    total_ventas=Decimal("350000.00"),
                    total_devoluciones=Decimal("15000.00"),
                    total_contado=Decimal("485000.00"),
                    diferencia=Decimal("0.00")
                )
                
            # Reportes de Compra
            for i in range(10):
                c = compras_legacy[i]
                ReporteCompra.objects.create(
                    orden_compra_id=c,
                    proveedor_id=c.proveedor,
                    presentacion_id=presentaciones[i % len(presentaciones)],
                    total=c.total or Decimal("150000.00"),
                    estado_orden='facturada',
                    fecha=timezone.now()
                )
                
            # Reportes de Devolucion
            for i in range(10):
                d = devoluciones[i]
                ReporteDevolucion.objects.create(
                    devolucion_id=d,
                    venta_id=d.venta,
                    cliente_id=d.venta.cliente,
                    total_devuelto=d.total_devuelto,
                    motivo=d.get_motivo_display(),
                    fecha=d.fecha
                )
                
            # Reportes de Lote
            for i in range(10):
                l = lotes[i]
                ReporteLote.objects.create(
                    lote_id=l,
                    presentacion_id=l.presentacion,
                    stock_actual=l.stock_actual,
                    costo_unitario=l.costo_unitario,
                    fecha_vencimiento=l.fecha_vencimiento,
                    dias_para_vencer=l.dias_para_vencer or 365,
                    estado='vigente'
                )
            print("-> Creados exitosamente 10 registros en cada una de las 6 tablas de reportes.")
            
            print("\n¡Base de datos poblada exitosamente con datos consistentes y actualizados en todos los modelos!")

    except Exception as e:
        print(f"\n[ERROR] Ocurrió un problema poblando la base de datos: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run()
