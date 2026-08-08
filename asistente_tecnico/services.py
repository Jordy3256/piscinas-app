from datetime import timedelta
from django.utils import timezone

from .models import CasoAsistenteTecnico


def generar_recordatorios_seguimiento(user=None, crear_notificacion=None, max_recordatorios=3):
    """Crea recordatorios al vencer el seguimiento y vuelve a recordar cada 24 h, máximo 3 veces."""
    ahora = timezone.now()
    qs = CasoAsistenteTecnico.objects.filter(
        resultado="pendiente",
        seguimiento_programado_para__isnull=False,
        seguimiento_programado_para__lte=ahora,
        recordatorios_enviados__lt=max_recordatorios,
    ).select_related("user")
    if user is not None:
        qs = qs.filter(user=user)

    creados = 0
    for caso in qs:
        if caso.ultimo_recordatorio_en and caso.ultimo_recordatorio_en > ahora - timedelta(hours=24):
            continue

        numero = caso.recordatorios_enviados + 1
        titulo = "🧠 Seguimiento de tratamiento"
        if numero == 1:
            mensaje = "Hace aproximadamente 24 horas usaste el Asistente Técnico. ¿El tratamiento dio el resultado esperado?"
        else:
            mensaje = f"Seguimiento pendiente del caso #{caso.pk}. Cuéntanos cómo terminó el agua para seguir mejorando las recomendaciones."
        url = f"/dashboard/asistente/casos/{caso.pk}/seguimiento/"

        if crear_notificacion:
            crear_notificacion(
                user=caso.user,
                titulo=titulo,
                mensaje=mensaje,
                url=url,
                enviar_push=True,
            )
        else:
            from dashboard.models import Notificacion
            # Tipo general evita colisión con unique_together usando referencia nula.
            Notificacion.objects.create(user=caso.user, titulo=titulo, mensaje=mensaje, url=url, tipo="general")

        caso.recordatorios_enviados = numero
        caso.ultimo_recordatorio_en = ahora
        caso.save(update_fields=["recordatorios_enviados", "ultimo_recordatorio_en", "actualizado_en"])
        creados += 1
    return creados
