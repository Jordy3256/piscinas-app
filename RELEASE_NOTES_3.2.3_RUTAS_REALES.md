# JVAQUA ERP v3.2.3 — Rutas inteligentes por carretera

- Sustituye la estimación por distancia lineal por Google Routes API / Route Matrix cuando existe `GOOGLE_MAPS_API_KEY`.
- Calcula tiempos reales por carretera entre la ubicación inicial y todas las piscinas del día.
- Optimiza el orden respetando hora fija, ventana horaria, prioridad y duración estimada.
- Genera una única ruta de Google Maps con todas las paradas en el orden decidido por el ERP.
- Mantiene fallback por cercanía GPS si Google Routes no está configurado o no responde.
- No requiere migraciones.

## Render
Agregar la variable de entorno `GOOGLE_MAPS_API_KEY` con una clave de Google Maps Platform que tenga habilitada **Routes API** y facturación. Restringir la clave a Routes API y, cuando sea posible, a las IP/entorno del servidor.
