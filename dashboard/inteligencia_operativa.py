from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from mantenimientos.models import Mantenimiento
from trabajadores.models import Trabajador


D0 = Decimal("0.00")


def _city_q(ciudad):
    if ciudad is None:
        return Q()
    return (
        Q(contrato__ciudad_ref=ciudad)
        | Q(contrato__ciudad_ref__isnull=True, cliente__ciudad_ref=ciudad)
    )


def analizar_operacion(*, hoy=None, ciudad=None):
    hoy = hoy or timezone.localdate()
    inicio_mes = hoy.replace(day=1)
    fin_semana = hoy + timedelta(days=7)

    qs = (
        Mantenimiento.objects.filter(_city_q(ciudad))
        .select_related("cliente", "contrato", "contrato__ciudad_ref", "cliente__ciudad_ref")
        .prefetch_related("trabajadores")
    )

    mes = qs.filter(fecha__gte=inicio_mes, fecha__lte=hoy)
    programados_mes = mes.count()
    realizados_mes = mes.filter(estado="realizado").count()
    pendientes_mes = mes.filter(estado="pendiente").count()
    atrasados_qs = qs.filter(estado="pendiente", fecha__lt=hoy)
    atrasados = atrasados_qs.count()
    cumplimiento = round((realizados_mes / programados_mes) * 100, 1) if programados_mes else 100.0

    hoy_qs = qs.filter(fecha=hoy)
    hoy_total = hoy_qs.count()
    hoy_realizados = hoy_qs.filter(estado="realizado").count()
    hoy_pendientes = hoy_qs.filter(estado="pendiente").count()

    proximos = qs.filter(
        estado="pendiente",
        fecha__gte=hoy,
        fecha__lte=fin_semana,
    )

    # Rendimiento por trabajador del mes.
    trabajadores = []
    for t in Trabajador.objects.filter(activo=True).select_related("user").order_by("user__first_name", "user__username"):
        t_mes = mes.filter(trabajadores=t)
        total = t_mes.count()
        realizados = t_mes.filter(estado="realizado").count()
        atras = atrasados_qs.filter(trabajadores=t).count()
        proxima_carga = proximos.filter(trabajadores=t).count()
        if total or atras or proxima_carga:
            tasa = round((realizados / total) * 100, 1) if total else 100.0
            trabajadores.append({
                "trabajador": t,
                "programados": total,
                "realizados": realizados,
                "atrasados": atras,
                "proximos_7": proxima_carga,
                "cumplimiento": tasa,
                "nivel": "critico" if atras >= 3 or tasa < 80 else "atencion" if atras or tasa < 95 else "saludable",
            })
    trabajadores.sort(key=lambda x: (x["atrasados"], -x["cumplimiento"], x["proximos_7"]), reverse=True)

    # Carga futura: próximos 7 días por trabajador.
    carga = sorted(
        [
            {
                "trabajador": x["trabajador"],
                "total": x["proximos_7"],
                "nivel": "alta" if x["proximos_7"] >= 8 else "media" if x["proximos_7"] >= 4 else "normal",
            }
            for x in trabajadores
            if x["proximos_7"]
        ],
        key=lambda x: x["total"],
        reverse=True,
    )

    # Incidencias recurrentes por cliente durante los últimos 60 días.
    desde_incidencias = hoy - timedelta(days=60)
    incidencias_cliente = defaultdict(lambda: {
        "cliente": None,
        "visitas": 0,
        "incidencias": 0,
        "agua": 0,
        "equipos": 0,
        "observaciones": 0,
        "ultima": None,
    })
    recientes = qs.filter(fecha__gte=desde_incidencias, fecha__lte=hoy)
    for m in recientes:
        c = incidencias_cliente[m.cliente_id]
        c["cliente"] = m.cliente
        c["visitas"] += 1
        incidencia = False
        if m.estado_agua_rapido in {"turbidez", "verde"}:
            c["agua"] += 1
            incidencia = True
        if m.equipo_rapido in {"bomba_ruido", "filtro_revision"}:
            c["equipos"] += 1
            incidencia = True
        if (m.observaciones or "").strip():
            c["observaciones"] += 1
            incidencia = True
        if incidencia:
            c["incidencias"] += 1
            if c["ultima"] is None or m.fecha > c["ultima"]:
                c["ultima"] = m.fecha

    recurrentes = []
    for c in incidencias_cliente.values():
        if c["incidencias"] >= 2:
            recurrentes.append({
                **c,
                "url_cliente": reverse("cliente_detalle", args=[c["cliente"].pk]),
                "nivel": "critico" if c["incidencias"] >= 4 else "atencion",
            })
    recurrentes.sort(key=lambda x: (x["incidencias"], x["ultima"] or hoy), reverse=True)

    # Productividad territorial.
    ciudades = defaultdict(lambda: {"nombre": "", "programados": 0, "realizados": 0, "atrasados": 0})
    for m in mes:
        ciudad_obj = m.contrato.ciudad_ref or getattr(m.cliente, "ciudad_ref", None)
        nombre = getattr(ciudad_obj, "nombre", None) or getattr(m.contrato, "ciudad", "") or getattr(m.cliente, "ciudad", "") or "Sin ciudad"
        item = ciudades[nombre]
        item["nombre"] = nombre
        item["programados"] += 1
        if m.estado == "realizado":
            item["realizados"] += 1
    for m in atrasados_qs:
        ciudad_obj = m.contrato.ciudad_ref or getattr(m.cliente, "ciudad_ref", None)
        nombre = getattr(ciudad_obj, "nombre", None) or getattr(m.contrato, "ciudad", "") or getattr(m.cliente, "ciudad", "") or "Sin ciudad"
        ciudades[nombre]["nombre"] = nombre
        ciudades[nombre]["atrasados"] += 1
    ranking_ciudades = []
    for x in ciudades.values():
        x["cumplimiento"] = round((x["realizados"] / x["programados"]) * 100, 1) if x["programados"] else 100.0
        ranking_ciudades.append(x)
    ranking_ciudades.sort(key=lambda x: (x["cumplimiento"], -x["atrasados"]))

    # Riesgos operativos concretos.
    riesgos = []
    for m in atrasados_qs.order_by("fecha")[:20]:
        dias = (hoy - m.fecha).days
        riesgos.append({
            "tipo": "atraso",
            "nivel": "critico" if dias >= 3 else "atencion",
            "titulo": f"{m.cliente} · {dias} día(s) de atraso",
            "texto": f"Mantenimiento programado para {m.fecha.strftime('%d/%m/%Y')}.",
            "url": reverse("mantenimiento_detalle", args=[m.pk]),
        })
    for c in recurrentes[:8]:
        riesgos.append({
            "tipo": "reincidencia",
            "nivel": c["nivel"],
            "titulo": f"{c['cliente']} · incidencias recurrentes",
            "texto": f"{c['incidencias']} visita(s) con novedad en los últimos 60 días.",
            "url": c["url_cliente"],
        })
    riesgos.sort(key=lambda x: 0 if x["nivel"] == "critico" else 1)

    senales = []
    if atrasados >= 5:
        senales.append({"nivel": "critico", "titulo": "Atrasos operativos elevados", "texto": f"Hay {atrasados} mantenimientos pendientes con fecha vencida."})
    elif atrasados:
        senales.append({"nivel": "atencion", "titulo": "Existen mantenimientos atrasados", "texto": f"Hay {atrasados} mantenimiento(s) que requieren reprogramación o cierre."})
    if cumplimiento < 90:
        senales.append({"nivel": "critico", "titulo": "Cumplimiento mensual bajo", "texto": f"El cumplimiento acumulado del mes es {cumplimiento}%."})
    elif cumplimiento < 97:
        senales.append({"nivel": "atencion", "titulo": "Cumplimiento mejorable", "texto": f"El cumplimiento acumulado del mes es {cumplimiento}%."})
    if recurrentes:
        senales.append({"nivel": "atencion", "titulo": "Clientes con incidencias recurrentes", "texto": f"{len(recurrentes)} cliente(s) presentan novedades repetidas en los últimos 60 días."})
    if not senales:
        senales.append({"nivel": "saludable", "titulo": "Operación bajo control", "texto": "No se detectan señales operativas críticas con la información registrada."})

    return {
        "programados_mes": programados_mes,
        "realizados_mes": realizados_mes,
        "pendientes_mes": pendientes_mes,
        "atrasados": atrasados,
        "cumplimiento": cumplimiento,
        "hoy_total": hoy_total,
        "hoy_realizados": hoy_realizados,
        "hoy_pendientes": hoy_pendientes,
        "trabajadores": trabajadores,
        "carga": carga,
        "recurrentes": recurrentes,
        "ranking_ciudades": ranking_ciudades,
        "riesgos": riesgos,
        "senales": senales,
        "proximos_7": proximos.count(),
    }
