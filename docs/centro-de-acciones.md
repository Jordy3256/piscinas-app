# Centro de Acciones Inteligente

El Centro de Acciones es la pantalla inicial del administrador (`/dashboard/inicio/`). Reúne tareas accionables sin duplicar la lógica de los módulos de origen.

## Fuentes de datos

- Cobros y facturación: `Factura` y sus pagos.
- Nómina: `ObligacionTrabajador` y pagos asociados.
- Operación: `Mantenimiento`.
- Programación: `Contrato.programado_hasta`.
- Actividad: `ActividadSistema`.

## Reglas

- Las facturas anuladas no aparecen.
- Los cobros se clasifican como vencidos, del día o próximos.
- La nómina se agrupa por trabajador y muestra el saldo consolidado.
- Los mantenimientos atrasados y sin asignar se priorizan.
- Las alertas financieras se actualizan al abrir la pantalla.

## Navegación

Cada acción lleva directamente al formulario o detalle correspondiente. El Dashboard analítico permanece disponible como pantalla separada.
