"""Avisos consolidados de AQUO 360. No altera mantenimientos ni cobros."""
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from mantenimientos.models import Mantenimiento
from trabajadores.models import Trabajador
from .models import Notificacion

ECUADOR = ZoneInfo('America/Guayaquil')
SLOTS = {8: '08:00', 14: '14:00', 20: '20:00'}


def _admin_users():
    from .views import es_admin
    return [u for u in get_user_model().objects.filter(is_active=True).prefetch_related('groups') if es_admin(u)]


def _notify_once(user, tipo, key, titulo, mensaje, url, *, push=True, dry_run=False):
    """Una notificación por usuario/tipo/clave; reintentos no duplican."""
    if dry_run:
        return True
    with transaction.atomic():
        # Serializa ejecuciones simultáneas por usuario en PostgreSQL.
        # No requiere migraciones ni altera las notificaciones existentes.
        get_user_model().objects.select_for_update().get(pk=user.pk)
        obj, created = Notificacion.objects.get_or_create(
            user=user, tipo=tipo, referencia_id=key,
            defaults={'titulo': titulo, 'mensaje': mensaje, 'url': url},
        )
    if created and push:
        from .views import _send_push_to_user
        _send_push_to_user(user, titulo, mensaje, url=url, tag=f'{tipo}-{key}-{user.pk}')
    return created


def enviar_resumenes(hora, *, dry_run=False, fecha=None):
    """Invocar con cron a las 08, 14 y 20, hora de Ecuador."""
    if hora not in SLOTS:
        raise ValueError('Horario no permitido: 08, 14 o 20')
    fecha = fecha or timezone.localtime(timezone.now(), ECUADOR).date()
    key = int(fecha.strftime('%Y%m%d')) * 100 + hora
    pendientes = Mantenimiento.objects.filter(fecha=fecha, estado='pendiente').prefetch_related('trabajadores__user')
    por_trabajador = defaultdict(int)
    for m in pendientes.iterator(chunk_size=200):
        for t in m.trabajadores.all():
            if t.activo and t.user.is_active:
                por_trabajador[t.pk] += 1
    resultado = {'trabajadores': 0, 'administradores': 0, 'pendientes': sum(por_trabajador.values())}
    trabajadores = list(Trabajador.objects.filter(pk__in=por_trabajador.keys()).select_related('user'))
    if hora in (8, 14):
        for t in trabajadores:
            n = por_trabajador[t.pk]
            if n and _notify_once(t.user, 'resumen_trabajador', key,
                f'{n} mantenimiento(s) pendiente(s) hoy',
                f'A las {SLOTS[hora]} tienes {n} mantenimiento(s) programado(s) aún sin registrar como realizado(s).',
                '/dashboard/', dry_run=dry_run):
                resultado['trabajadores'] += 1
    if por_trabajador:
        detalle = ', '.join(f'{t.user.get_full_name() or t.user.username}: {por_trabajador[t.pk]}' for t in sorted(trabajadores, key=lambda t: t.user.username.lower()))
        titulo = f'Operativo {SLOTS[hora]}: {sum(por_trabajador.values())} asignación(es) pendiente(s)'
        mensaje = f'Pendientes de hoy por trabajador: {detalle}'
        for admin in _admin_users():
            if _notify_once(admin, 'resumen_admin', key, titulo, mensaje[:2000],
                            '/dashboard/operativo/', dry_run=dry_run):
                resultado['administradores'] += 1
    return resultado
