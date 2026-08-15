# JVAQUA ERP v3.4.0 · Base JVAQUA Digital

- Nuevo perfil Suscriptor, separado de Administrador y Trabajador.
- Estados preparados para prueba, activo, pausado y vencido; todavía sin pasarela de pagos.
- Portal JVAQUA Digital aislado del ERP.
- Mi Piscina: volumen, dimensiones, filtro, desinfección y piscina principal.
- Resolver en Modo Guiado para suscriptores usando el mismo Motor Técnico JVAQUA.
- Trabajadores conservan el Modo Técnico actual sin cambios.
- Academia compartida con control de contenido Compartido / Solo JVAQUA / Solo suscriptores.
- Login de un suscriptor activo entra directamente a JVAQUA Digital.

## Alta temporal de suscriptores
Desde /admin/: crear primero el User y luego un PerfilSuscriptor asociado. Para acceso inmediato usar estado Activo, o Prueba con fecha válida. La futura pasarela de pagos automatizará este proceso.
