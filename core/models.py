from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal


# ==============================================================================
# 1. USUARIO (si se referencia o usa como modelo base)
# ==============================================================================
class Usuario(models.Model):
    """
    Entidad: usuario
    PK: documento
    """
    documento = models.CharField(max_length=30, primary_key=True, verbose_name="Documento")
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    apellido = models.CharField(max_length=100, verbose_name="Apellido")
    correo = models.EmailField(unique=True, verbose_name="Correo Electrónico")
    telefono = models.CharField(max_length=20, verbose_name="Teléfono")
    tipo_identificacion = models.CharField(max_length=20, verbose_name="Tipo de Identificación")
    contrasena = models.CharField(max_length=255, verbose_name="Contraseña", db_column="contraseña")
    rol = models.CharField(max_length=50, verbose_name="Rol")
    estado = models.CharField(max_length=20, default="activo", verbose_name="Estado")
    foto = models.ImageField(upload_to="usuarios/fotos/", null=True, blank=True, verbose_name="Foto")

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        db_table = "usuario"

    def __str__(self):
        return f"{self.nombre} {self.apellido} ({self.documento})"


# ==============================================================================
# 2. BODEGA
# ==============================================================================
class Bodega(models.Model):
    """
    Entidad: bodega
    PK: codigo_bodega
    """
    codigo_bodega = models.AutoField(primary_key=True, verbose_name="Código Bodega")
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    estado = models.CharField(max_length=20, default="activo", verbose_name="Estado")
    capacidad = models.PositiveIntegerField(null=True, blank=True, verbose_name="Capacidad")

    class Meta:
        verbose_name = "Bodega"
        verbose_name_plural = "Bodegas"
        db_table = "bodega"

    def __str__(self):
        return f"{self.codigo_bodega} - {self.nombre}"


# ==============================================================================
# 3. CATEGORIA
# ==============================================================================
class Categoria(models.Model):
    """
    Entidad: categoria
    PK: codigo_categoria
    """
    codigo_categoria = models.AutoField(primary_key=True, verbose_name="Código Categoría")
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    subcategoria = models.CharField(max_length=100, blank=True, null=True, verbose_name="Subcategoría")
    padre = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subcategorias_hijas',
        db_column='padre_id',
        verbose_name="Categoría Padre"
    )
    codigo_producto = models.ForeignKey(
        'Producto',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='categorias_relacionadas',
        db_column='codigo_producto',
        verbose_name="Producto Relacionado"
    )

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        db_table = "categoria"

    def __str__(self):
        return self.nombre


# ==============================================================================
# 4. PRODUCTO
# ==============================================================================
class Producto(models.Model):
    """
    Entidad: producto
    PK: codigo_producto
    """
    codigo_producto = models.AutoField(primary_key=True, verbose_name="Código Producto")
    nombre = models.CharField(max_length=150, verbose_name="Nombre")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    fecha_vencimiento = models.DateField(null=True, blank=True, verbose_name="Fecha de Vencimiento")
    codigo_lote = models.ForeignKey(
        'Lote',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='productos_por_lote',
        db_column='codigo_lote',
        verbose_name="Lote"
    )
    codigo_categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='productos',
        db_column='codigo_categoria',
        verbose_name="Categoría"
    )

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        db_table = "producto"

    def __str__(self):
        return f"{self.codigo_producto} - {self.nombre}"


# ==============================================================================
# 5. PRESENTACION PRODUCTO
# ==============================================================================
class PresentacionProducto(models.Model):
    """
    Entidad: presentacion producto
    PK: codigo_presentacion
    """
    codigo_presentacion = models.AutoField(primary_key=True, verbose_name="Código Presentación")
    precio_venta = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Precio de Venta"
    )
    unidades = models.PositiveIntegerField(default=1, verbose_name="Unidades")
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    codigo_producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name='presentaciones',
        db_column='codigo_producto',
        verbose_name="Producto"
    )

    class Meta:
        verbose_name = "Presentación de Producto"
        verbose_name_plural = "Presentaciones de Producto"
        db_table = "presentacion_producto"

    def __str__(self):
        return f"Presentación #{self.codigo_presentacion} - {self.codigo_producto.nombre} ({self.unidades} uds)"


# ==============================================================================
# 6. MARCA
# ==============================================================================
class Marca(models.Model):
    """
    Entidad: marca
    PK: codigo_marca
    """
    codigo_marca = models.AutoField(primary_key=True, verbose_name="Código Marca")
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    estado = models.CharField(max_length=20, default="activo", verbose_name="Estado")
    codigo_presentacion = models.ForeignKey(
        PresentacionProducto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='marcas',
        db_column='codigo_presentacion',
        verbose_name="Presentación"
    )
    codigo_producto = models.ForeignKey(
        Producto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='marcas',
        db_column='codigo_producto',
        verbose_name="Producto"
    )

    class Meta:
        verbose_name = "Marca"
        verbose_name_plural = "Marcas"
        db_table = "marca"

    def __str__(self):
        return self.nombre


# ==============================================================================
# 7. LOTE
# ==============================================================================
class Lote(models.Model):
    """
    Entidad: lote
    PK: codigo_lote
    """
    codigo_lote = models.AutoField(primary_key=True, verbose_name="Código Lote")
    costo_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Costo Unitario"
    )
    costo_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Costo Total"
    )
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")
    codigo_producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name='lotes',
        db_column='codigo_producto',
        verbose_name="Producto"
    )
    codigo_presentacion = models.ForeignKey(
        PresentacionProducto,
        on_delete=models.CASCADE,
        related_name='lotes',
        db_column='codigo_presentacion',
        verbose_name="Presentación"
    )
    codigo_bodega = models.ForeignKey(
        Bodega,
        on_delete=models.CASCADE,
        related_name='lotes',
        db_column='codigo_bodega',
        verbose_name="Bodega"
    )

    class Meta:
        verbose_name = "Lote"
        verbose_name_plural = "Lotes"
        db_table = "lote"

    def __str__(self):
        return f"Lote #{self.codigo_lote} - Prod: {self.codigo_producto_id}"


# ==============================================================================
# 8. DETALLE PRODUCTO
# ==============================================================================
class DetalleProducto(models.Model):
    """
    Entidad: detalle producto
    PK: numero_producto
    """
    numero_producto = models.AutoField(primary_key=True, verbose_name="Número Producto")
    codigo_barras = models.CharField(max_length=50, unique=True, verbose_name="Código de Barras")
    fecha_vencimiento = models.DateField(null=True, blank=True, verbose_name="Fecha de Vencimiento")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    codigo_marca = models.ForeignKey(
        Marca,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='detalles_producto',
        db_column='codigo_marca',
        verbose_name="Marca"
    )
    codigo_presentacion = models.ForeignKey(
        PresentacionProducto,
        on_delete=models.CASCADE,
        related_name='detalles_producto',
        db_column='codigo_presentacion',
        verbose_name="Presentación"
    )
    codigo_producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name='detalles_producto',
        db_column='codigo_producto',
        verbose_name="Producto"
    )

    class Meta:
        verbose_name = "Detalle de Producto"
        verbose_name_plural = "Detalles de Producto"
        db_table = "detalle_producto"

    def __str__(self):
        return f"{self.numero_producto} - Barcode: {self.codigo_barras}"


# ==============================================================================
# 9. PROVEEDOR
# ==============================================================================
class Proveedor(models.Model):
    """
    Entidad: proveedor
    PK: nit_proveedores
    """
    nit_proveedores = models.CharField(max_length=50, primary_key=True, verbose_name="NIT Proveedor")
    nombre_empresa = models.CharField(max_length=200, verbose_name="Nombre de la Empresa")
    telefono = models.CharField(max_length=20, verbose_name="Teléfono")
    correo = models.EmailField(blank=True, null=True, verbose_name="Correo Electrónico")
    tipo_proveedor = models.CharField(max_length=50, blank=True, null=True, verbose_name="Tipo de Proveedor")
    estado = models.CharField(max_length=20, default="activo", verbose_name="Estado")
    observacion = models.TextField(blank=True, null=True, verbose_name="Observación")
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")
    codigo_lote = models.ForeignKey(
        Lote,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='proveedores',
        db_column='codigo_lote',
        verbose_name="Lote Suministrado"
    )
    codigo_marca = models.ForeignKey(
        Marca,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='proveedores',
        db_column='codigo_marca',
        verbose_name="Marca Suministrada"
    )

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        db_table = "proveedor"

    def __str__(self):
        return f"{self.nombre_empresa} ({self.nit_proveedores})"


# ==============================================================================
# 10. COMPRA
# ==============================================================================
class Compra(models.Model):
    """
    Entidad: compra
    PK: codigo_compra
    """
    codigo_compra = models.AutoField(primary_key=True, verbose_name="Código Compra")
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")
    estado = models.CharField(max_length=20, default="pendiente", verbose_name="Estado")
    valor = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Valor"
    )
    saldo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Saldo"
    )
    documento_usuario = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='compras_realizadas',
        db_column='documento_usuario',
        verbose_name="Usuario"
    )
    codigo_proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        related_name='compras',
        db_column='codigo_proveedor',
        verbose_name="Proveedor"
    )

    class Meta:
        verbose_name = "Compra"
        verbose_name_plural = "Compras"
        db_table = "compra"

    def __str__(self):
        return f"Compra #{self.codigo_compra} - Valor: {self.valor}"


# ==============================================================================
# 11. DETALLE COMPRA
# ==============================================================================
class DetalleCompra(models.Model):
    """
    Entidad: detalle compra
    PK: numero_compra
    """
    numero_compra = models.AutoField(primary_key=True, verbose_name="Número Compra")
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)], verbose_name="Cantidad")
    precio_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Precio Unitario"
    )
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")
    subtotal_compra = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Subtotal Compra"
    )
    codigo_compra = models.ForeignKey(
        Compra,
        on_delete=models.CASCADE,
        related_name='detalles',
        db_column='codigo_compra',
        null=True,
        blank=True,
        verbose_name="Compra"
    )

    class Meta:
        verbose_name = "Detalle de Compra"
        verbose_name_plural = "Detalles de Compra"
        db_table = "detalle_compra"

    def __str__(self):
        return f"Detalle #{self.numero_compra} de Compra #{self.codigo_compra_id}"


# ==============================================================================
# 12. METODO DE PAGO
# ==============================================================================
class MetodoPago(models.Model):
    """
    Entidad: Método de pago
    PK: codigo_metodo
    """
    codigo_metodo = models.AutoField(primary_key=True, verbose_name="Código Método")
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")
    valor = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Valor"
    )
    referencia = models.CharField(max_length=100, blank=True, null=True, verbose_name="Referencia")
    efectivo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        blank=True,
        null=True,
        verbose_name="Efectivo"
    )
    transaccion = models.CharField(max_length=100, blank=True, null=True, verbose_name="Transacción")
    observacion = models.TextField(blank=True, null=True, verbose_name="Observación")
    codigo_compra = models.ForeignKey(
        Compra,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='metodos_pago',
        db_column='codigo_compra',
        verbose_name="Compra"
    )

    class Meta:
        verbose_name = "Método de Pago"
        verbose_name_plural = "Métodos de Pago"
        db_table = "metodo_pago"

    def __str__(self):
        return f"Método #{self.codigo_metodo} - Ref: {self.referencia or 'S/R'}"


# ==============================================================================
# 13. CAJA
# ==============================================================================
class Caja(models.Model):
    """
    Entidad: Caja
    PK: codigo_caja
    """
    codigo_caja = models.AutoField(primary_key=True, verbose_name="Código Caja")
    fecha_hora = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora")
    denominaciones = models.TextField(verbose_name="Denominaciones")
    monto_base = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Monto Base"
    )
    total_efectivo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Total Efectivo"
    )
    total_transferencias = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Total Transferencias"
    )
    total_retirado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Total Retirado"
    )
    observacion = models.TextField(blank=True, null=True, verbose_name="Observación")
    documento_usuario = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name='cajas_gestionadas',
        db_column='documento_usuario',
        verbose_name="Usuario"
    )

    class Meta:
        verbose_name = "Caja"
        verbose_name_plural = "Cajas"
        db_table = "caja"

    def __str__(self):
        return f"Caja #{self.codigo_caja} - {self.fecha_hora:%d/%m/%Y %H:%M}"


# ==============================================================================
# 14. VENTA
# ==============================================================================
class Venta(models.Model):
    """
    Entidad: venta
    PK: codigo_venta
    """
    codigo_venta = models.AutoField(primary_key=True, verbose_name="Código Venta")
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")
    total_venta = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Total Venta"
    )
    metodo_pago = models.CharField(max_length=50, verbose_name="Método de Pago")
    documento_usuario = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name='ventas_realizadas',
        db_column='documento_usuario',
        verbose_name="Usuario"
    )

    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        db_table = "venta"

    def __str__(self):
        return f"Venta #{self.codigo_venta} - Total: ${self.total_venta:,.2f}"


# ==============================================================================
# 15. PAGO VENTA
# ==============================================================================
class PagoVenta(models.Model):
    """
    Entidad: pago venta
    PK: codigo_pago
    """
    codigo_pago = models.AutoField(primary_key=True, verbose_name="Código Pago")
    fecha_pago = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Pago")
    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Monto"
    )
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    codigo_metodo = models.ForeignKey(
        MetodoPago,
        on_delete=models.PROTECT,
        related_name='pagos_ventas',
        db_column='codigo_metodo',
        verbose_name="Método de Pago"
    )
    codigo_venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        related_name='pagos',
        db_column='codigo_venta',
        verbose_name="Venta"
    )

    class Meta:
        verbose_name = "Pago de Venta"
        verbose_name_plural = "Pagos de Venta"
        db_table = "pago_venta"

    def __str__(self):
        return f"Pago #{self.codigo_pago} (Venta #{self.codigo_venta_id}) - ${self.monto:,.2f}"


# ==============================================================================
# 16. DEVOLUCION
# ==============================================================================
class Devolucion(models.Model):
    """
    Entidad: devolucion
    PK: codigo_devolucion
    """
    codigo_devolucion = models.AutoField(primary_key=True, verbose_name="Código Devolución")
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")
    motivo = models.CharField(max_length=200, verbose_name="Motivo")
    tipo_devolucion = models.CharField(max_length=50, verbose_name="Tipo de Devolución")
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    presenta_comprobante = models.BooleanField(default=True, verbose_name="Presenta Comprobante")
    total_devuelto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Total Devuelto"
    )
    estado = models.CharField(max_length=20, default="pendiente", verbose_name="Estado")
    cantidad_cambio = models.PositiveIntegerField(default=0, verbose_name="Cantidad Cambio")
    metodo_pago_devolucion = models.ForeignKey(
        MetodoPago,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='devoluciones',
        db_column='metodo_pago_devolucion',
        verbose_name="Método de Pago Devolución"
    )
    documento_usuario = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name='devoluciones_gestionadas',
        db_column='documento_usuario',
        verbose_name="Usuario"
    )
    codigo_venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        related_name='devoluciones',
        db_column='codigo_venta',
        verbose_name="Venta"
    )
    codigo_detalle_venta = models.ForeignKey(
        DetalleProducto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='devoluciones',
        db_column='codigo_detalle_venta',
        verbose_name="Detalle de Venta / Producto"
    )

    class Meta:
        verbose_name = "Devolución"
        verbose_name_plural = "Devoluciones"
        db_table = "devolucion"

    def __str__(self):
        return f"Devolución #{self.codigo_devolucion} - Venta #{self.codigo_venta_id}"


# ==============================================================================
# 17. DETALLE DEVOLUCION
# ==============================================================================
class DetalleDevolucion(models.Model):
    """
    Entidad: detalle devolucion
    PK: numero_devolucion
    """
    numero_devolucion = models.AutoField(primary_key=True, verbose_name="Número Devolución")
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)], verbose_name="Cantidad")
    fecha_vencimiento = models.DateField(null=True, blank=True, verbose_name="Fecha de Vencimiento")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    observacion = models.TextField(blank=True, null=True, verbose_name="Observación")
    codigo_devolucion = models.ForeignKey(
        Devolucion,
        on_delete=models.CASCADE,
        related_name='detalles',
        db_column='codigo_devolucion',
        verbose_name="Devolución"
    )
    codigo_producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name='detalles_devolucion',
        db_column='codigo_producto',
        verbose_name="Producto"
    )

    class Meta:
        verbose_name = "Detalle de Devolución"
        verbose_name_plural = "Detalles de Devolución"
        db_table = "detalle_devolucion"

    def __str__(self):
        return f"Detalle #{self.numero_devolucion} de Devolución #{self.codigo_devolucion_id}"


# ==============================================================================
# 18. DEVOLUCION PROVEEDORES
# ==============================================================================
class DevolucionProveedores(models.Model):
    """
    Entidad: devolucion proveedores
    PK: numero_proveedor
    """
    numero_proveedor = models.AutoField(primary_key=True, verbose_name="Número Proveedor")
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")
    motivo = models.CharField(max_length=200, verbose_name="Motivo")
    estado = models.CharField(max_length=20, default="pendiente", verbose_name="Estado")
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    nit_proveedores = models.ForeignKey(
        Proveedor,
        on_delete=models.CASCADE,
        related_name='devoluciones_proveedor',
        db_column='nit_proveedores',
        verbose_name="Proveedor"
    )

    class Meta:
        verbose_name = "Devolución a Proveedor"
        verbose_name_plural = "Devoluciones a Proveedores"
        db_table = "devolucion_proveedores"

    def __str__(self):
        return f"Devolución Proveedor #{self.numero_proveedor} - {self.nit_proveedores_id}"
