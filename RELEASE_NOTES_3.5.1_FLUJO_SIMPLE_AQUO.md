# JVAQUA v3.5.1 — Flujo simple AQUO

Actualización incremental.

## Cambios
- Resolver inicia con solo dos opciones: problema con el agua / otro problema.
- Agua: solicita pH y cloro, luego aspecto visual y genera diagnóstico.
- Otro problema: recién entonces muestra las categorías técnicas.
- Ayudas contextuales hacia Academia para aprender qué es y cómo medir pH y cloro.
- El estado del flujo químico se conserva temporalmente en el navegador para que el suscriptor pueda abrir la Academia y volver sin empezar desde cero.
- No cambia el motor técnico, modelos, rutas, trabajadores ni ERP.

## Instalación
1. Extraer sobre la raíz del backend y reemplazar.
2. python manage.py check
3. python manage.py makemigrations --check --dry-run
4. python manage.py collectstatic --noinput

No requiere migraciones.
