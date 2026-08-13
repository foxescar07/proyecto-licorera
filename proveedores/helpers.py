"""
Helper functions para el módulo de proveedores.
Centraliza lógica reutilizable para evitar duplicación.
"""

import logging
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, Count, F, DecimalField
from django.db.models.functions import TruncMonth
from datetime import timedelta
from .models import Compra, DetalleCompra, HistorialCompra, Proveedor
from productos.models import Producto
from inventario.models import Lote, Inventario, MovimientoInventario

logger = logging.getLogger(__name__)


# ============================================
# HELPERS - VALIDACIÓN DE COMPRAS
# ============================================

def validar_datos_compra(producto_id, cantidad, precio_unitario):
    """
    Valida que los datos de una compra sean correctos.

    Args:
        producto_id: ID del producto
        cantidad: Cantidad a comprar
        precio_unitario: Precio por unidad

    Returns:
        tuple: (es_valido: bool, mensaje: str)
    """
    errores = []

    try:
        cantidad = int(cantidad)
        if cantidad <= 0:
            errores.append("La cantidad debe ser mayor a 0")
    except (ValueError, TypeError):
        errores.append("La cantidad debe ser un número entero")

    try:
        precio = Decimal(str(precio_unitario))
        if precio <= 0:
            errores.append("El precio debe ser mayor a 0")
    except (ValueError, TypeError):
        errores.append("El precio debe ser un número decimal válido")

    try:
        producto = Producto.objects.get(id=producto_id)
    except Producto.DoesNotExist:
        errores.append("El producto seleccionado no existe")

    if errores:
        return False, " | ".join(errores)

    return True, "OK"


# ============================================
# HELPERS - OBTENCIÓN DE COMPRAS
# ============================================

def obtener_compras_proveedor(proveedor_id):
    """
    Obtiene todas las compras de un proveedor con sus detalles.

    Args:
        proveedor_id: ID del proveedor

    Returns:
        QuerySet: Compras del proveedor ordenadas por fecha
    """
    try:
        compras = (
            Compra.objects
            .filter(proveedor_id=proveedor_id)
            .select_related('proveedor', 'documento_usuario')
            .prefetch_related('detalles', 'historial')
            .order_by('-fecha')
        )
        return compras
    except Exception as e:
        logger.error(f"Error al obtener compras del proveedor {proveedor_id}: {e}")
        return Compra.objects.none()


def calcular_totales_compra(proveedor=None):
    """
    Calcula totales y estadísticas de compras.

    Args:
        proveedor: (Opcional) Proveedor específico, si None calcula para todos

    Returns:
        dict: Diccionario con estadísticas
    """
    try:
        hoy = timezone.now()
        hace_7_dias = hoy - timedelta(days=7)

        # Filtrar por proveedor si se proporciona
        queryset = Compra.objects.all()
        if proveedor:
            queryset = queryset.filter(proveedor=proveedor)

        # Gasto esta semana
        compras_semana = queryset.filter(fecha__gte=hace_7_dias).exclude(valor__isnull=True)
        total_gastado = sum(float(c.valor) for c in compras_semana) or 0

        # Compras este mes
        compras_mes = queryset.filter(
            fecha__year=hoy.year,
            fecha__month=hoy.month,
        )
        count_mes = compras_mes.count()
        total_mes = sum(float(c.valor) for c in compras_mes.exclude(valor__isnull=True)) or 0

        # Producto más comprado
        producto_top = (
            DetalleCompra.objects
            .values('producto__nombre', 'producto__id')
            .annotate(total_und=Sum('cantidad'))
            .order_by('-total_und')
            .first()
        )

        return {
            'total_gastado': float(total_gastado),
            'count_mes': count_mes,
            'total_mes': float(total_mes),
            'producto_top': producto_top,
        }
    except Exception as e:
        logger.error(f"Error al calcular totales de compra: {e}")
        return {
            'total_gastado': 0,
            'count_mes': 0,
            'total_mes': 0,
            'producto_top': None,
        }


# ============================================
# HELPERS - DATOS PARA GRÁFICOS
# ============================================

def obtener_datos_graficos(proveedor=None):
    """
    Obtiene datos para gráficos de compras.

    Args:
        proveedor: (Opcional) Proveedor específico

    Returns:
        dict: Datos para gráficos en formato JSON-safe
    """
    try:
        hoy = timezone.now()
        desde = hoy - timedelta(days=365)

        queryset = Compra.objects.filter(fecha__gte=desde)
        if proveedor:
            queryset = queryset.filter(proveedor=proveedor)

        # ===== COMPRAS POR MES =====
        compras_por_mes = (
            queryset
            .annotate(mes=TruncMonth('fecha'))
            .values('mes')
            .annotate(total=Count('id'))
            .order_by('mes')
        )

        meses_labels = []
        meses_data = []
        meses_nombres = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

        datos_por_mes = {item['mes'].month: item['total'] for item in compras_por_mes if item['mes']}

        mes_actual = hoy.month
        for i in range(12):
            mes = (mes_actual - (11 - i) - 1) % 12 + 1
            meses_labels.append(meses_nombres[mes - 1])
            meses_data.append(datos_por_mes.get(mes, 0))

        # ===== GASTOS POR PROVEEDOR =====
        gastos_proveedor_dict = {}
        for compra in queryset.select_related('proveedor'):
            nombre = compra.proveedor.nombre_empresa
            valor = float(compra.valor or 0)
            gastos_proveedor_dict[nombre] = gastos_proveedor_dict.get(nombre, 0) + valor

        gastos_ordenados = sorted(gastos_proveedor_dict.items(), key=lambda x: x[1], reverse=True)[:5]
        gastos_labels = [item[0] for item in gastos_ordenados]
        gastos_data = [int(item[1]) for item in gastos_ordenados]

        # Calcular porcentajes
        gastos_total = sum(gastos_data) if gastos_data else 1
        gastos_porcentajes = [int((gasto / gastos_total * 100)) for gasto in gastos_data] if gastos_data else []

        return {
            'meses_labels': meses_labels,
            'meses_data': meses_data,
            'gastos_labels': gastos_labels,
            'gastos_data': gastos_data,
            'gastos_porcentajes': gastos_porcentajes,
        }
    except Exception as e:
        logger.error(f"Error al obtener datos de gráficos: {e}")
        return {
            'meses_labels': [],
            'meses_data': [],
            'gastos_labels': [],
            'gastos_data': [],
            'gastos_porcentajes': [],
        }


# ============================================
# HELPERS - CREACIÓN DE REGISTROS
# ============================================

@transaction.atomic
def crear_compra_con_detalles(proveedor, producto, cantidad, precio_unitario, usuario):
    """
    Crea una compra completa con detalles, lote e historial.

    Args:
        proveedor: Instancia de Proveedor
        producto: Instancia de Producto
        cantidad: Cantidad a comprar
        precio_unitario: Precio por unidad
        usuario: Usuario que registra la compra

    Returns:
        tuple: (compra: Compra, error: str or None)
    """
    try:
        # Validar datos
        es_valido, mensaje = validar_datos_compra(producto.id, cantidad, precio_unitario)
        if not es_valido:
            return None, mensaje

        cantidad = int(cantidad)
        precio_unitario = Decimal(str(precio_unitario))
        total_compra = cantidad * precio_unitario

        # Crear compra
        compra = Compra.objects.create(
            proveedor=proveedor,
            valor=total_compra,
            saldo=total_compra,
            documento_usuario=usuario,
            estado='pendiente'
        )

        # Crear historial
        HistorialCompra.objects.create(
            compra=compra,
            evento='creada',
            usuario=usuario,
            descripcion=f'Compra registrada: {cantidad} x {producto.nombre}'
        )

        # Obtener o crear presentación
        presentacion = producto.presentaciones.first()
        if not presentacion:
            from productos.models import PresentacionProducto
            presentacion = PresentacionProducto.objects.create(
                producto=producto,
                nombre=f"{producto.nombre} - Presentación Estándar",
                cantidad=0,
                unidades=1,
                precio=precio_unitario,
            )

        # Crear lote
        import uuid
        lote_numero = f"LOTE-{uuid.uuid4().hex[:8].upper()}"
        lote = Lote.objects.create(
            numero_lote=lote_numero,
            presentacion=presentacion,
            stock_actual=cantidad,
            costo_unitario=precio_unitario,
            registrado_por=usuario
        )

        # Crear detalle de compra
        DetalleCompra.objects.create(
            compra=compra,
            producto=producto,
            presentacion=presentacion,
            cantidad=cantidad,
            precio_unitario=precio_unitario
        )

        # Actualizar producto
        producto.cantidad_disponible += cantidad
        producto.save()

        # Actualizar presentación
        presentacion.cantidad += cantidad
        presentacion.save()

        # Inventario conserva el saldo por producto/presentación; el registro
        # de entrada pertenece a MovimientoInventario.
        inventario, _ = Inventario.objects.get_or_create(
            producto=producto,
            presentacion=presentacion,
            defaults={'stock_actual': 0},
        )
        inventario.stock_actual += cantidad
        inventario.save(update_fields=['stock_actual'])
        MovimientoInventario.objects.create(
            inventario=inventario,
            lote=lote,
            registrado_por=usuario,
            tipo='entrada',
            cantidad=cantidad,
            motivo=f'Compra a proveedor: {proveedor.nombre_empresa}',
            stock_resultante=inventario.stock_actual,
        )

        logger.info(f"Compra creada exitosamente: ID={compra.id}, Proveedor={proveedor.nombre_empresa}")
        return compra, None

    except Exception as e:
        logger.error(f"Error creando compra: {e}")
        return None, f"Error al registrar la compra: {str(e)}"


# ============================================
# HELPERS - ESTADÍSTICAS DE PROVEEDORES
# ============================================

def calcular_estadisticas_proveedor(proveedor):
    """
    Calcula estadísticas de un proveedor.

    Args:
        proveedor: Instancia de Proveedor

    Returns:
        dict: Estadísticas del proveedor
    """
    try:
        compras = Compra.objects.filter(proveedor=proveedor)
        total_compras = compras.count()
        total_gastado = sum(float(c.valor) for c in compras if c.valor) or 0

        return {
            'total_compras': total_compras,
            'total_gastado': float(total_gastado),
        }
    except Exception as e:
        logger.error(f"Error calculando estadísticas del proveedor {proveedor.id}: {e}")
        return {
            'total_compras': 0,
            'total_gastado': 0,
        }
