from django.db import models
from django.conf import settings


class ReporteVenta(models.Model):
    """Reporte de ventas realizadas"""
    id = models.AutoField(primary_key=True)
    venta_id = models.ForeignKey('ventas.Venta', on_delete=models.CASCADE)
    cliente_id = models.ForeignKey('ventas.Cliente', on_delete=models.CASCADE)
    presentacion_id = models.ForeignKey('productos.PresentacionProducto', on_delete=models.CASCADE)
    vendedor_id = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    fecha = models.DateTimeField()
    generado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reportes_reporteventa'
        ordering = ['-fecha']
        verbose_name = "Reporte de Venta"
        verbose_name_plural = "Reportes de Ventas"

    def __str__(self):
        return f"Venta #{self.venta_id} - ${self.total}"


class ReporteInventario(models.Model):
    """Reporte del estado del inventario"""
    ESTADO_LOTE_CHOICES = [
        ('disponible', 'Disponible'),
        ('reservado', 'Reservado'),
        ('vencido', 'Vencido'),
        ('dañado', 'Dañado'),
    ]

    id = models.AutoField(primary_key=True)
    presentacion_id = models.ForeignKey('productos.PresentacionProducto', on_delete=models.CASCADE)
    lote_id = models.ForeignKey('inventario.Lote', on_delete=models.CASCADE)
    sesion_conteo = models.CharField(max_length=50, null=True, blank=True)
    stock_sistema = models.IntegerField()
    stock_fisico = models.IntegerField()
    diferencia = models.IntegerField()
    estado_lote = models.CharField(max_length=50, choices=ESTADO_LOTE_CHOICES)
    fecha_vencimiento = models.DateField()
    generado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reportes_reporteinventario'
        ordering = ['-generado_en']
        verbose_name = "Reporte de Inventario"
        verbose_name_plural = "Reportes de Inventario"

    def __str__(self):
        return f"Inventario {self.presentacion_id} - Diferencia: {self.diferencia}"


class ReporteCaja(models.Model):
    """Reporte de caja y movimientos de dinero"""
    id = models.AutoField(primary_key=True)
    apertura_id = models.ForeignKey('ventas.AperturaCaja', on_delete=models.SET_NULL, null=True)
    cierre_id = models.ForeignKey('ventas.CierreCaja', on_delete=models.SET_NULL, null=True, blank=True)
    usuario_id = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    total_ventas = models.DecimalField(max_digits=12, decimal_places=2)
    total_devoluciones = models.DecimalField(max_digits=12, decimal_places=2)
    total_contado = models.DecimalField(max_digits=12, decimal_places=2)
    diferencia = models.DecimalField(max_digits=12, decimal_places=2)
    generado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reportes_reportecaja'
        ordering = ['-generado_en']
        verbose_name = "Reporte de Caja"
        verbose_name_plural = "Reportes de Caja"

    def __str__(self):
        return f"Caja - ${self.total_ventas}"


class ReporteCompra(models.Model):
    """Reporte de órdenes de compra"""
    ESTADO_ORDEN_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('confirmada', 'Confirmada'),
        ('recibida', 'Recibida'),
        ('facturada', 'Facturada'),
        ('cancelada', 'Cancelada'),
    ]

    id = models.AutoField(primary_key=True)
    orden_compra_id = models.ForeignKey('proveedores.Compra', on_delete=models.CASCADE)
    proveedor_id = models.ForeignKey('proveedores.Proveedor', on_delete=models.CASCADE)
    presentacion_id = models.ForeignKey('productos.PresentacionProducto', on_delete=models.CASCADE)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    estado_orden = models.CharField(max_length=50, choices=ESTADO_ORDEN_CHOICES)
    fecha = models.DateTimeField()
    generado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reportes_reportecompra'
        ordering = ['-fecha']
        verbose_name = "Reporte de Compra"
        verbose_name_plural = "Reportes de Compras"

    def __str__(self):
        return f"Compra OC-{self.orden_compra_id} - ${self.total}"


class ReporteDevolucion(models.Model):
    """Reporte de devoluciones de clientes"""
    id = models.AutoField(primary_key=True)
    devolucion_id = models.ForeignKey('ventas.Devolucion', on_delete=models.CASCADE)
    venta_id = models.ForeignKey('ventas.Venta', on_delete=models.CASCADE)
    cliente_id = models.ForeignKey('ventas.Cliente', on_delete=models.CASCADE)
    total_devuelto = models.DecimalField(max_digits=12, decimal_places=2)
    motivo = models.CharField(max_length=255)
    fecha = models.DateTimeField()
    generado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reportes_reportedevolucion'
        ordering = ['-fecha']
        verbose_name = "Reporte de Devolución"
        verbose_name_plural = "Reportes de Devoluciones"

    def __str__(self):
        return f"Devolución {self.cliente_id} - ${self.total_devuelto}"


class ReporteLote(models.Model):
    """Reporte de lotes de productos"""
    ESTADO_CHOICES = [
        ('vigente', 'Vigente'),
        ('proximo_vencer', 'Próximo a Vencer'),
        ('vencido', 'Vencido'),
    ]

    id = models.AutoField(primary_key=True)
    lote_id = models.ForeignKey('inventario.Lote', on_delete=models.CASCADE)
    presentacion_id = models.ForeignKey('productos.PresentacionProducto', on_delete=models.CASCADE)
    stock_actual = models.IntegerField()
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_vencimiento = models.DateField()
    dias_para_vencer = models.IntegerField()
    estado = models.CharField(max_length=50, choices=ESTADO_CHOICES)
    generado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reportes_reportelote'
        ordering = ['fecha_vencimiento']
        verbose_name = "Reporte de Lote"
        verbose_name_plural = "Reportes de Lotes"

    def __str__(self):
        return f"Lote {self.lote_id} - Vence: {self.fecha_vencimiento}"