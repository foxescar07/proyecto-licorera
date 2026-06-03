erDiagram

  User {
    int id PK
    string username
    string email
    string password
  }
  Perfil {
    int id PK
    int user_id FK
    string tipo_id
    string identificacion UK
    string telefono
    string rol
    bool activo
  }
  Cliente {
    int id PK
    string nombre
    string identificacion
    string telefono
    string email
  }

  Categoria {
    int id PK
    string codigo UK
    string nombre
    text descripcion
    int padre_id FK
  }
  Producto {
    int id PK
    string codigo UK
    string nombre
    text descripcion
    string unidad
    int categoria_id FK
  }
  PresentacionProducto {
    int id PK
    int producto_id FK
    string nombre
    int unidades
    decimal precio
  }

  Proveedor {
    int id PK
    string nombre_empresa
    string email UK
    string telefono
    string tipo_proveedor
    string estado
    int registrado_por_id FK
  }
  ProveedorCategoria {
    int proveedor_id FK
    int categoria_id FK
  }
  OrdenCompra {
    int id PK
    int proveedor_id FK
    int registrado_por_id FK
    datetime fecha
    string estado
    decimal total
  }
  DetalleCompra {
    int id PK
    int orden_compra_id FK
    int presentacion_id FK
    int cantidad
    decimal precio_unitario
  }

  Lote {
    int id PK
    string numero_lote UK
    int presentacion_id FK
    int detalle_compra_id FK
    int stock_actual
    decimal costo_unitario
    date fecha_vencimiento
    int registrado_por_id FK
  }
  Inventario {
    int id PK
    int presentacion_id FK
    int lote_id FK
    int registrado_por_id FK
    string tipo
    int cantidad
    string motivo
    datetime fecha_actualizada
  }
  SesionConteo {
    int id PK
    datetime fecha_inicio
    string estado
    datetime fecha_fin
    int responsable_id FK
  }
  ConteoProducto {
    int id PK
    int sesion_id FK
    int presentacion_id FK
    int cantidad_contada
    datetime actualizado_en
  }
  ResultadoInventario {
    int id PK
    int sesion_id FK
    int presentacion_id FK
    int cantidad_sistema
    int cantidad_fisica
    int diferencia
  }
  AgendaInventario {
    int id PK
    string titulo
    datetime fecha_programada
    string estado
    int creado_por_id FK
    int responsable_id FK
  }

  Venta {
    int id PK
    int cliente_id FK
    int vendedor_id FK
    datetime fecha
    decimal descuento_porcentaje
    decimal total_con_descuento
    decimal pago_efectivo
    decimal pago_tarjeta
    decimal pago_transferencia
    decimal pago_nequi
    decimal pago_daviplata
  }
  DetalleVenta {
    int id PK
    int venta_id FK
    int presentacion_id FK
    int lote_id FK
    int cantidad
    decimal precio_unitario
  }
  AperturaCaja {
    int id PK
    int usuario_id FK
    datetime fecha_apertura
    decimal monto_base
    json denominaciones
  }
  CierreCaja {
    int id PK
    int apertura_id FK
    int usuario_id FK
    datetime fecha_cierre
    int turno
    decimal total_contado
    decimal total_retirado
    decimal monto_base_siguiente
    json denominaciones
  }
  Devolucion {
    int id PK
    int venta_id FK
    int registrado_por_id FK
    datetime fecha
    string motivo
    text observaciones
    bool restaurar_stock
    bool tiene_comprobante
    decimal total_devuelto
  }
  DetalleDevolucion {
    int id PK
    int devolucion_id FK
    int presentacion_id FK
    int lote_id FK
    int cantidad
    decimal precio_unitario
  }

  ReporteVenta {
    int id PK
    int venta_id FK
    int cliente_id FK
    int presentacion_id FK
    int vendedor_id FK
    decimal total
    datetime fecha
    datetime generado_en
  }
  ReporteInventario {
    int id PK
    int presentacion_id FK
    int lote_id FK
    int sesion_conteo_id FK
    int stock_sistema
    int stock_fisico
    int diferencia
    string estado_lote
    date fecha_vencimiento
    datetime generado_en
  }
  ReporteCaja {
    int id PK
    int apertura_id FK
    int cierre_id FK
    int usuario_id FK
    decimal total_ventas
    decimal total_devoluciones
    decimal total_contado
    decimal diferencia
    datetime generado_en
  }
  ReporteCompra {
    int id PK
    int orden_compra_id FK
    int proveedor_id FK
    int presentacion_id FK
    decimal total
    string estado_orden
    datetime fecha
    datetime generado_en
  }
  ReporteDevolucion {
    int id PK
    int devolucion_id FK
    int venta_id FK
    int cliente_id FK
    decimal total_devuelto
    string motivo
    datetime fecha
    datetime generado_en
  }
  ReporteLote {
    int id PK
    int lote_id FK
    int presentacion_id FK
    int stock_actual
    decimal costo_unitario
    date fecha_vencimiento
    int dias_para_vencer
    string estado
    datetime generado_en
  }

  %% ── USUARIOS ───────────────────────────────────────────
  User ||--|| Perfil : "extiende"
  User ||--o{ Proveedor : "registra"
  User ||--o{ Lote : "registra"
  User ||--o{ Inventario : "registra"
  User ||--o{ SesionConteo : "responsable"
  User ||--o{ AgendaInventario : "crea"
  User ||--o{ OrdenCompra : "registra"
  User ||--o{ Venta : "vendedor"
  User ||--o{ AperturaCaja : "abre"
  User ||--o{ CierreCaja : "cierra"
  User ||--o{ Devolucion : "registra"

  %% ── PRODUCTOS ──────────────────────────────────────────
  Categoria ||--o{ Categoria : "subcategoria"
  Categoria ||--o{ Producto : "clasifica"
  Categoria ||--o{ ProveedorCategoria : "en"
  Producto ||--o{ PresentacionProducto : "tiene"

  %% ── COMPRAS ────────────────────────────────────────────
  Proveedor ||--o{ ProveedorCategoria : "surte"
  Proveedor ||--o{ OrdenCompra : "en"
  OrdenCompra ||--o{ DetalleCompra : "contiene"
  DetalleCompra ||--o{ Lote : "genera"
  PresentacionProducto ||--o{ DetalleCompra : "en"

  %% ── INVENTARIO ─────────────────────────────────────────
  PresentacionProducto ||--o{ Lote : "tiene"
  PresentacionProducto ||--o{ Inventario : "mueve"
  PresentacionProducto ||--o{ ConteoProducto : "contada"
  PresentacionProducto ||--o{ ResultadoInventario : "resultado"
  Lote ||--o{ Inventario : "afecta"
  SesionConteo ||--o{ ConteoProducto : "contiene"
  SesionConteo ||--o{ ResultadoInventario : "genera"

  %% ── VENTAS ─────────────────────────────────────────────
  PresentacionProducto ||--o{ DetalleVenta : "vendida"
  PresentacionProducto ||--o{ DetalleDevolucion : "devuelta"
  Lote ||--o{ DetalleVenta : "de lote"
  Lote ||--o{ DetalleDevolucion : "de lote"
  Cliente ||--o{ Venta : "realiza"
  Venta ||--o{ DetalleVenta : "contiene"
  Venta ||--o{ Devolucion : "origina"
  Devolucion ||--o{ DetalleDevolucion : "contiene"
  AperturaCaja ||--o{ CierreCaja : "cierra"

  %% ── REPORTES ───────────────────────────────────────────
  Venta ||--o{ ReporteVenta : "alimenta"
  Cliente ||--o{ ReporteVenta : "en"
  PresentacionProducto ||--o{ ReporteVenta : "en"

  Lote ||--o{ ReporteInventario : "en"
  PresentacionProducto ||--o{ ReporteInventario : "en"
  SesionConteo ||--o{ ReporteInventario : "en"

  AperturaCaja ||--o{ ReporteCaja : "en"
  CierreCaja ||--o{ ReporteCaja : "en"

  OrdenCompra ||--o{ ReporteCompra : "en"
  Proveedor ||--o{ ReporteCompra : "en"
  PresentacionProducto ||--o{ ReporteCompra : "en"

  Devolucion ||--o{ ReporteDevolucion : "en"
  Venta ||--o{ ReporteDevolucion : "en"
  Cliente ||--o{ ReporteDevolucion : "en"

  Lote ||--o{ ReporteLote : "en"
  PresentacionProducto ||--o{ ReporteLote : "en"

