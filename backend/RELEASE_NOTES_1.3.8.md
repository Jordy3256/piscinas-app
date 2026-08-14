# JVAQUA ERP v1.3.8 — Información operativa del cliente

## Cambios

- Se agrega al detalle del mantenimiento una tarjeta compacta con información operativa del cliente.
- Se muestra nombre, dirección, ciudad/sector, frecuencia y fecha de la visita.
- El trabajador asignado dispone de un botón **WhatsApp** con mensaje prellenado:
  "Hola, buenos días. Soy [Nombre del trabajador], técnico de JVAQUA. Me encuentro aquí en su domicilio para realizar el mantenimiento de su piscina."
- El mensaje nunca se envía automáticamente; WhatsApp se abre para que el trabajador decida enviarlo.
- Se agrega botón **Navegar** usando el enlace de Google Maps registrado. Si no existe enlace, se genera una búsqueda de Google Maps a partir de la dirección.
- No se agrega botón de llamada ni se muestran datos financieros/administrativos al trabajador.
- Cada uso del acceso rápido de WhatsApp se registra en Actividad del Sistema como intento de contacto desde la app.
- Solo un trabajador asignado al mantenimiento puede utilizar el acceso rápido de WhatsApp.

## Base de datos

No requiere migraciones.
