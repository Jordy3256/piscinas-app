# JVAQUA ERP — Sprint 2.2.1

## Operativo
- El cierre del mantenimiento exige únicamente las tres fotografías obligatorias.
- Checklist, inspección y tratamiento químico quedan opcionales.
- Registro parcial como borrador.
- Observaciones rápidas para estado del agua, equipos y recomendaciones.

## Nómina y trabajadores
- Configuración de pago individual por trabajador.
- Modalidades: fin de mes, adelantado, semanal, quincenal, por visita, por contrato y personalizado.
- Programación por fechas de contratos, día fijo o rango de días.
- Pago único, dos pagos, parciales o personalizado.
- Registro de anticipos con egreso automático.
- Descuento automático y progresivo de anticipos al generar la nómina.

## App del trabajador
- Nueva sección **Mi Cuenta**.
- Resumen generado, pagado, pendiente y próximo pago.
- Desglose por contrato.
- Historial de pagos consolidados y anticipos.
- Contratos asignados y estadísticas mensuales.
- Descarga de comprobantes propios con control de acceso.

## Migraciones
- `mantenimientos/0008_mantenimiento_observaciones_rapidas.py`
- `trabajadores/0003_configuracion_pago_trabajador.py`
- `finanzas/0012_anticipotrabajador.py`
