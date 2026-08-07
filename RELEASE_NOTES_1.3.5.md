# JVAQUA ERP v1.3.5 — Inventario Inteligente

## Objetivo
Controlar el ciclo completo de los insumos: compra, bodega general, entrega a trabajadores, consumo en mantenimientos, devoluciones, ventas, costos y reportes.

## Novedades principales
- Inventario general y stock por trabajador.
- Químicos almacenados en kg; los técnicos pueden registrar consumos en gramos o kg.
- Compras con costo promedio y egreso financiero automático.
- Ventas integradas con el inventario y los ingresos.
- Entregas y devoluciones de stock entre bodega y trabajadores.
- Consumo de químicos desde cada mantenimiento.
- Protección contra stock insuficiente.
- Costo químico real por visita.
- Kardex y movimientos con trazabilidad completa.
- Reportes PDF.
- Mi inventario en la cuenta del trabajador.

## Compatibilidad
Los consumos históricos se conservan. Los nuevos consumos ya no generan un segundo egreso financiero porque el costo del producto se reconoce al momento de la compra; el mantenimiento conserva el costo operativo para análisis de rentabilidad.

## Migraciones
- inventario/0006_inventario_inteligente.py
- mantenimientos/0009_usoinsumo_inventario_trabajador.py
