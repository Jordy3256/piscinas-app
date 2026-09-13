from django.db.models import Q
from django.utils import timezone

from .models import (
    NotificacionDigital,
    PerfilSuscriptor,
    ConversacionSoporteDigital,
    MensajeSoporteDigital,
)


def _es_admin(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    grupos = {g.name.strip().lower() for g in user.groups.all()}
    return bool({"administradores", "administrador", "admins", "adimistradores"} & grupos)


def _payload_cliente(perfil):
    resultado = []
    for conv in (
        perfil.conversaciones_soporte.exclude(estado="cerrada")
        .order_by("-ultimo_mensaje_en", "-id")[:8]
    ):
        no_leidos = conv.mensajes.filter(
            remitente="admin",
            leido_cliente=False,
        ).count()
        if no_leidos <= 0:
            continue

        ultimo_entrante_id = (
            conv.mensajes.filter(remitente="admin")
            .order_by("-id")
            .values_list("id", flat=True)
            .first()
            or 0
        )
        resultado.append({
            "id": conv.pk,
            "titulo": "Soporte JVAQUA",
            "subtitulo": (conv.asunto or conv.get_categoria_display())[:80],
            "no_leidos": no_leidos,
            "ultimo_entrante_id": ultimo_entrante_id,
            "estado": conv.estado,
            "estado_label": conv.get_estado_display(),
            "url": f"/dashboard/asistente/digital/soporte/{conv.pk}/?support_float=1",
            "url_completa": f"/dashboard/asistente/digital/soporte/{conv.pk}/",
        })
    return resultado


def _payload_admin():
    resultado = []
    for conv in (
        ConversacionSoporteDigital.objects.exclude(estado="cerrada")
        .select_related("suscriptor__user")
        .order_by("-ultimo_mensaje_en", "-id")[:12]
    ):
        no_leidos = conv.mensajes.filter(
            remitente="cliente",
            leido_admin=False,
        ).count()
        if no_leidos <= 0:
            continue

        ultimo_entrante_id = (
            conv.mensajes.filter(remitente="cliente")
            .order_by("-id")
            .values_list("id", flat=True)
            .first()
            or 0
        )
        user = conv.suscriptor.user
        resultado.append({
            "id": conv.pk,
            "titulo": user.get_full_name() or user.username,
            "subtitulo": (conv.asunto or conv.get_categoria_display())[:80],
            "no_leidos": no_leidos,
            "ultimo_entrante_id": ultimo_entrante_id,
            "estado": conv.estado,
            "estado_label": conv.get_estado_display(),
            "url": f"/dashboard/asistente/administracion/soporte/{conv.pk}/?support_float=1",
            "url_completa": f"/dashboard/asistente/administracion/soporte/{conv.pk}/",
        })
    return resultado

def notificaciones_digitales(request):
    contexto = {
        "digital_notificaciones_pendientes": 0,
        "soporte_cliente_inicial": [],
        "soporte_admin_inicial": [],
    }
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return contexto

    if _es_admin(user):
        contexto["soporte_admin_inicial"] = _payload_admin()

    try:
        perfil = user.perfil_suscriptor
    except PerfilSuscriptor.DoesNotExist:
        return contexto

    if not perfil.tiene_acceso:
        return contexto

    contexto["digital_notificaciones_pendientes"] = NotificacionDigital.objects.filter(
        suscriptor=perfil,
        programada_para__lte=timezone.now(),
        leida=False,
    ).count()
    contexto["soporte_cliente_inicial"] = _payload_cliente(perfil)
    return contexto
