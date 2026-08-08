# JVAQUA ERP v1.3.9 — Asistente Técnico Inteligente

## Qué cambia

La Calculadora Química se reemplaza por el **Asistente Técnico Inteligente JVAQUA v1.0**, una herramienta independiente que diagnostica, recomienda procedimientos y conserva su propio historial para evaluar la efectividad de los protocolos con el tiempo.

### Entradas
- Volumen de la piscina (m³).
- pH actual.
- Cloro actual (ppm).
- Estado del agua: transparente, ligeramente turbia, muy turbia o verde.
- Tipo de piscina: residencial, condominio/urbanización, hotel/hostería o pública/alto uso.

### Protocolos
- Agua transparente: mantenimiento normal, corrección gradual de pH y prioridad a tricloro cuando corresponde.
- Turbidez ligera: corrección de pH, cloro granulado y filtración; sin floculación automática.
- Agua muy turbia o verde: choque/floculación con sulfato de aluminio, cloro, alguicida y corrección previa de pH cuando está bajo.
- Sulfato: referencia operativa de 1 kg por cada 25 m³ con tolerancia aproximada de ±5 m³; 32 m³ pasa al siguiente tramo.
- Cal P24: referencia de 250–350 g por cada 25 m³ según qué tan bajo esté el pH.
- Alguicida en choque: 50 g por cada 25 m³.
- Cloro granulado: referencia operativa JVAQUA de 7 g/m³ en refuerzo/choque, con nueva medición para confirmar el objetivo.
- Floculación: 24 horas recomendadas.

## Seguimiento y aprendizaje

Cada caso queda pendiente de seguimiento. Desde aproximadamente 24 horas después, la aplicación consulta al trabajador si funcionó completamente, parcialmente o no funcionó. Si no respondió, puede recordar hasta tres veces, con separación mínima de 24 horas.

Los resultados sirven únicamente para analizar la calidad del Asistente. **No modifican automáticamente las reglas.**

## Independencia

El Asistente no descuenta inventario, no crea consumos, no modifica mantenimientos, no genera movimientos financieros y no altera contratos.

## Administración

Existe un panel para revisar tasa de éxito, fallos frecuentes, rendimiento por protocolo, tipo de piscina y volumen; además permite marcar casos destacados y publicar versiones controladas del motor. Los casos históricos conservan la versión con la que fueron calculados.

## Base de datos

Requiere la migración `asistente_tecnico/migrations/0001_initial.py`.
