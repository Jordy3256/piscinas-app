# JVAQUA v3.6.1 — Corrección modelos de mantenimiento digital

Corrige la actualización v3.6.0, donde `admin.py`, `views.py` y la migración 0013 referenciaban `PlanMantenimientoPiscina` y `RegistroMantenimientoPiscina`, pero ambas clases no quedaron incluidas al final de `asistente_tecnico/models.py`.

Este parche solo reemplaza `asistente_tecnico/models.py`. Después de copiarlo ejecutar:

    python manage.py migrate
    python manage.py check
    python manage.py makemigrations --check --dry-run
    python manage.py collectstatic --noinput
