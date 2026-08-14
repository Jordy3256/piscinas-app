# JVAQUA ERP v3.3.6 — Academia · Experiencia educativa

## Cambios
- 10 contenidos oficiales nuevos orientados a formación práctica.
- Biblioteca personal con Favoritos y Consultados recientemente.
- Puente contextual desde cada artículo hacia el Asistente Técnico.
- Mejoras responsive para móvil.
- Se conserva Aprender / Consultar / Resolver.

## Instalación
1. Copiar el contenido del ZIP sobre la raíz del backend y aceptar reemplazos.
2. Ejecutar:
   python manage.py migrate
   python manage.py check
   python manage.py makemigrations --check --dry-run
   python manage.py collectstatic --noinput
