# Changelog

## 1.3.5 — Inventario Inteligente

- Nuevo inventario general con stock decimal y unidad base en kg para químicos.
- Inventario independiente por trabajador.
- Entregas y devoluciones entre bodega general y técnicos.
- Compras con actualización de costo promedio y egreso automático.
- Ventas conservadas e integradas con el nuevo stock decimal e ingreso financiero.
- Registro de consumos desde cada mantenimiento en gramos, kilogramos o unidades.
- Conversión automática de gramos a kilogramos.
- Descuento automático del inventario del técnico y validación de stock insuficiente.
- Costo químico por mantenimiento usando el costo promedio real del producto.
- Kardex completo por producto y movimientos por trabajador.
- Catálogo multicategoría y presentaciones comerciales.
- PDFs de inventario general, trabajador, Kardex, movimientos, compras y ventas.
- Nueva pestaña Mi inventario dentro de Mi Cuenta del trabajador.

## 1.3.4 — Nómina profesional y periodos de servicio

- El trabajador puede descargar su PDF mensual de nómina desde Mi Cuenta.
- Cada obligación de nómina conserva las fechas históricas de inicio y fin del servicio.
- Los periodos de servicio aparecen en la nómina administrativa, el detalle, Mi Cuenta y los PDFs.
- Los comprobantes consolidados incluyen el periodo real de cada contrato.
- Los contratos modificados posteriormente no alteran los periodos históricos ya guardados.

## 1.3.2 — Centro de Acciones Inteligente

- Nuevo escritorio operativo para administradores.
- Prioridades de cobro, facturación, nómina y mantenimientos.
- Acciones rápidas con acceso directo a cada flujo.
- Resumen diario y actividad reciente.
- Integración con las alertas financieras existentes.
- Diseño responsive para computadora y móvil.

# Historial de cambios

## 1.3.0 — Optimización Integral, Sprint 1

### Mejoras
- Nueva capa global de experiencia móvil para administración, trabajadores y vistas generales.
- Tablas compatibles convertidas automáticamente en tarjetas legibles en teléfonos.
- Botón Volver reforzado, con destino seguro por módulo y sin listeners duplicados.
- Breadcrumb más claro y visible también en móvil.
- Controles táctiles, formularios, modales, paginación y navegación inferior optimizados.
- Conservación del contexto del navegador y la posición de desplazamiento al regresar.
- Indicador de envío de formularios unificado para evitar dobles registros.

### Compatibilidad
- No cambia modelos, migraciones, URLs ni reglas de negocio.
- Mantiene Contratos, Cartera, Nómina, Mantenimientos, Inventario y notificaciones.
