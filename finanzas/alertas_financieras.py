from __future__ import annotations

import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from dashboard.models import Notificacion

from .models import Factura, ObligacionTrabajador

logger = logging.getLogger(__name__)

TIPOS_FINANCIEROS = {
    "cobro_hoy",
    "cobro_vencido",
    "cobro_proximo",
    "factura_emitir",
    "nomina_pagar",
}


def _usuarios_admin():
    User = get_user_model()
    return (
        User.objects.filter(
            Q(is_superuser=True)
            | Q(is_staff=True)
            | Q(groups__name__in=["Administradores", "Administrador", "Admins", "Adimistradores"])
        )
        .filter(is_active=True)
        .distinct()
    )


def _crear_para_admins(*, tipo, referencia_id, titulo, mensaje, url, enviar_push=True):
    creadas = []
    for user in _usuarios_admin():
        notif, creada = Notificacion.objects.update_or_create(
            user=user,
            tipo=tipo,
            referencia_id=referencia_id,
            defaults={
                "titulo": titulo,
                "mensaje": mensaje,
                "url": url,
            },
        )
        if creada:
            creadas.append((user, notif))

    if enviar_push:
        # Importación diferida para evitar dependencia circular durante el arranque.
        try:
            from dashboard.views import _send_push_to_user

            for user, notif in creadas:
                _send_push_to_user(
                    user=user,
                    title=notif.titulo,
                    body=notif.mensaje,
                    url=notif.url or "/dashboard/notificaciones/",
                    tag=f"{tipo}-{referencia_id}",
                )
        except Exception:
            logger.exception("No fue posible enviar las alertas financieras push.")


def generar_alertas_financieras(*, enviar_push=True):
    """Crea alertas financieras pendientes y elimina las que ya fueron resueltas."""
    hoy = timezone.localdate()
    manana = hoy + timedelta(days=1)

    facturas = (
        Factura.objects.exclude(estado=Factura.ESTADO_ANULADA)
        .select_related("cliente", "contrato")
        .prefetch_related("pagos")
    )
    obligaciones = (
        ObligacionTrabajador.objects.exclude(estado=ObligacionTrabajador.ESTADO_ANULADO)
        .select_related("trabajador", "contrato", "contrato__cliente")
        .prefetch_related("pagos")
    )

    activas = set()

    for factura in facturas:
        if factura.saldo <= 0:
            continue

        url = f"/dashboard/finanzas/facturas/{factura.pk}/"
        if factura.fecha_vencimiento < hoy:
            tipo = "cobro_vencido"
            activas.add((tipo, factura.pk))
            dias = (hoy - factura.fecha_vencimiento).days
            _crear_para_admins(
                tipo=tipo,
                referencia_id=factura.pk,
                titulo="🔴 Cobro vencido",
                mensaje=f"{factura.cliente}: saldo ${factura.saldo:.2f}, con {dias} día(s) de atraso.",
                url=url,
                enviar_push=enviar_push,
            )
        elif (factura.fecha_cobro_desde or factura.fecha_vencimiento) <= hoy <= factura.fecha_vencimiento:
            tipo = "cobro_hoy"
            activas.add((tipo, factura.pk))
            _crear_para_admins(
                tipo=tipo,
                referencia_id=factura.pk,
                titulo="🟠 Cobro pendiente para hoy",
                mensaje=f"{factura.cliente}: gestionar cobro de ${factura.saldo:.2f} ({factura.periodo_label}).",
                url=url,
                enviar_push=enviar_push,
            )
        elif (factura.fecha_cobro_desde or factura.fecha_vencimiento) == manana:
            tipo = "cobro_proximo"
            activas.add((tipo, factura.pk))
            _crear_para_admins(
                tipo=tipo,
                referencia_id=factura.pk,
                titulo="🟡 Cobro programado para mañana",
                mensaje=f"{factura.cliente}: ${factura.saldo:.2f} ({factura.periodo_label}).",
                url=url,
                enviar_push=enviar_push,
            )

        if (
            factura.requiere_factura
            and not factura.factura_enviada
            and factura.fecha_facturacion_programada
            and factura.fecha_facturacion_programada <= hoy
        ):
            tipo = "factura_emitir"
            activas.add((tipo, factura.pk))
            _crear_para_admins(
                tipo=tipo,
                referencia_id=factura.pk,
                titulo="📄 Factura pendiente de emitir/enviar",
                mensaje=f"{factura.cliente}: periodo {factura.periodo_label}.",
                url=url,
                enviar_push=enviar_push,
            )

    for obligacion in obligaciones:
        if obligacion.saldo <= 0 or obligacion.fecha_pago_programada > hoy:
            continue
        tipo = "nomina_pagar"
        activas.add((tipo, obligacion.pk))
        _crear_para_admins(
            tipo=tipo,
            referencia_id=obligacion.pk,
            titulo="🔵 Pago de nómina pendiente",
            mensaje=f"{obligacion.trabajador}: ${obligacion.saldo:.2f} por {obligacion.contrato.cliente}.",
            url=f"/dashboard/finanzas/nomina/?anio={obligacion.periodo_anio}&mes={obligacion.periodo_mes}",
            enviar_push=enviar_push,
        )

    # Las alertas resueltas no deben continuar apareciendo en la campana.
    qs = Notificacion.objects.filter(tipo__in=TIPOS_FINANCIEROS)
    for notif in qs.only("id", "tipo", "referencia_id"):
        if (notif.tipo, notif.referencia_id) not in activas:
            notif.delete()

    return len(activas)
