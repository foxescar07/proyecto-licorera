from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models
from django.utils import timezone

# ── MANAGER DE USUARIO ────────────────────────────────────────────────────────
class UsuarioManager(BaseUserManager):
    def create_user(self, correo, nombre, apellido, documento, password=None):
        if not correo:
            raise ValueError('El usuario debe tener un correo electrónico')
        user = self.model(
            correo=self.normalize_email(correo),
            nombre=nombre,
            apellido=apellido,
            documento=documento,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, correo, nombre, apellido, documento, password=None):
        user = self.create_user(
            correo,
            nombre=nombre,
            apellido=apellido,
            documento=documento,
            password=password,
        )
        user.is_admin = True
        user.save(using=self._db)
        return user

# ── 1. USUARIO ──
class Usuario(AbstractBaseUser):
    documento = models.CharField(max_length=50, primary_key=True, db_column='documento')
    nombre = models.CharField(max_length=100, db_column='nombre')
    apellido = models.CharField(max_length=100, db_column='apellido')
    correo = models.EmailField(unique=True, db_column='correo')
    telefono = models.CharField(max_length=20, blank=True, null=True, db_column='telefono')
    tipo_identificacion = models.CharField(max_length=20, db_column='tipo_identificacion')
    rol = models.CharField(max_length=50, db_column='rol')
    estado = models.CharField(max_length=20, default='activo', db_column='estado')
    foto = models.ImageField(upload_to='usuarios/fotos/', blank=True, null=True, db_column='foto')
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)

    objects = UsuarioManager()

    USERNAME_FIELD = 'correo'
    REQUIRED_FIELDS = ['nombre', 'apellido', 'documento']

    class Meta:
        db_table = 'usuario'

    @property
    def is_staff(self):
        return self.is_admin

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True

# ── 2. BODEGA ──
class Bodega(models.Model):
    codigo_bodega = models.AutoField(primary_key=True, db_column='codigo_bodega')
    nombre = models.CharField(max_length=100, db_column='nombre')
    descripcion = models.TextField(blank=True, null=True, db_column='descripcion')
    estado = models.CharField(max_length=20, db_column='estado')
    capacidad = models.IntegerField(blank=True, null=True, db_column='capacidad')

    class Meta:
        db_table = 'bodega'

    def __str__(self):
        return self.nombre

# ── 3. CATEGORIA ──
class Categoria(models.Model):
    codigo_categoria = models.AutoField(primary_key=True, db_column='codigo_categoria')
    nombre = models.CharField(max_length=100, db_column='nombre')
    descripcion = models.TextField(db_column='descripcion')
    subcategoria = models.CharField(max_length=100, db_column='subcategoria')
    padre = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, db_column='padre_id', related_name='subcategorias')

    class Meta:
        db_table = 'categoria'

    def __str__(self):
        return self.nombre

# ── 4. PRODUCTO ──
class Producto(models.Model):
    codigo_producto = models.AutoField(primary_key=True, db_column='codigo_producto')
    nombre = models.CharField(max_length=150, db_column='nombre')
    descripcion = models.TextField(db_column='descripcion')
    fecha_vencimiento = models.DateField(db_column='fecha_vencimiento')
    categoria = models.ForeignKey('Categoria', on_delete=models.SET_NULL, null=True, blank=True, db_column='codigo_categoria', related_name='productos')

    class Meta:
        db_table = 'producto'

    def __str__(self):
        return self.nombre

# ── 5. PRESENTACION PRODUCTO ──
class PresentacionProducto(models.Model):
    codigo_presentacion = models.AutoField(primary_key=True, db_column='codigo_presentacion')
    precio_venta = models.DecimalField(max_digits=12, decimal_places=2, db_column='precio_venta')
    unidades = models.PositiveIntegerField(db_column='unidades')
    observaciones = models.TextField(blank=True, null=True, db_column='observaciones')
    producto = models.ForeignKey('Producto', on_delete=models.CASCADE, db_column='codigo_producto')

    class Meta:
        db_table = 'presentacion_producto'

    def __str__(self):
        return f"{self.producto.nombre} - {self.unidades} uds"

# ── 6. LOTE ──
class Lote(models.Model):
    codigo_lote = models.AutoField(primary_key=True, db_column='codigo_lote')
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2, db_column='costo_unitario')
    costo_total = models.DecimalField(max_digits=12, decimal_places=2, db_column='costo_total')
    fecha_registro = models.DateTimeField(default=timezone.now, db_column='fecha_registro')
    producto = models.ForeignKey('Producto', on_delete=models.CASCADE, db_column='codigo_producto', related_name='lotes')
    presentacion = models.ForeignKey('PresentacionProducto', on_delete=models.CASCADE, db_column='codigo_presentacion')
    bodega = models.ForeignKey('Bodega', on_delete=models.CASCADE, db_column='codigo_bodega')

    class Meta:
        db_table = 'lote'

# ── 7. MARCA ──
class Marca(models.Model):
    codigo_marca = models.AutoField(primary_key=True, db_column='codigo_marca')
    nombre = models.CharField(max_length=100, db_column='nombre')
    descripcion = models.TextField(db_column='descripcion')
    estado = models.CharField(max_length=20, db_column='estado')

    class Meta:
        db_table = 'marca'

    def __str__(self):
        return self.nombre

# ── 8. DETALLE PRODUCTO ──
class DetalleProducto(models.Model):
    numero_producto = models.AutoField(primary_key=True, db_column='numero_producto')
    codigo_barras = models.CharField(max_length=100, db_column='codigo_barras')
    fecha_vencimiento = models.DateField(db_column='fecha_vencimiento')
    descripcion = models.TextField(db_column='descripcion')
    marca = models.ForeignKey('Marca', on_delete=models.CASCADE, db_column='codigo_marca')
    presentacion = models.ForeignKey('PresentacionProducto', on_delete=models.CASCADE, db_column='codigo_presentacion')
    producto = models.ForeignKey('Producto', on_delete=models.CASCADE, db_column='codigo_producto')

    class Meta:
        db_table = 'detalle_producto'

# ── 9. PROVEEDOR ──
class Proveedor(models.Model):
    nit_proveedores = models.CharField(max_length=50, primary_key=True, db_column='nit_proveedores')
    nombre_empresa = models.CharField(max_length=200, db_column='nombre_empresa')
    telefono = models.CharField(max_length=20, db_column='telefono')
    correo = models.EmailField(db_column='correo')
    tipo_proveedor = models.CharField(max_length=50, db_column='tipo_proveedor')
    estado = models.CharField(max_length=20, db_column='estado')
    observacion = models.TextField(db_column='observacion')
    fecha_registro = models.DateTimeField(default=timezone.now, db_column='fecha_registro')

    class Meta:
        db_table = 'proveedor'

    def __str__(self):
        return self.nombre_empresa

# ── 10. COMPRA ──
class Compra(models.Model):
    codigo_compra = models.AutoField(primary_key=True, db_column='codigo_compra')
    fecha = models.DateTimeField(default=timezone.now, db_column='fecha')
    estado = models.CharField(max_length=20, db_column='estado')
    valor = models.DecimalField(max_digits=12, decimal_places=2, db_column='valor')
    saldo = models.DecimalField(max_digits=12, decimal_places=2, db_column='saldo')
    usuario = models.ForeignKey('Usuario', on_delete=models.PROTECT, db_column='documento_usuario')
    proveedor = models.ForeignKey('Proveedor', on_delete=models.CASCADE, db_column='codigo_proveedor')

    class Meta:
        db_table = 'compra'

# ── 11. DETALLE COMPRA ──
class DetalleCompra(models.Model):
    numero_compra = models.AutoField(primary_key=True, db_column='numero_compra')
    cantidad = models.IntegerField(db_column='cantidad')
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, db_column='precio_unitario')
    fecha_registro = models.DateTimeField(default=timezone.now, db_column='fecha_registro')
    subtotal_compra = models.DecimalField(max_digits=12, decimal_places=2, db_column='subtotal_compra')
    compra = models.ForeignKey('Compra', on_delete=models.CASCADE, db_column='codigo_compra')

    class Meta:
        db_table = 'detalle_compra'

# ── 12. DEVOLUCION PROVEEDORES ──
class DevolucionProveedores(models.Model):
    numero_proveedor = models.AutoField(primary_key=True, db_column='numero_proveedor')
    fecha = models.DateTimeField(default=timezone.now, db_column='fecha')
    motivo = models.TextField(db_column='motivo')
    estado = models.CharField(max_length=20, db_column='estado')
    observaciones = models.TextField(blank=True, null=True, db_column='observaciones')
    proveedor = models.ForeignKey('Proveedor', on_delete=models.CASCADE, db_column='nit_proveedores')

    class Meta:
        db_table = 'devolucion_proveedores'

# ── 18. CAJA ──
class Caja(models.Model):
    codigo_caja = models.AutoField(primary_key=True, db_column='codigo_caja')
    fecha_hora = models.DateTimeField(default=timezone.now, db_column='fecha_hora')
    denominaciones = models.JSONField(default=dict, blank=True, db_column='denominaciones')
    monto_base = models.DecimalField(max_digits=12, decimal_places=2, db_column='monto_base')
    total_efectivo = models.DecimalField(max_digits=12, decimal_places=2, db_column='total_efectivo')
    total_transferencias = models.DecimalField(max_digits=12, decimal_places=2, db_column='total_transferencias')
    total_retirado = models.DecimalField(max_digits=12, decimal_places=2, db_column='total_retirado')
    observacion = models.TextField(blank=True, null=True, db_column='observacion')
    usuario = models.ForeignKey('Usuario', on_delete=models.PROTECT, db_column='documento_usuario')

    class Meta:
        db_table = 'caja'

# ── 13. VENTA ──
class Venta(models.Model):
    codigo_venta = models.AutoField(primary_key=True, db_column='codigo_venta')
    fecha = models.DateTimeField(default=timezone.now, db_column='fecha')
    total_venta = models.DecimalField(max_digits=12, decimal_places=2, db_column='total_venta')
    metodo_pago = models.CharField(max_length=50, db_column='metodo_pago')
    usuario = models.ForeignKey('Usuario', on_delete=models.PROTECT, db_column='documento_usuario')
    caja = models.ForeignKey(Caja, on_delete=models.PROTECT, db_column='codigo_caja', null=True, blank=True, related_name='ventas')

    class Meta:
        db_table = 'venta'

# ── 14. DETALLE VENTA ──
class DetalleVenta(models.Model):
    codigo_detalle_venta = models.AutoField(primary_key=True, db_column='codigo_detalle_venta')
    cantidad = models.IntegerField(db_column='cantidad')
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, db_column='precio_unitario')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, db_column='subtotal')
    total = models.DecimalField(max_digits=12, decimal_places=2, db_column='total')
    venta = models.ForeignKey('Venta', on_delete=models.CASCADE, db_column='codigo_venta')
    producto = models.ForeignKey('Producto', on_delete=models.CASCADE, db_column='codigo_producto')

    class Meta:
        db_table = 'detalle_venta'

# ── 14. PAGO VENTA ──
class PagoVenta(models.Model):
    codigo_pago = models.AutoField(primary_key=True, db_column='codigo_pago')
    fecha_pago = models.DateTimeField(default=timezone.now, db_column='fecha_pago')
    monto = models.DecimalField(max_digits=12, decimal_places=2, db_column='monto')
    observaciones = models.TextField(blank=True, null=True, db_column='observaciones')
    metodo = models.ForeignKey('MetodoPago', on_delete=models.CASCADE, db_column='codigo_metodo')
    venta = models.ForeignKey('Venta', on_delete=models.CASCADE, db_column='codigo_venta')

    class Meta:
        db_table = 'pago_venta'

# ── 15. DEVOLUCION ──
class Devolucion(models.Model):
    codigo_devolucion = models.AutoField(primary_key=True, db_column='codigo_devolucion')
    fecha = models.DateTimeField(default=timezone.now, db_column='fecha')
    motivo = models.TextField(db_column='motivo')
    tipo_devolucion = models.CharField(max_length=50, db_column='tipo_devolucion')
    observaciones = models.TextField(blank=True, null=True, db_column='observaciones')
    presenta_comprobante = models.BooleanField(db_column='presenta_comprobante')
    total_devuelto = models.DecimalField(max_digits=12, decimal_places=2, db_column='total_devuelto')
    estado = models.CharField(max_length=20, db_column='estado')
    cantidad_cambio = models.IntegerField(db_column='cantidad_cambio')
    metodo_pago_devolucion = models.CharField(max_length=50, db_column='metodo_pago_devolucion')
    usuario = models.ForeignKey('Usuario', on_delete=models.PROTECT, db_column='documento_usuario')
    venta = models.ForeignKey('Venta', on_delete=models.CASCADE, db_column='codigo_venta')
    detalle_venta = models.ForeignKey('DetalleVenta', on_delete=models.SET_NULL, null=True, blank=True, db_column='codigo_detalle_venta')

    class Meta:
        db_table = 'devolucion'

# ── 16. DETALLE DEVOLUCION ──
class DetalleDevolucion(models.Model):
    numero_devolucion = models.AutoField(primary_key=True, db_column='numero_devolucion')
    cantidad = models.IntegerField(db_column='cantidad')
    fecha_vencimiento = models.DateField(db_column='fecha_vencimiento')
    descripcion = models.TextField(db_column='descripcion')
    observacion = models.TextField(blank=True, null=True, db_column='observacion')
    devolucion = models.ForeignKey('Devolucion', on_delete=models.CASCADE, db_column='codigo_devolucion')
    producto = models.ForeignKey('Producto', on_delete=models.CASCADE, db_column='codigo_producto')

    class Meta:
        db_table = 'detalle_devolucion'

# ── 17. METODO PAGO ──
class MetodoPago(models.Model):
    codigo_metodo = models.AutoField(primary_key=True, db_column='codigo_metodo')
    fecha = models.DateTimeField(default=timezone.now, db_column='fecha')
    valor = models.DecimalField(max_digits=12, decimal_places=2, db_column='valor')
    referencia = models.CharField(max_length=100, blank=True, null=True, db_column='referencia')
    efectivo = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='efectivo')
    transaccion = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='transaccion')
    observacion = models.TextField(blank=True, null=True, db_column='observacion')
    compra = models.ForeignKey('Compra', on_delete=models.CASCADE, db_column='codigo_compra', null=True, blank=True)

    class Meta:
        db_table = 'metodo_pago'


