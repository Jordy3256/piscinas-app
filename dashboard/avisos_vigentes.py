"""Bandeja inteligente: no borra registros; oculta avisos ya resueltos."""
from datetime import timedelta
from django.utils import timezone
from mantenimientos.models import Mantenimiento

TIPOS_MANTENIMIENTO = {"mantenimiento_hoy", "mantenimiento_manana", "mantenimiento_atrasado", "recordatorio_mantenimiento"}


def avisos_vigentes(user, notificaciones):
    """Filtra en bloque sin consultar una vez por notificación."""
    avisos = list(notificaciones)
    referencias = {n.referencia_id for n in avisos if n.tipo in TIPOS_MANTENIMIENTO and n.referencia_id}
    pendientes = set(Mantenimiento.objects.filter(pk__in=referencias, estado="pendiente").values_list("pk", flat=True)) if referencias else set()
    es_resumen = any(n.tipo == "resumen_trabajador" for n in avisos)
    tiene_pendientes = True
    if es_resumen:
        try:
            trabajador = user.trabajador
            tiene_pendientes = Mantenimiento.objects.filter(
                trabajadores=trabajador, fecha__lte=timezone.localdate(), estado="pendiente"
            ).exists()
        except Exception:
            tiene_pendientes = True  # No ocultar si no es posible comprobarlo.
    return [n for n in avisos if not (
        (n.tipo in TIPOS_MANTENIMIENTO and n.referencia_id and n.referencia_id not in pendientes)
        or (n.tipo == "resumen_trabajador" and not tiene_pendientes)
    )]
