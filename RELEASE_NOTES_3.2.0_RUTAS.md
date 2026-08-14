# JVAQUA ERP 3.2.0 — Rutas inteligentes de mantenimientos

## Implementado
- Ruta sugerida opcional dentro de **Mis mantenimientos** del trabajador.
- Recalculo desde la ubicación actual del dispositivo (con permiso del trabajador).
- Orden sugerido considerando hora fija, ventana horaria, prioridad, duración y cercanía cuando el enlace GPS expone coordenadas.
- Acceso individual a Google Maps y Waze.
- Apertura de ruta completa en Google Maps.
- Progreso de visitas realizadas/pendientes.
- Configuración por contrato: horario libre, hora fija o ventana; duración estimada (30 min por defecto); prioridad normal/alta.
- Advertencia cuando el enlace disponible no permite detectar coordenadas para optimización local.

## Filosofía
La ruta es una ayuda opcional. Nunca bloquea ni obliga el orden de los mantenimientos.

## Instalación
1. `python manage.py migrate`
2. `python manage.py check`
3. `python manage.py makemigrations --check --dry-run`
4. `python manage.py collectstatic --noinput`

Migración incluida: `contratos/migrations/0010_planificacion_rutas.py`.
