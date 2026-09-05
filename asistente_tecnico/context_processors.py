from django.utils import timezone

from .models import NotificacionDigital, PerfilSuscriptor


def notificaciones_digitales(request):
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {"digital_notificaciones_pendientes": 0}
    try:
        perfil = request.user.perfil_suscriptor
    except PerfilSuscriptor.DoesNotExist:
        return {"digital_notificaciones_pendientes": 0}
    if not perfil.tiene_acceso:
        return {"digital_notificaciones_pendientes": 0}
    total = NotificacionDigital.objects.filter(
        suscriptor=perfil,
        programada_para__lte=timezone.now(),
        leida=False,
    ).count()
    return {"digital_notificaciones_pendientes": total}
