from datetime import timedelta

from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone

from dashboard.models import Notificacion

from .models import Contrato


TIPOS_VIGENCIA = {"contrato_por_vencer", "contrato_vencido"}


def _admins():
    return User.objects.filter(
        Q(is_superuser=True)
        | Q(is_staff=True)
        | Q(groups__name__in=["Administradores", "Administrador", "Admins", "Adimistradores"])
    ).distinct()


def sincronizar_alertas_vencimiento_contratos(*, hoy=None):
    """
    Mantiene alertas administrativas de contratos próximos a vencer o vencidos.

    No desactiva el contrato automáticamente: evita cortar un servicio por una
    decisión administrativa pendiente. La programación y la facturación sí
    respetan la fecha contractual.
    """
    hoy = hoy or timezone.localdate()
    admins = list(_admins())
    activas = set()
    creadas = 0
    actualizadas = 0

    contratos = (
        Contrato.objects.filter(activo=True, fecha_fin_contrato__isnull=False)
        .select_related("cliente")
        .order_by("fecha_fin_contrato", "id")
    )

    for contrato in contratos:
        dias = (contrato.fecha_fin_contrato - hoy).days
        aviso_dias = int(contrato.aviso_vencimiento_dias or 30)

        if dias < 0:
            tipo = "contrato_vencido"
            titulo = "🔴 Contrato vencido"
            mensaje = (
                f"{contrato.cliente}: venció el {contrato.fecha_fin_contrato:%d/%m/%Y}. "
                "Renueva o finaliza administrativamente el contrato."
            )
        elif dias <= aviso_dias:
            tipo = "contrato_por_vencer"
            titulo = "🟡 Contrato próximo a vencer"
            mensaje = (
                f"{contrato.cliente}: vence el {contrato.fecha_fin_contrato:%d/%m/%Y} "
                f"({dias} día(s)). Revisa su renovación."
            )
        else:
            continue

        activas.add((tipo, contrato.pk))
        for admin in admins:
            notif, creada = Notificacion.objects.get_or_create(
                user=admin,
                tipo=tipo,
                referencia_id=contrato.pk,
                defaults={
                    "titulo": titulo,
                    "mensaje": mensaje,
                    "url": f"/dashboard/contratos/{contrato.pk}/",
                },
            )
            if creada:
                creadas += 1
                continue
            cambios = []
            for campo, valor in {
                "titulo": titulo,
                "mensaje": mensaje,
                "url": f"/dashboard/contratos/{contrato.pk}/",
            }.items():
                if getattr(notif, campo) != valor:
                    setattr(notif, campo, valor)
                    cambios.append(campo)
            if cambios:
                notif.save(update_fields=cambios)
                actualizadas += 1

    # Renovaciones o cambios de vigencia limpian las alertas que ya no aplican.
    qs = Notificacion.objects.filter(tipo__in=TIPOS_VIGENCIA)
    eliminadas = 0
    for notif in qs.only("id", "tipo", "referencia_id"):
        if (notif.tipo, notif.referencia_id) not in activas:
            notif.delete()
            eliminadas += 1

    return {
        "contratos_alertados": len(activas),
        "notificaciones_creadas": creadas,
        "notificaciones_actualizadas": actualizadas,
        "notificaciones_eliminadas": eliminadas,
    }
