"""Recordatorios y push exclusivos AQUO360. Nunca importa dashboard.models."""
import json
import logging
from datetime import datetime, time, timedelta
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from .models import (PerfilSuscriptor, PlanMantenimientoPiscina, VisitaProgramadaPiscina,
                     NotificacionDigital, CobroPiscinaDigital, SuscripcionPushDigital, EntregaPushDigital)
from .cartera_digital import crear_cobros_mes, generar_avisos_cobros

logger = logging.getLogger(__name__)
BASE_DIGITAL = "/dashboard/asistente/digital/"


def generar_recordatorios_mantenimientos(fecha=None):
    """Solo visitas de hoy, sin duplicar ni reactivar visitas finalizadas."""
    fecha = fecha or timezone.localdate()
    hora = timezone.make_aware(datetime.combine(fecha, time(7)), timezone.get_current_timezone())
    nuevos = 0
    planes = PlanMantenimientoPiscina.objects.select_related("piscina__suscriptor").filter(
        activo=True, piscina__activa=True, piscina__suscriptor__estado="activo",
    )
    for plan in planes:
        perfil = plan.piscina.suscriptor
        if not perfil.tiene_acceso or plan.creado_en.date() > fecha or plan.piscina.creado_en.date() > fecha:
            continue
        dias = [int(d) for d in (plan.dias_semana or []) if str(d).isdigit() and 0 <= int(d) <= 6]
        if not dias:
            # Compatibilidad con los planes creados antes de seleccionar días.
            dias = sorted({(plan.creado_en.date().weekday() + int(i * 7 / plan.frecuencia_semanal)) % 7 for i in range(plan.frecuencia_semanal)})
        if fecha.weekday() not in dias:
            continue
        visita, _ = VisitaProgramadaPiscina.objects.get_or_create(
            plan=plan, fecha=fecha, visita_numero=1,
            defaults={"piscina": plan.piscina, "plan_resultado": {"tareas": plan.rutina_visita(1)}},
        )
        if visita.estado != "programada":
            continue
        _, creada = NotificacionDigital.objects.get_or_create(
            suscriptor=perfil, visita=visita, tipo="visita_hoy",
            defaults={"piscina": plan.piscina, "titulo": f"Mantenimiento: {plan.piscina.nombre}",
                      "mensaje": f"Hoy tienes programado el mantenimiento de {plan.piscina.nombre}.",
                      "programada_para": hora},
        )
        nuevos += int(creada)
    return nuevos


def generar_avisos_renovacion(fecha=None):
    """Avisos 3, 1 y 0 días antes de vencer: solo suscripciones activas.

    La fecha del aviso sirve de clave idempotente. No cambia el plan, ni cobra,
    ni modifica permisos. Los avisos pertenecen al suscriptor digital.
    """
    fecha = fecha or timezone.localdate()
    fecha_aviso = timezone.make_aware(datetime.combine(fecha, time(7)), timezone.get_current_timezone())
    nuevos = 0
    perfiles = PerfilSuscriptor.objects.filter(
        estado="activo", acceso_hasta__in=[fecha, fecha + timedelta(days=1), fecha + timedelta(days=3)],
    )
    for perfil in perfiles.iterator():
        if not perfil.tiene_acceso:
            continue
        restantes = (perfil.acceso_hasta - fecha).days
        mensaje = (
            "Tu suscripción AQUO360 vence hoy. Renueva para mantener el acceso."
            if restantes == 0 else
            f"Tu suscripción AQUO360 vence en {restantes} día(s) "
            f"({perfil.acceso_hasta:%d/%m/%Y}). Puedes solicitar la renovación."
        )
        _, creado = NotificacionDigital.objects.get_or_create(
            suscriptor=perfil, tipo="suscripcion_proxima", programada_para=fecha_aviso,
            defaults={"titulo": "Renueva tu suscripción AQUO360", "mensaje": mensaje},
        )
        nuevos += int(creado)
    return nuevos


def generar_recordatorios_digitales(fecha=None):
    fecha = fecha or timezone.localdate()
    nuevos_visitas = generar_recordatorios_mantenimientos(fecha)
    nuevas_renovaciones = generar_avisos_renovacion(fecha)
    nuevos_cargos = 0
    for perfil in PerfilSuscriptor.objects.filter(plan="empresarial", estado="activo"):
        if perfil.tiene_acceso:
            nuevos_cargos += crear_cobros_mes(perfil, fecha.year, fecha.month)
    nuevos_cobros = generar_avisos_cobros(fecha)
    return {"visitas": nuevos_visitas, "cargos": nuevos_cargos, "cobros": nuevos_cobros, "renovaciones": nuevas_renovaciones}


def _aviso_vigente(n):
    perfil = n.suscriptor
    if not perfil.tiene_acceso:
        return False
    if n.tipo == "suscripcion_proxima":
        fecha_aviso = timezone.localtime(n.programada_para).date()
        return bool(
            n.suscriptor.estado == "activo"
            and n.suscriptor.acceso_hasta
            and (n.suscriptor.acceso_hasta - fecha_aviso).days in (0, 1, 3)
            and fecha_aviso == timezone.localdate()
        )
    if n.visita_id:
        return bool(n.visita.estado == "programada" and n.visita.plan.activo and n.visita.fecha == timezone.localdate()
                    and n.piscina and n.piscina.activa and n.visita.piscina_id == n.piscina_id)
    if n.cobro_id:
        c = n.cobro
        hoy = timezone.localdate()
        return bool(perfil.plan == "empresarial" and c.piscina_id == n.piscina_id
                    and c.piscina.suscriptor_id == perfil.pk and c.piscina.activa
                    and c.piscina.recordatorio_cobro_activo and c.saldo > 0
                    and ((n.tipo == "cobro_proximo" and c.vencimiento == hoy + timedelta(days=1))
                         or (n.tipo == "cobro_hoy" and c.vencimiento == hoy)
                         or (n.tipo == "cobro_vencido" and c.vencimiento < hoy)))
    return False


def enviar_push_digitales():
    """Envío programado con trazabilidad por dispositivo e idempotencia de reintentos."""
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        logger.error("pywebpush no instalado; omitiendo push AQUO360")
        return {"enviados": 0, "fallidos": 0, "motivo": "pywebpush ausente"}
    clave = (getattr(settings, "VAPID_PRIVATE_KEY", "") or "").strip()
    if not clave:
        return {"enviados": 0, "fallidos": 0, "motivo": "VAPID_PRIVATE_KEY no configurada"}
    ahora = timezone.now()
    comienzo = timezone.make_aware(datetime.combine(timezone.localdate(), time.min), timezone.get_current_timezone())
    avisos = NotificacionDigital.objects.select_related("suscriptor", "piscina", "visita", "cobro__piscina").filter(
        programada_para__gte=comienzo, programada_para__lte=ahora, leida=False,
        tipo__in=["visita_hoy", "cobro_proximo", "cobro_hoy", "cobro_vencido", "suscripcion_proxima"],
    )
    enviados = fallidos = 0
    for aviso in avisos.iterator():
        if not _aviso_vigente(aviso):
            continue
        for sub in SuscripcionPushDigital.objects.filter(suscriptor=aviso.suscriptor):
            entrega, _ = EntregaPushDigital.objects.get_or_create(notificacion=aviso, suscripcion=sub)
            if entrega.estado == "enviado" or entrega.intentos >= 3:
                continue
            if entrega.ultimo_intento and entrega.ultimo_intento > ahora - timedelta(minutes=15):
                continue
            # Reclamo atómico del intento para evitar duplicados ante dos cron simultáneos.
            actualizado = EntregaPushDigital.objects.filter(pk=entrega.pk, intentos=entrega.intentos).update(
                intentos=entrega.intentos + 1, estado="enviando", ultimo_intento=ahora,
            )
            if not actualizado:
                continue
            enlace = (BASE_DIGITAL + "suscripcion/?renovar=1" if aviso.tipo == "suscripcion_proxima"
                      else BASE_DIGITAL + ("cartera/" if aviso.cobro_id else "agenda/"))
            cuerpo = json.dumps({"title": aviso.titulo, "body": aviso.mensaje, "url": enlace,
                                 "tag": f"aquo360-{aviso.pk}"}, ensure_ascii=False)
            try:
                webpush(subscription_info={"endpoint": sub.endpoint,
                           "keys": {"p256dh": sub.p256dh, "auth": sub.auth}},
                        data=cuerpo, vapid_private_key=clave,
                        vapid_claims={"sub": (getattr(settings, "VAPID_SUBJECT", "") or "mailto:admin@piscinas-app.local").strip()},
                        content_encoding="aes128gcm", ttl=3600)
                EntregaPushDigital.objects.filter(pk=entrega.pk).update(estado="enviado", enviado_en=timezone.now())
                enviados += 1
            except WebPushException as exc:
                codigo = getattr(getattr(exc, "response", None), "status_code", None)
                fallidos += 1
                if codigo in (404, 410):
                    sub.delete()
                else:
                    EntregaPushDigital.objects.filter(pk=entrega.pk).update(estado="fallido")
                    logger.warning("Push AQUO360 falló: aviso=%s codigo=%s", aviso.pk, codigo)
            except Exception:
                fallidos += 1
                EntregaPushDigital.objects.filter(pk=entrega.pk).update(estado="fallido")
                logger.exception("Error de envío push AQUO360 aviso=%s", aviso.pk)
    return {"enviados": enviados, "fallidos": fallidos}
