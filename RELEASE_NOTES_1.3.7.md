# JVAQUA ERP 1.3.7 — Centro Logístico

## Objetivo
Cerrar la gestión logística desde el ERP y eliminar la dependencia del Admin de Django para administrar productos.

## Novedades
- Catálogo maestro administrable desde `Inventario > Productos`.
- Creación, edición, activación/desactivación y eliminación segura.
- Los productos con historial no se borran físicamente: se desactivan para preservar Kardex, ventas, compras y mantenimientos.
- Ficha y bitácora individual de cada producto.
- Presentaciones comerciales administrables desde la ficha.
- Código interno automático `JVQ-...` para productos sin código.
- Registro de lote y fechas de fabricación/vencimiento en compras.
- Nuevo Centro Logístico con indicadores mensuales.
- Nueva página `Mi Inventario` para trabajadores con datos exclusivamente propios.
- Solicitudes de reposición y aviso al administrador.
- PDFs de stock crítico, consumo por trabajador y consumo por contrato.
- Se conserva la venta de insumos y su integración con ingresos financieros.

## Seguridad
- Las pantallas de catálogo y logística administrativa continúan restringidas a administradores.
- El trabajador solo consulta su propio inventario y sus propios movimientos.
- Solicitar reposición no cambia el stock; la existencia solo cambia cuando administración registra una entrega.

## Migraciones
Sí: `inventario/migrations/0007_centro_logistico.py`.
