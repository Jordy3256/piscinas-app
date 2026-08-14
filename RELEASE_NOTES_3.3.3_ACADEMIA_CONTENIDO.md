# JVAQUA ERP 3.3.3 — Academia: problemas, preventivo y equipos

Actualización incremental del contenido oficial de Academia JVAQUA.

Incluye:
- 6 diagnósticos de problemas frecuentes del agua/equipos.
- 4 procedimientos de mantenimiento preventivo.
- 5 fichas adicionales de equipos.
- relaciones entre contenidos y nuevos consejos técnicos.

No modifica rutas inteligentes, finanzas, nómina, contratos ni mantenimientos.

## Instalación

```powershell
python manage.py migrate
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py collectstatic --noinput
```
