"""Cartera de suscriptores Empresarial. Nunca accede a finanzas del ERP JVAQUA."""
import calendar
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from .models import CobroPiscinaDigital, NotificacionDigital, PiscinaSuscriptor


def crear_cobros_mes(perfil, anio, mes):
    """Crea el cargo mensual una sola vez, con valor histórico inmutable."""
    if perfil.plan != "empresarial" or not perfil.tiene_acceso:
        return 0
    periodo = date(anio, mes, 1)
    fin_mes = calendar.monthrange(anio, mes)[1]
    piscinas = PiscinaSuscriptor.objects.filter(suscriptor=perfil, activa=True, valor_mensual__gt=0, dia_cobro__isnull=False)
    creados = 0
    for piscina in piscinas:
        # No crear deuda para un mes anterior al registro real de la piscina.
        if periodo < piscina.creado_en.date().replace(day=1):
            continue
        vencimiento = date(anio, mes, min(piscina.dia_cobro, fin_mes))
        _, nuevo = CobroPiscinaDigital.objects.get_or_create(
            piscina=piscina, periodo=periodo,
            defaults={"vencimiento": vencimiento, "importe": piscina.valor_mensual},
        )
        creados += int(nuevo)
    return creados


def generar_avisos_cobros(fecha=None):
    """Invocar diariamente por cron; evita avisos duplicados y no envía push todavía."""
    fecha = fecha or timezone.localdate()
    avisos = 0
    cobros = CobroPiscinaDigital.objects.select_related("piscina__suscriptor").filter(
        piscina__activa=True, piscina__recordatorio_cobro_activo=True,
        piscina__suscriptor__plan="empresarial", piscina__suscriptor__estado="activo",
        vencimiento__gte=fecha-timedelta(days=30), vencimiento__lte=fecha+timedelta(days=1),
    )
    for cobro in cobros:
        perfil = cobro.piscina.suscriptor
        if not perfil.tiene_acceso or cobro.saldo <= 0:
            continue
        if cobro.vencimiento == fecha + timedelta(days=1):
            tipo, mensaje = "cobro_proximo", "vence mañana"
        elif cobro.vencimiento == fecha:
            tipo, mensaje = "cobro_hoy", "vence hoy"
        elif cobro.vencimiento < fecha:
            tipo, mensaje = "cobro_vencido", "está vencido"
        else:
            continue
        momento = timezone.make_aware(datetime.combine(fecha, time(hour=7)), timezone.get_current_timezone())
        _, creado = NotificacionDigital.objects.get_or_create(
            suscriptor=perfil, cobro=cobro, tipo=tipo,
            defaults={
                "piscina": cobro.piscina, "titulo": f"Cobro: {cobro.piscina.nombre}",
                "mensaje": f"El cobro de {cobro.piscina.nombre} {mensaje}. Saldo ${cobro.saldo:.2f}.",
                "programada_para": momento,
            },
        )
        avisos += int(creado)
    return avisos
