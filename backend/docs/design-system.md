# Design System — JVAQUA ERP

## Principios
1. Móvil primero, sin perjudicar la experiencia de escritorio.
2. Área táctil mínima recomendada: 44–48 px.
3. Acciones primarias visibles; acciones secundarias agrupadas.
4. Mismos estados visuales para éxito, advertencia, error e información.
5. Las tablas grandes deben convertirse en tarjetas o declarar explícitamente desplazamiento horizontal.

## Clases globales disponibles
- `.jv-page-heading`: encabezado de página con título y acciones.
- `.jv-page-actions`: grupo de acciones adaptable.
- `.jv-form-actions`: botones finales de formulario.
- `.jv-mobile-actions`: acciones que ocupan ancho útil en móvil.
- `data-jv-table-mode="scroll"`: conserva una tabla como tabla desplazable en móvil.
- `data-jv-mobile="off"`: excluye una tabla de la transformación automática.

## Formularios
- Botón primario al final y Cancelar/Volver como acción secundaria.
- Campos con etiquetas visibles.
- Errores debajo del campo correspondiente.
- No usar campos menores a 16 px en móvil para evitar zoom automático de iOS.

## Tablas
- En escritorio conservan su estructura tradicional.
- En móvil, las tablas con encabezados se convierten automáticamente en tarjetas.
- Calendarios y matrices deben usar `data-jv-table-mode="scroll"`.
