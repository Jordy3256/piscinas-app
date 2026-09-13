import re
from decimal import Decimal

from django.utils import timezone

from finanzas.models import Factura, ObligacionTrabajador
from .inteligencia_rentabilidad import analizar_rentabilidad
from .inteligencia_crecimiento import analizar_crecimiento_retencion
from .salud_erp import diagnosticar_salud_erp
from .inteligencia_cartera import analizar_cartera_inteligente
from .inteligencia_operativa import analizar_operacion
from .inteligencia_inventario import analizar_inventario_inteligente


D0 = Decimal("0.00")


def _money(value):
    return Decimal(value or 0).quantize(Decimal("0.01"))


def construir_snapshot_ejecutivo(*, hoy=None, ciudad=None):
    hoy = hoy or timezone.localdate()
    rent = analizar_rentabilidad(hoy=hoy, ciudad=ciudad)
    crecimiento = analizar_crecimiento_retencion(hoy=hoy, ciudad=ciudad)
    salud = diagnosticar_salud_erp(hoy=hoy)
    cartera_inteligente = analizar_cartera_inteligente(hoy=hoy, ciudad=ciudad)
    operacion = analizar_operacion(hoy=hoy, ciudad=ciudad)
    inventario = analizar_inventario_inteligente(hoy=hoy, ciudad=ciudad)

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
        "cartera_inteligente": cartera_inteligente,
        "operacion": operacion,
        "inventario": inventario,
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
    c=s["cartera_inteligente"]
    texto=(
        f"La cartera pendiente total es {_fmt(c['total'])}, con {_fmt(c['vencido'])} vencidos. "
        f"Hay {c['clientes_prioritarios']} cliente(s) de cobro prioritario y {_fmt(c['recuperable_30'])} "
        f"corresponde a deuda vencida de hasta 30 días."
    )
    detalle=[
        f"{x['cliente']}: {_fmt(x['vencido'])} vencidos · {x['max_dias']} días · prioridad {x['score']}/100"
        for x in c["ranking"][:5]
    ]
    return texto, detalle, "Gestiona primero los clientes con mayor puntaje de cobranza y antigüedad."



def _respuesta_operacion(s):
    o=s["operacion"]
    texto=(
        f"El cumplimiento operativo del mes es {o['cumplimiento']}%: "
        f"{o['realizados_mes']} de {o['programados_mes']} mantenimientos registrados fueron realizados. "
        f"Hay {o['atrasados']} atraso(s), {o['proximos_7']} mantenimiento(s) pendientes en los próximos 7 días "
        f"y {len(o['recurrentes'])} cliente(s) con incidencias recurrentes."
    )
    detalle=[
        f"{x['trabajador'].user.get_full_name() or x['trabajador'].user.username}: "
        f"{x['cumplimiento']}% · {x['atrasados']} atraso(s) · {x['proximos_7']} próximos"
        for x in o["trabajadores"][:5]
    ]
    return texto, detalle, "Prioriza atrasos, trabajadores con menor cumplimiento e incidencias recurrentes."


def _respuesta_inventario(s):
    i=s["inventario"]
    texto=(
        f"El costo químico registrado este mes es {_fmt(i['costo_mes'])}. "
        f"Hay {i['agotados']} producto(s) agotado(s), {i['criticos']} en stock crítico, "
        f"{i['proximos']} próximos al mínimo y {i['anomalos']} contrato(s) con consumo anormal."
    )
    detalle=[
        f"{x['insumo'].nombre}: stock {x['stock']} {x['insumo'].unidad_corta} · "
        + (f"autonomía {x['autonomia_dias']} días" if x["autonomia_dias"] is not None else "sin autonomía calculable")
        for x in i["ranking_productos"][:5]
    ]
    return texto, detalle, "Repón primero productos agotados/críticos y revisa contratos con consumo anormal."


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
    detalle=[f"{x['titulo']}: {x['cantidad']}" for x in h.get("items", [])[:6]]
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
    o=s["operacion"]; i=s["inventario"]; ci=s["cartera_inteligente"]
    texto=(
        f"JVAQUA tiene {r['contratos']} contratos vigentes en el análisis, margen operativo base de "
        f"{r['margen_pct']}% ({_fmt(r['margen'])}) y crecimiento neto mensual de {c['crecimiento_neto']:+d}. "
        f"La retención estimada es {c['retencion']}%, la cartera vencida es {_fmt(s['cartera_vencida'])} "
        f"y existen {h['criticas']} incidencias críticas en el ERP. "
        f"Operación tiene {o['cumplimiento']}% de cumplimiento y {o['atrasados']} atraso(s). "
        f"Inventario reporta {i['agotados']} agotado(s), {i['criticos']} crítico(s) y {i['anomalos']} consumo(s) anormal(es)."
    )
    prioridades=[]
    if r["en_perdida"] or r["criticos"]: prioridades.append(f"Rentabilidad: {r['en_perdida']} en pérdida y {r['criticos']} críticos.")
    if ci["vencido"] > 0: prioridades.append(f"Cartera: {_fmt(ci['vencido'])} vencida · {ci['clientes_prioritarios']} cliente(s) prioritario(s).")
    if o["atrasados"]: prioridades.append(f"Operación: {o['atrasados']} mantenimiento(s) atrasado(s), cumplimiento {o['cumplimiento']}%.")
    if i["agotados"] or i["criticos"]: prioridades.append(f"Inventario: {i['agotados']} agotado(s) y {i['criticos']} producto(s) crítico(s).")
    if i["anomalos"]: prioridades.append(f"Consumo: {i['anomalos']} contrato(s) con desviación anormal.")
    if c["crecimiento_neto"] < 0: prioridades.append(f"Crecimiento: neto {c['crecimiento_neto']:+d} este mes.")
    if h["criticas"]: prioridades.append(f"Sistema: {h['criticas']} incidencias críticas.")
    if not prioridades: prioridades.append("No detecto una señal ejecutiva crítica en los indicadores principales.")
    return texto, prioridades, "Atiende primero pérdida de margen, cartera vencida y errores críticos del ERP."


def _normalizar(texto):
    texto = (texto or "").lower()
    reemplazos = str.maketrans("áéíóúüñ", "aeiouun")
    return re.sub(r"\s+", " ", texto.translate(reemplazos)).strip()


INTENCIONES = {
    "rentabilidad": (
        "rentab", "margen", "ganancia", "utilidad", "perdida", "perdiendo",
        "rentable", "costo", "contratos malos", "contratos en riesgo",
    ),
    "crecimiento": (
        "crec", "retenci", "alta", "baja", "recuper", "cancel", "clientes perdidos",
        "contratos perdidos", "nuevos contratos",
    ),
    "cartera": (
        "cartera", "cobro", "cobrar", "vencid", "deben", "cuentas por cobrar",
        "moros", "morosidad", "pagos de clientes",
    ),
    "operacion": (
        "operacion", "operativo", "mantenimiento", "mantenimientos", "atraso",
        "atrasados", "cumplimiento", "trabajador", "trabajadores", "carga de trabajo",
        "incidencias recurrentes", "servicio",
    ),
    "inventario": (
        "inventario", "stock", "quimico", "quimicos", "consumo", "consumos",
        "cloro", "alguicida", "floculante", "metasilicato", "producto", "productos",
        "autonomia", "agotado", "reposicion",
    ),
    "nomina": (
        "nomina", "sueldo", "salario", "pago trabajadores", "pagar trabajadores",
        "obligaciones trabajadores",
    ),
    "salud": (
        "salud", "error", "problema", "incidencia", "alerta", "fallo",
        "inconsistencia", "revisar hoy", "prioridad", "prioridades",
    ),
    "ciudades": (
        "ciudad", "guayaquil", "quito", "cuenca", "manta", "portoviejo",
        "samborondon", "duran", "azogues", "gualaceo", "crucita", "playas",
        "santa elena",
    ),
}


def _detectar_intenciones(pregunta):
    q = _normalizar(pregunta)
    detectadas = []
    for tipo, palabras in INTENCIONES.items():
        if any(p in q for p in palabras):
            detectadas.append(tipo)

    # Preguntas ejecutivas amplias deben cruzar información, no caer en un único módulo.
    if any(p in q for p in (
        "como esta jvaqua", "como estamos", "resumen", "situacion",
        "que debo hacer", "que deberia hacer", "que revisar", "prioridades",
        "decision", "decisiones", "estado de la empresa",
    )):
        return ["resumen"]

    return detectadas or ["resumen"]


def _prioridades_cruzadas(snapshot):
    r = snapshot["rentabilidad"]
    c = snapshot["crecimiento"]["actual"]
    h = snapshot["salud"]
    prioridades = []

    if r["en_perdida"]:
        prioridades.append((100, f"Rentabilidad: {r['en_perdida']} contrato(s) están generando pérdida."))
    if r["criticos"]:
        prioridades.append((90, f"Margen: {r['criticos']} contrato(s) tienen margen crítico menor al 15%."))
    ci=snapshot["cartera_inteligente"]; o=snapshot["operacion"]; i=snapshot["inventario"]
    if ci["vencido"] > 0:
        prioridades.append((85, f"Cartera: {_fmt(ci['vencido'])} vencida · {ci['clientes_prioritarios']} cliente(s) prioritario(s)."))
    if o["atrasados"] >= 3:
        prioridades.append((88, f"Operación: {o['atrasados']} mantenimientos atrasados; cumplimiento {o['cumplimiento']}%."))
    elif o["atrasados"]:
        prioridades.append((72, f"Operación: {o['atrasados']} mantenimiento(s) atrasado(s)."))
    if i["agotados"] or i["criticos"]:
        prioridades.append((86, f"Inventario: {i['agotados']} agotado(s) y {i['criticos']} producto(s) en stock crítico."))
    if i["anomalos"]:
        prioridades.append((68, f"Consumo: {i['anomalos']} contrato(s) presentan consumo anormal."))
    if h["criticas"]:
        prioridades.append((80, f"ERP: existen {h['criticas']} incidencia(s) crítica(s) que pueden afectar la operación."))
    if c["crecimiento_neto"] < 0:
        prioridades.append((75, f"Crecimiento: el balance mensual es {c['crecimiento_neto']:+d} contratos."))
    if c["retencion"] < 95:
        prioridades.append((70, f"Retención: está en {c['retencion']}%, por debajo de la referencia ejecutiva del 95%."))
    if snapshot["nomina_pendiente"] > 0:
        prioridades.append((45, f"Nómina: quedan {_fmt(snapshot['nomina_pendiente'])} pendientes del mes."))

    prioridades.sort(key=lambda x: x[0], reverse=True)
    return [texto for _, texto in prioridades[:5]] or [
        "Los indicadores principales no muestran una prioridad crítica inmediata."
    ]


def _bloque_por_tipo(tipo, snapshot):
    return {
        "rentabilidad": _respuesta_rentabilidad,
        "crecimiento": _respuesta_crecimiento,
        "cartera": _respuesta_cartera,
        "operacion": _respuesta_operacion,
        "inventario": _respuesta_inventario,
        "nomina": _respuesta_nomina,
        "salud": _respuesta_salud,
        "ciudades": _respuesta_ciudades,
        "resumen": _respuesta_resumen,
    }[tipo](snapshot)


def responder_aquo_ejecutivo(pregunta, *, hoy=None, ciudad=None):
    """
    AQUO Ejecutivo 2.0.

    Interpreta una pregunta administrativa, detecta una o varias áreas y arma
    una respuesta cruzada exclusivamente con datos calculados desde el ERP.
    No modifica información ni inventa valores.
    """
    snapshot = construir_snapshot_ejecutivo(hoy=hoy, ciudad=ciudad)
    intenciones = _detectar_intenciones(pregunta)

    if intenciones == ["resumen"]:
        texto, detalle, recomendacion = _respuesta_resumen(snapshot)
        detalle = _prioridades_cruzadas(snapshot)
        tipo = "resumen ejecutivo"
    elif len(intenciones) == 1:
        tipo = intenciones[0]
        texto, detalle, recomendacion = _bloque_por_tipo(tipo, snapshot)
    else:
        # Respuesta multiárea: conserva una síntesis corta por cada dimensión
        # detectada y termina con prioridades calculadas globalmente.
        partes = []
        detalle = []
        for tipo_detectado in intenciones[:4]:
            bloque_texto, bloque_detalle, _ = _bloque_por_tipo(tipo_detectado, snapshot)
            partes.append(bloque_texto)
            for item in bloque_detalle[:2]:
                detalle.append(item)
        texto = " ".join(partes)
        prioridades = _prioridades_cruzadas(snapshot)
        detalle.extend(prioridades)
        recomendacion = prioridades[0]
        tipo = "análisis cruzado"

    return {
        "tipo": tipo,
        "intenciones": intenciones,
        "pregunta": pregunta,
        "respuesta": texto,
        "detalle": detalle[:10],
        "recomendacion": recomendacion,
        "snapshot": snapshot,
    }
