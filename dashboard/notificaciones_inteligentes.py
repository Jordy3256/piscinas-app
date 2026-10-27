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
    # Incluye visitas anteriores aún pendientes: no solamente las del día.
    pendientes = Mantenimiento.objects.filter(
        fecha__lte=fecha, estado='pendiente'
    ).prefetch_related('trabajadores__user')
    por_trabajador = defaultdict(lambda: {'hoy': 0, 'atrasados': 0})
    for m in pendientes.iterator(chunk_size=200):
        categoria = 'atrasados' if m.fecha < fecha else 'hoy'
        for t in m.trabajadores.all():
            if t.activo and t.user.is_active:
                por_trabajador[t.pk][categoria] += 1
    resultado = {
        'trabajadores': 0,
        'administradores': 0,
        'pendientes': sum(sum(v.values()) for v in por_trabajador.values()),
    }
    trabajadores = list(Trabajador.objects.filter(pk__in=por_trabajador.keys()).select_related('user'))
    if hora in SLOTS:
        for t in trabajadores:
            cantidades = por_trabajador[t.pk]
            hoy_n, atrasados_n = cantidades['hoy'], cantidades['atrasados']
            total = hoy_n + atrasados_n
            if total and _notify_once(
                t.user, 'resumen_trabajador', key,
                f'{total} mantenimiento(s) pendiente(s)',
                f'A las {SLOTS[hora]} tienes {hoy_n} visita(s) pendiente(s) de hoy y '
                f'{atrasados_n} atrasada(s) de días anteriores.',
                '/dashboard/', dry_run=dry_run,
            ):
                resultado['trabajadores'] += 1
    if por_trabajador:
        detalle = ', '.join(
            f'{t.user.get_full_name() or t.user.username}: '
            f"{por_trabajador[t.pk]['hoy']} hoy, {por_trabajador[t.pk]['atrasados']} atrasadas"
            for t in sorted(trabajadores, key=lambda t: t.user.username.lower())
        )
        titulo = f"Operativo {SLOTS[hora]}: {resultado['pendientes']} asignación(es) pendiente(s)"
        mensaje = f'Pendientes por trabajador (hoy y atrasadas): {detalle}'
        for admin in _admin_users():
            if _notify_once(admin, 'resumen_admin', key, titulo, mensaje[:2000],
                            '/dashboard/operativo/', dry_run=dry_run):
                resultado['administradores'] += 1
    return resultado
