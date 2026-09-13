import re
from decimal import Decimal

from django.utils import timezone

from finanzas.models import Factura, ObligacionTrabajador
from .inteligencia_rentabilidad import analizar_rentabilidad
from .inteligencia_crecimiento import analizar_crecimiento_retencion
from .salud_erp import diagnosticar_salud_erp


D0 = Decimal("0.00")


def _money(value):
    return Decimal(value or 0).quantize(Decimal("0.01"))


def construir_snapshot_ejecutivo(*, hoy=None, ciudad=None):
    hoy = hoy or timezone.localdate()
    rent = analizar_rentabilidad(hoy=hoy, ciudad=ciudad)
    crecimiento = analizar_crecimiento_retencion(hoy=hoy, ciudad=ciudad)
    salud = diagnosticar_salud_erp(hoy=hoy)

    facturas = list(
        Factura.objects.exclude(estado=Factura.ESTADO_ANULADA)
        .filter(fecha_emision__year=hoy.year, fecha_emision__month=hoy.month)
        .prefetch_related("pagos")
    )
    cartera_pendiente = sum((_money(f.saldo) for f in facturas if f.saldo > 0), D0)
    cartera_vencida = sum(
        (_money(f.saldo) for f in facturas if f.saldo > 0 and f.fecha_vencimiento and f.fecha_vencimiento < hoy),
        D0,
    )
    cobrado = sum((_money(f.monto_pagado) for f in facturas), D0)

    obligaciones = list(
        ObligacionTrabajador.objects.exclude(estado=ObligacionTrabajador.ESTADO_ANULADO)
        .filter(fecha_pago_programada__year=hoy.year, fecha_pago_programada__month=hoy.month)
        .prefetch_related("pagos")
    )
    nomina_pendiente = sum((_money(o.saldo) for o in obligaciones if o.saldo > 0), D0)

    return {
        "hoy": hoy,
        "ciudad": ciudad,
        "rentabilidad": rent,
        "crecimiento": crecimiento,
        "salud": salud,
        "cartera_pendiente": cartera_pendiente,
        "cartera_vencida": cartera_vencida,
        "cobrado_mes": cobrado,
        "nomina_pendiente": nomina_pendiente,
    }


def _fmt(value):
    return f"${_money(value):,.2f}"


def _respuesta_rentabilidad(s):
    r=s["rentabilidad"]
    riesgos=[x for x in r["filas"] if x["estado"] in {"perdida","critico"}][:5]
    detalle=[
        f"{x['contrato'].cliente}: margen {x['margen_pct']}% ({_fmt(x['margen'])})"
        for x in riesgos
    ]
    texto=(
        f"El margen operativo base es {r['margen_pct']}%, equivalente a {_fmt(r['margen'])}. "
        f"Analizo {r['contratos']} contratos vigentes: {r['en_perdida']} en pérdida, "
        f"{r['criticos']} críticos y {r['atencion']} en atención."
    )
    return texto, detalle, "Revisa primero los contratos en pérdida o con margen menor al 15%."


def _respuesta_crecimiento(s):
    a=s["crecimiento"]["actual"]
    texto=(
        f"Este mes hay {a['altas']} altas, {a['recuperados']} recuperaciones y {a['bajas']} bajas. "
        f"El crecimiento neto es {a['crecimiento_neto']:+d} contratos y la retención estimada es {a['retencion']}%. "
        f"La mensualidad ganada es {_fmt(a['ingreso_ganado'])}, recuperada {_fmt(a['ingreso_recuperado'])} "
        f"y perdida {_fmt(a['ingreso_perdido'])}."
    )
    detalle=[f"{x['ciudad'].nombre}: neto {x['neto']:+d}, {x['activos']} activos" for x in s["crecimiento"]["ranking_ciudades"][:5]]
    return texto, detalle, "Prioriza las ciudades con crecimiento neto negativo y revisa sus motivos de baja."


def _respuesta_cartera(s):
    texto=(
        f"En el mes actual se han registrado {_fmt(s['cobrado_mes'])} en cobros. "
        f"La cartera pendiente es {_fmt(s['cartera_pendiente'])}, de la cual {_fmt(s['cartera_vencida'])} está vencida."
    )
    return texto, [], "Da prioridad a la cartera vencida antes que a los cobros todavía dentro de plazo."


def _respuesta_nomina(s):
    return (
        f"La nómina pendiente del mes es {_fmt(s['nomina_pendiente'])}.",
        [],
        "Revisa las obligaciones vencidas y los trabajadores con saldos pendientes antes del cierre mensual.",
    )


def _respuesta_salud(s):
    h=s["salud"]
    texto=(
        f"El Centro de Salud del ERP reporta {h['criticas']} incidencias críticas, "
        f"{h['atencion']} de atención y {h['avisos']} avisos, afectando {h['total_afectados']} registros."
    )
    detalle=[f"{x['titulo']}: {x['cantidad']}" for x in h.get("incidencias", [])[:6]]
    return texto, detalle, "Abre el Centro de Salud y resuelve primero las incidencias críticas."


def _respuesta_ciudades(s):
    ranking=s["rentabilidad"]["ranking_ciudades"]
    if not ranking:
        return "Todavía no hay información suficiente para comparar ciudades.", [], "Continúa registrando contratos y costos por ciudad."
    detalle=[f"{x['nombre']}: margen {x['margen_pct']}% · {_fmt(x['margen'])}" for x in ranking[:6]]
    mejor=ranking[0]
    return (
        f"La ciudad con mayor contribución operativa es {mejor['nombre']}, con {_fmt(mejor['margen'])} "
        f"de margen base y {mejor['margen_pct']}%.",
        detalle,
        "Compara margen, crecimiento y retención antes de decidir dónde expandir recursos.",
    )


def _respuesta_resumen(s):
    r=s["rentabilidad"]; c=s["crecimiento"]["actual"]; h=s["salud"]
    texto=(
        f"JVAQUA tiene {r['contratos']} contratos vigentes en el análisis, margen operativo base de "
        f"{r['margen_pct']}% ({_fmt(r['margen'])}) y crecimiento neto mensual de {c['crecimiento_neto']:+d}. "
        f"La retención estimada es {c['retencion']}%, la cartera vencida es {_fmt(s['cartera_vencida'])} "
        f"y existen {h['criticas']} incidencias críticas en el ERP."
    )
    prioridades=[]
    if r["en_perdida"] or r["criticos"]: prioridades.append(f"Rentabilidad: {r['en_perdida']} en pérdida y {r['criticos']} críticos.")
    if s["cartera_vencida"] > 0: prioridades.append(f"Cartera: {_fmt(s['cartera_vencida'])} vencida.")
    if c["crecimiento_neto"] < 0: prioridades.append(f"Crecimiento: neto {c['crecimiento_neto']:+d} este mes.")
    if h["criticas"]: prioridades.append(f"Sistema: {h['criticas']} incidencias críticas.")
    if not prioridades: prioridades.append("No detecto una señal ejecutiva crítica en los indicadores principales.")
    return texto, prioridades, "Atiende primero pérdida de margen, cartera vencida y errores críticos del ERP."


def responder_aquo_ejecutivo(pregunta, *, hoy=None, ciudad=None):
    q=re.sub(r"\s+"," ",(pregunta or "").strip().lower())
    snapshot=construir_snapshot_ejecutivo(hoy=hoy, ciudad=ciudad)

    if any(k in q for k in ("rentab","margen","ganancia","perdiendo dinero","pérdida","utilidad","contratos malos")):
        tipo="rentabilidad"; respuesta=_respuesta_rentabilidad(snapshot)
    elif any(k in q for k in ("crec","retenci","alta","baja","recuper","cancel","perdidos")):
        tipo="crecimiento"; respuesta=_respuesta_crecimiento(snapshot)
    elif any(k in q for k in ("cartera","cobro","cobrar","vencid","deben","cuentas por cobrar")):
        tipo="cartera"; respuesta=_respuesta_cartera(snapshot)
    elif any(k in q for k in ("nómina","nomina","trabajador","pagar","sueldo")):
        tipo="nomina"; respuesta=_respuesta_nomina(snapshot)
    elif any(k in q for k in ("salud","error","problema","incidencia","revisar hoy","alerta")):
        tipo="salud"; respuesta=_respuesta_salud(snapshot)
    elif any(k in q for k in ("ciudad","guayaquil","quito","cuenca","manta","portoviejo","samborond")):
        tipo="ciudades"; respuesta=_respuesta_ciudades(snapshot)
    else:
        tipo="resumen"; respuesta=_respuesta_resumen(snapshot)

    texto, detalle, recomendacion=respuesta
    return {
        "tipo": tipo,
        "pregunta": pregunta,
        "respuesta": texto,
        "detalle": detalle,
        "recomendacion": recomendacion,
        "snapshot": snapshot,
    }
