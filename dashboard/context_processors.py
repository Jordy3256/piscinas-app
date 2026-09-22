from django.conf import settings

def vapid_public_key(request):
    key = getattr(settings, "VAPID_PUBLIC_KEY", "") or ""
    key = key.replace("\n", "").replace("\r", "").strip()
    return {"VAPID_PUBLIC_KEY": key}

def novedades_mantenimiento_admin(request):
    """Contador global de novedades operativas abiertas para administración."""
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return {"novedades_mantenimiento_pendientes": 0}
    grupos = {g.name.strip().lower() for g in user.groups.all()}
    admin = user.is_superuser or user.is_staff or bool(
        grupos & {"administradores", "administrador", "admins", "adimistradores"}
    )
    if not admin:
        return {"novedades_mantenimiento_pendientes": 0}
    try:
        from mantenimientos.models import NovedadMantenimiento
        total = NovedadMantenimiento.objects.exclude(estado="resuelta").count()
    except Exception:
        total = 0
    return {"novedades_mantenimiento_pendientes": total}
