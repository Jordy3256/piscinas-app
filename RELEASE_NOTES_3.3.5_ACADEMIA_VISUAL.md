# JVAQUA ERP v3.3.5 — Academia visual e interactiva

Actualización incremental. Incluye únicamente archivos nuevos/modificados.

## Cambios
- Rediseño moderno de Academia para uso interno y futuro producto para clientes.
- Nuevas tarjetas visuales con ilustraciones SVG propias.
- Nueva experiencia Aprender / Consultar / Resolver.
- Progreso visual de curso y "Continuar donde quedaste".
- Fichas con hero visual, navegación interna, bloques de buenas prácticas/errores/consejos y contenidos relacionados.
- 11 contenidos oficiales nuevos sobre fundamentos, química, mantenimiento, equipos, seguridad y conocimiento avanzado.
- Ilustraciones de química, balance de agua, bomba, filtro, multiválvula, recuperación de agua, seguridad, bomba de calor, equipos, mantenimiento y circulación.

## Instalación
Extraer sobre la raíz del backend y ejecutar:

python manage.py migrate
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py collectstatic --noinput

No ejecutar makemigrations normal.
