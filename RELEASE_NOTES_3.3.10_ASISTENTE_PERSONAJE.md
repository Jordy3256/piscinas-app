# JVAQUA ERP v3.3.10 — Asistente con personaje interactivo

## Cambios
- Se incorpora un robot técnico JVAQUA integrado directamente en la interfaz del Asistente.
- Diseño premium, minimalista y no infantil.
- El personaje tiene animación flotante, parpadeo y núcleo luminoso.
- Mensaje contextual del asistente antes del diagnóstico.
- Estado visual de "analizando" al enviar el formulario.
- Mensaje de diagnóstico listo cuando existe un resultado.
- Se agrega una guía breve junto al formulario para explicar qué datos necesita el Asistente.
- Diseño responsive para móvil y escritorio.

## Instalación
No requiere migraciones.

Ejecutar:
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py collectstatic --noinput
