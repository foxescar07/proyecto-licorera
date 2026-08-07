from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
from django.db.models import Sum, F


class OperacionBase(models.Model):
    """
    TABLA BASE CENTRAL - Unififica todas las operaciones del negocio
    Conecta: Proveedores, Compras, Inventario, Ventas, Usuarios, Productos
    """

    TIPO_OPERACION_CHOICES = [
        ('compra_proveedor', 'Compra a Proveedor'),
        ('recepcion_compra', 'Recepción de Compra'),
        ('venta_cliente', 'Venta a Cliente'),
        ('devolucion_cliente', 'Devolución de Cliente'),
        ('ajuste_inventario', 'Ajuste de Inventario'),
        ('pago_proveedor', 'Pago a Proveedor'),
    ]

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('en_proceso', 'En Proceso'),
        ('completada', 'Completada'),
        ('cancelada', 'Cancelada'),
        ('rechazada', 'Rechazada'),
    ]

    # ═══════════════════════════════════════════════════════════════════
    # IDENTIFICACIÓN
    # ═══════════════════════════════════════════════════════════════════
    codigo = models.CharField(
        max_length=50,
        unique=True,
        help_text="Código único de la operación (Ej: OC-2024-001, VENTA-2024-005)"
    )
    tipo_operacion = models.CharField(
        max_length=30,
        choices=TIPO_OPERACION_CHOICES,
        help_text="Tipo de operación realizada"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='pendiente',
        help_text="Estado actual de la operación"
    )

    # ═══════════════════════════════════════════════════════════════════
    # RELACIONES PRINCIPALES - PROVEEDORES
    # ═══════════════════════════════════════════════════════════════════
    proveedor = models.ForeignKey(
        'proveedores.Proveedor',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='operaciones_base',
        help_text="Proveedor asociado"
    )
    orden_compra = models.ForeignKey(
        'proveedores.OrdenCompra',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='operaciones_base',
        help_text="Orden de compra asociada"
    )
    compra_legacy = models.ForeignKey(
        'proveedores.Compra',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='operaciones_base',
        help_text="Compra legacy (antigua) si aplica"
    )
    detalle_compra = models.ForeignKey(
        'proveedores.DetalleCompra',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='operaciones_base',
        help_text="Detalle de compra específico"
    )

    # ═══════════════════════════════════════════════════════════════════
    # RELACIONES PRINCIPALES - VENTAS
    # ═══════════════════════════════════════════════════════════════════
    cliente = models.ForeignKey(
        'ventas.Cliente',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='operaciones_base',
        help_text="Cliente asociado"
    )
    venta = models.ForeignKey(
        'ventas.Venta',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='operaciones_base',
        help_text="Venta asociada"
    )
    devolucion = models.ForeignKey(
        'ventas.Devolucion',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='operaciones_base',
        help_text="Devolución de cliente asociada"
    )
    detalle_venta = models.ForeignKey(
        'ventas.DetalleVenta',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='operaciones_base',
        help_text="Detalle de venta específico"
    )

    # ═══════════════════════════════════════════════════════════════════
    # RELACIONES PRINCIPALES - INVENTARIO
    # ═══════════════════════════════════════════════════════════════════
    producto = models.ForeignKey(
        'productos.Producto',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='operaciones_base',
        help_text="Producto asociado"
    )
    presentacion = models.ForeignKey(
        'productos.PresentacionProducto',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='operaciones_base',
        help_text="Presentación del producto"
    )
    lote = models.ForeignKey(
        'inventario.Lote',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='operaciones_base',
        help_text="Lote de inventario asociado"
    )
    movimiento_inventario = models.ForeignKey(
        'inventario.Inventario',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='operaciones_base',
        help_text="Movimiento de inventario"
    )

    # ═══════════════════════════════════════════════════════════════════
    # DATOS OPERACIONALES
    # ═══════════════════════════════════════════════════════════════════
    cantidad = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Cantidad de productos/unidades"
    )
    precio_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Precio unitario en COP"
    )
    descuento = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Descuento aplicado"
    )
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Subtotal (cantidad × precio_unitario)"
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total (subtotal - descuento)"
    )

    # ═══════════════════════════════════════════════════════════════════
    # DETALLES DE PAGO (Para compras)
    # ═══════════════════════════════════════════════════════════════════
    metodo_pago = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('transferencia', 'Transferencia Bancaria'),
            ('efectivo', 'Efectivo'),
            ('cheque', 'Cheque'),
            ('tarjeta', 'Tarjeta de Crédito'),
            ('credito', 'Crédito a 30 días'),
            ('nequi', 'Nequi'),
            ('daviplata', 'DaviPlata'),
        ],
        help_text="Método de pago utilizado"
    )
    estado_pago = models.CharField(
        max_length=20,
        default='pendiente',
        choices=[
            ('pendiente', 'Pendiente de Pago'),
            ('pagada', 'Pagada'),
            ('parcial', 'Pago Parcial'),
        ],
        help_text="Estado del pago"
    )
    monto_pagado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Monto ya pagado"
    )
    saldo_pendiente = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Saldo pendiente de pago"
    )
    fecha_pago = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha en que se realizó el pago"
    )

    # ═══════════════════════════════════════════════════════════════════
    # INFORMACIÓN DE RECEPCIÓN/ENVÍO
    # ═══════════════════════════════════════════════════════════════════
    cantidad_recibida = models.PositiveIntegerField(
        null=True,
        blank=True,
        default=0,
        help_text="Cantidad recibida (para compras)"
    )
    fecha_recepcion = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha en que se recibió"
    )
    numero_factura = models.CharField(
        max_length=100,
        blank=True,
        help_text="Número de factura del proveedor"
    )
    numero_documento = models.CharField(
        max_length=100,
        blank=True,
        help_text="Número de documento (factura, recibo, etc)"
    )

    # ═══════════════════════════════════════════════════════════════════
    # AUDITORÍA Y CONTROL
    # ═══════════════════════════════════════════════════════════════════
    usuario_creador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='operaciones_creadas',
        help_text="Usuario que creó la operación"
    )
    usuario_modificador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='operaciones_modificadas',
        help_text="Usuario que última vez modificó"
    )
    usuario_autorizado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='operaciones_autorizadas',
        help_text="Usuario que autorizó la operación"
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha de creación"
    )
    fecha_modificacion = models.DateTimeField(
        auto_now=True,
        help_text="Fecha de última modificación"
    )
    fecha_operacion = models.DateTimeField(
        default=timezone.now,
        help_text="Fecha en que ocurrió la operación"
    )

    # ═══════════════════════════════════════════════════════════════════
    # NOTAS Y OBSERVACIONES
    # ═══════════════════════════════════════════════════════════════════
    notas = models.TextField(
        blank=True,
        help_text="Notas internas sobre la operación"
    )
    observaciones = models.TextField(
        blank=True,
        help_text="Observaciones adicionales"
    )
    motivo_cancelacion = models.TextField(
        blank=True,
        help_text="Motivo si fue cancelada"
    )

    class Meta:
        verbose_name = 'Operación Base'
        verbose_name_plural = 'Operaciones Base'
        ordering = ['-fecha_operacion']
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['tipo_operacion', 'estado']),
            models.Index(fields=['proveedor', 'fecha_operacion']),
            models.Index(fields=['cliente', 'fecha_operacion']),
            models.Index(fields=['usuario_creador', 'fecha_creacion']),
            models.Index(fields=['estado', 'fecha_operacion']),
        ]

    def __str__(self):
        return f"{self.codigo} - {self.get_tipo_operacion_display()} ({self.estado})"

    def save(self, *args, **kwargs):
        # Calcular subtotal
        if self.cantidad and self.precio_unitario:
            self.subtotal = self.cantidad * self.precio_unitario

        # Calcular total
        self.total = self.subtotal - self.descuento

        # Calcular saldo pendiente
        self.saldo_pendiente = self.total - self.monto_pagado

        # Actualizar estado de pago automáticamente
        if self.monto_pagado >= self.total:
            self.estado_pago = 'pagada'
        elif self.monto_pagado > 0:
            self.estado_pago = 'parcial'
        else:
            self.estado_pago = 'pendiente'

        super().save(*args, **kwargs)

    @property
    def esta_pagada(self):
        """Verifica si la operación está completamente pagada"""
        return self.monto_pagado >= self.total and self.estado_pago == 'pagada'

    @property
    def es_compra(self):
        """Verifica si es una operación de compra"""
        return self.tipo_operacion in ['compra_proveedor', 'recepcion_compra', 'pago_proveedor']

    @property
    def es_venta(self):
        """Verifica si es una operación de venta"""
        return self.tipo_operacion in ['venta_cliente', 'devolucion_cliente']


class DetalleOperacionBase(models.Model):
    """
    DETALLES de la operación base - Para líneas adicionales
    Permite múltiples productos por operación
    """

    operacion = models.ForeignKey(
        OperacionBase,
        on_delete=models.CASCADE,
        related_name='detalles',
        help_text="Operación base a la que pertenece"
    )

    # Producto
    producto = models.ForeignKey(
        'productos.Producto',
        on_delete=models.PROTECT,
        related_name='detalles_operacion_base',
        help_text="Producto"
    )
    presentacion = models.ForeignKey(
        'productos.PresentacionProducto',
        on_delete=models.PROTECT,
        related_name='detalles_operacion_base',
        help_text="Presentación del producto"
    )
    lote = models.ForeignKey(
        'inventario.Lote',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='detalles_operacion_base',
        help_text="Lote específico (opcional)"
    )

    # Cantidad y precios
    cantidad = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Cantidad"
    )
    precio_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Precio unitario"
    )
    descuento_linea = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Descuento en esta línea"
    )

    # Códigos
    numero_lote = models.CharField(
        max_length=100,
        blank=True,
        help_text="Número de lote del proveedor"
    )
    fecha_vencimiento = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de vencimiento"
    )

    # Control
    orden_linea = models.PositiveIntegerField(
        default=0,
        help_text="Orden de esta línea en la operación"
    )
    activo = models.BooleanField(
        default=True,
        help_text="¿Está activa esta línea?"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Detalle Operación Base'
        verbose_name_plural = 'Detalles Operación Base'
        ordering = ['orden_linea']

    def __str__(self):
        return f"{self.operacion.codigo} - {self.producto.nombre} x{self.cantidad}"

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario

    @property
    def total(self):
        return self.subtotal - self.descuento_linea


class HistorialOperacionBase(models.Model):
    """
    HISTORIAL de cambios en operaciones base
    Mantiene registro de cada cambio realizado
    """

    EVENTO_CHOICES = [
        ('creada', 'Operación Creada'),
        ('confirmada', 'Confirmada'),
        ('recibida', 'Recibida'),
        ('pagada', 'Pagada'),
        ('cancelada', 'Cancelada'),
        ('editada', 'Editada'),
        ('autorizada', 'Autorizada'),
        ('rechazada', 'Rechazada'),
        ('estado_pago_actualizado', 'Estado de Pago Actualizado'),
        ('nota_agregada', 'Nota Agregada'),
    ]

    operacion = models.ForeignKey(
        OperacionBase,
        on_delete=models.CASCADE,
        related_name='historial',
        help_text="Operación"
    )
    evento = models.CharField(
        max_length=50,
        choices=EVENTO_CHOICES,
        help_text="Tipo de evento"
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historial_operaciones',
        help_text="Usuario que realizó la acción"
    )
    fecha = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha del evento"
    )
    descripcion = models.TextField(
        blank=True,
        help_text="Descripción del cambio"
    )
    valor_anterior = models.TextField(
        blank=True,
        help_text="Valor anterior (JSON)"
    )
    valor_nuevo = models.TextField(
        blank=True,
        help_text="Valor nuevo (JSON)"
    )

    class Meta:
        verbose_name = 'Historial Operación Base'
        verbose_name_plural = 'Historial Operaciones Base'
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.operacion.codigo} - {self.get_evento_display()}"
