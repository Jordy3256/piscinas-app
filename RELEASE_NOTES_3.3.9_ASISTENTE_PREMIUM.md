# JVAQUA ERP v3.3.9 — Asistente Premium

Actualización visual del Asistente Técnico Inteligente.

## Cambios
- Hero premium JVAQUA con resumen de capacidades.
- Flujo visual Datos → Diagnóstico → Acción → Cantidades → Verificación.
- Formulario más limpio y moderno, optimizado para móvil.
- Selector de volumen rediseñado sin cambiar su lógica.
- Resultados organizados en bloques visuales claros.
- Cantidades destacadas como tarjetas de dosis.
- Advertencias y seguimiento con jerarquía visual mejorada.
- Academia relacionada integrada visualmente en el resultado.
- Diagnósticos recientes modernizados.

## Importante
- No modifica modelos, migraciones ni lógica del motor.
- No modifica Rutas, Inventario, Finanzas, Contratos ni Mantenimientos.
- Solo reemplaza la plantilla del Asistente.

## Instalación
Extraer sobre la raíz del backend y ejecutar:

python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py collectstatic --noinput
