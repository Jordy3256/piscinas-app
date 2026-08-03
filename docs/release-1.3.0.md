# Notas de versión — JVAQUA ERP 1.3.0

## Objetivo
Mejorar navegación, legibilidad y uso táctil sin modificar la lógica operativa ni financiera.

## Archivos nuevos
- `dashboard/static/dashboard/app-ux-v13.css`
- `dashboard/static/dashboard/app-ux-v13.js`
- `VERSION.md`
- `CHANGELOG.md`
- `docs/design-system.md`
- `docs/release-1.3.0.md`

## Archivos modificados
- `dashboard/templates/dashboard/base_admin.html`
- `dashboard/templates/dashboard/base_trabajador.html`
- `dashboard/templates/dashboard/base_app.html`

## Migraciones
No requiere migraciones.

## Pruebas recomendadas
1. Abrir Clientes, Contratos, Cartera, Nómina e Inventario en un teléfono.
2. Confirmar que sus tablas se muestran como tarjetas y las acciones siguen funcionando.
3. Entrar en un detalle y usar Volver; debe conservar búsqueda, filtros y posición cuando el navegador lo permita.
4. Guardar un formulario y verificar que el botón muestre estado de carga sin duplicar el envío.
5. Revisar administración y panel del trabajador en escritorio.
6. Ejecutar `python manage.py check` y `python manage.py collectstatic --noinput`.
