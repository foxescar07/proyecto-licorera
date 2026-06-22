erDiagram

  %% ── USUARIOS ───────────────────────────────────────────
  Usuario {
    int id PK
    string username UK
    string email UK
    string password
    string first_name
    string last_name
    string tipo_id
    string identificacion UK
    string telefono
    string rol
    bool activo
    string reset_token
    datetime reset_token_expira
    image foto
    datetime date_joined
  }

  %% ── PRODUCTOS ──────────────────────────────────────────
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
    int cantidad_disponible
    decimal precio_unitario
    string unidad
    int categoria_id FK
  }

  PresentacionProducto {
    int id PK
    int producto_id FK
    string nombre
    int unidades
    int cantidad
    decimal precio
  }

  %% ── PROVEEDORES ────────────────────────────────────────
  Proveedor {
    int id PK
    string nombre_empresa UK
    string email UK
    string telefono
    string tipo_proveedor
    string estado
    text motivo_sancion
    datetime fecha_registro
    datetime ultima_modificacion
    int registrado_por_id FK
    int modificado_por_id FK
  }

  ProveedorCategoria {
    int id PK
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

  Compra {
    int id PK
    int proveedor_id FK
    int producto_id FK
    int lote_id FK
    int cantidad
    decimal precio_unitario
    datetime fecha_registro
    bool recibida
  }

  %% ── INVENTARIO ─────────────────────────────────────────
  Lote {
    int id PK
    string numero_lote UK
    int presentacion_id FK
    int detalle_compra_id FK
    int stock_actual
    decimal costo_unitario
    date fecha_vencimiento
    datetime fecha_registro
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
    int stock_resultante
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
    text descripcion
    datetime fecha_programada
    string estado
    int creado_por_id FK
    int responsable_id FK
  }

  %% ── VENTAS ─────────────────────────────────────────────
  Cliente {
    int id PK
    string tipo_id
    string identificacion UK
    string nombre
    string telefono
    string email
    string direccion
    datetime fecha_registro
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
    int producto_id FK
    int presentacion_id FK
    int lote_id FK
    int cantidad
    decimal precio_unitario
  }

  AperturaCaja {
    int id PK
    date fecha UK
    decimal monto_base
    int usuario_id FK
    text observacion
    json denominaciones
    datetime creado_en
  }

  CierreCaja {
    int id PK
    date fecha UK
    int apertura_id FK
    decimal total_contado
    decimal monto_base_siguiente
    decimal total_retirado
    json denominaciones
    datetime creado_en
  }

  Devolucion {
    int id PK
    int venta_id FK
    datetime fecha
    string motivo
    string tipo_reembolso
    text observaciones
    bool restaurar_stock
    bool tiene_comprobante
    decimal total_devuelto
    string estado
    string estado_retorno
    string numero_seguimiento UK
    int producto_cambio_id FK
    int cantidad_cambio
    decimal saldo_credito
    bool credito_aplicado
    datetime fecha_aplicacion_credito
    string metodo_pago_devolucion
    datetime fecha_reembolso
    string referencia_reembolso
  }

  DetalleDevolucion {
    int id PK
    int devolucion_id FK
    int producto_id FK
    int presentacion_id FK
    int lote_id FK
    int cantidad
    decimal precio_unitario
  }

  %% ── REPORTES ───────────────────────────────────────────
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

  %% ── RELACIONES: USUARIOS ───────────────────────────────
  Usuario ||--o{ Proveedor : "registra"
  Usuario ||--o{ Proveedor : "modifica"
  Usuario ||--o{ Lote : "registra"
  Usuario ||--o{ Inventario : "registra"
  Usuario ||--o{ SesionConteo : "responsable"
  Usuario ||--o{ AgendaInventario : "crea"
  Usuario ||--o{ AgendaInventario : "responsable"
  Usuario ||--o{ OrdenCompra : "registra"
  Usuario ||--o{ Venta : "vendedor"
  Usuario ||--o{ AperturaCaja : "abre"
  Usuario ||--o{ ReporteCaja : "en"

  %% ── RELACIONES: PRODUCTOS ──────────────────────────────
  Categoria ||--o{ Categoria : "subcategoria"
  Categoria ||--o{ Producto : "clasifica"
  Categoria ||--o{ ProveedorCategoria : "en"
  Producto ||--o{ PresentacionProducto : "tiene"
  Producto ||--o{ Compra : "en"
  Producto ||--o{ DetalleVenta : "en"
  Producto ||--o{ DetalleDevolucion : "en"
  Producto ||--o{ Devolucion : "cambio"

  %% ── RELACIONES: PROVEEDORES ────────────────────────────
  Proveedor ||--o{ ProveedorCategoria : "surte"
  Proveedor ||--o{ OrdenCompra : "en"
  Proveedor ||--o{ Compra : "realiza"
  Proveedor ||--o{ ReporteCompra : "en"
  OrdenCompra ||--o{ DetalleCompra : "contiene"
  OrdenCompra ||--o{ ReporteCompra : "en"
  DetalleCompra ||--o{ Lote : "genera"
  PresentacionProducto ||--o{ DetalleCompra : "en"

  %% ── RELACIONES: INVENTARIO ─────────────────────────────
  PresentacionProducto ||--o{ Lote : "tiene"
  PresentacionProducto ||--o{ Inventario : "mueve"
  PresentacionProducto ||--o{ ConteoProducto : "contada"
  PresentacionProducto ||--o{ ResultadoInventario : "resultado"
  PresentacionProducto ||--o{ ReporteInventario : "en"
  PresentacionProducto ||--o{ ReporteCompra : "en"
  PresentacionProducto ||--o{ ReporteLote : "en"
  Lote ||--o{ Inventario : "afecta"
  Lote ||--o{ Compra : "referencia"
  Lote ||--o{ ReporteInventario : "en"
  Lote ||--o{ ReporteLote : "en"
  SesionConteo ||--o{ ConteoProducto : "contiene"
  SesionConteo ||--o{ ResultadoInventario : "genera"
  SesionConteo ||--o{ ReporteInventario : "en"

  %% ── RELACIONES: VENTAS ─────────────────────────────────
  Cliente ||--o{ Venta : "realiza"
  Cliente ||--o{ ReporteVenta : "en"
  Cliente ||--o{ ReporteDevolucion : "en"
  Venta ||--o{ DetalleVenta : "contiene"
  Venta ||--o{ Devolucion : "origina"
  Venta ||--o{ ReporteVenta : "alimenta"
  Venta ||--o{ ReporteDevolucion : "en"
  PresentacionProducto ||--o{ DetalleVenta : "vendida"
  PresentacionProducto ||--o{ DetalleDevolucion : "devuelta"
  PresentacionProducto ||--o{ ReporteVenta : "en"
  Lote ||--o{ DetalleVenta : "de lote"
  Lote ||--o{ DetalleDevolucion : "de lote"
  Devolucion ||--o{ DetalleDevolucion : "contiene"
  Devolucion ||--o{ ReporteDevolucion : "en"
  AperturaCaja ||--|| CierreCaja : "cierra"
  AperturaCaja ||--o{ ReporteCaja : "en"
  CierreCaja ||--o{ ReporteCaja : "en"