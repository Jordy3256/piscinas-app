JVAQUA v3.8.0 — Cotizador Inteligente Administrativo

Incluye:
- Nuevo Cotizador Inteligente interno accesible desde Dashboard.
- Comparación con contratos activos de la misma ciudad y frecuencia.
- Precio mínimo, recomendado y objetivo.
- Pago técnico mínimo, recomendado y máximo.
- Estimación de químicos usando consumos históricos recientes cuando existen.
- Utilidad y margen estimados.
- Ajuste por volumen, equipamiento mensual y condiciones especiales.
- Guardado de cotizaciones e historial reciente.
- Ficha técnica opcional en contratos: largo, ancho, profundidades, volumen, uso, tipo,
  filtración, desinfección y observaciones.
- Modelo preparado para equipamiento asociado al contrato.

Instalación:
python manage.py migrate
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py collectstatic --noinput
