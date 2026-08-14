# JVAQUA ERP — Nómina por fecha programada de pago

## Corrección principal
La generación y consulta de nómina ya no se basan en el mes de inicio del contrato ni en el mes inicial del servicio. Se basan en `fecha_pago_programada`.

## Cambios
- El selector de Nómina ahora representa el mes en que corresponde pagar.
- Se buscan ciclos de servicio anteriores que tengan pago programado en el mes seleccionado.
- El listado administrativo, pago consolidado, PDF y Mi Cuenta usan la misma regla.
- El Centro Financiero proyecta la nómina en el mes real de pago.
- Si aún no existe una factura del cliente, la fecha se calcula desde el calendario comercial del contrato.
- En contratos con dos cuotas de cliente, la nómina consolidada toma el último vencimiento cuando la modalidad depende del cobro del contrato.

## Historial
Las obligaciones con pagos conservan sus valores y fechas históricas. Solo las obligaciones pendientes y sin pagos pueden sincronizarse con cambios de configuración.
