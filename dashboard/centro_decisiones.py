from decimal import Decimal

from django.utils import timezone

from .aquo_ejecutivo import construir_snapshot_ejecutivo


D0 = Decimal("0.00")


def _money(value):
    return Decimal(value or 0).quantize(Decimal("0.01"))


def _decision(*, clave, nivel, prioridad, titulo, motivo, impacto, impacto_tipo,
              accion, url, modulo, dato=None):
    return {
        "clave": clave,
        "nivel": nivel,
        "prioridad": int(prioridad),
        "titulo": titulo,
        "motivo": motivo,
        "impacto": _money(impacto),
        "impacto_tipo": impacto_tipo,
        "accion": accion,
        "url": url,
        "modulo": modulo,
        "dato": dato,
    }


def construir_centro_decisiones(*, hoy=None, ciudad=None):
    """
    Centro de Decisiones Ejecutivo.

    Convierte indicadores ya calculados por el ERP en una cola explicable de
    prioridades. No modifica registros ni intenta sustituir la contabilidad.
    El impacto económico es una referencia mensual estimada para priorización.
    """
    hoy = hoy or timezone.localdate()
    s = construir_snapshot_ejecutivo(hoy=hoy, ciudad=ciudad)
    r = s["rentabilidad"]
    c = s["crecimiento"]["actual"]
    h = s["salud"]
    ci = s["cartera_inteligente"]
    o = s["operacion"]
    i = s["inventario"]

    decisiones = []

    # 1. Contratos que destruyen margen.
    contratos_perdida = [x for x in r["filas"] if x["estado"] == "perdida"]
    if contratos_perdida:
        perdida_mensual = sum(
            (abs(_money(x["margen"])) for x in contratos_perdida if x["margen"] < 0),
            D0,
        )
        decisiones.append(_decision(
            clave="contratos_en_perdida",
            nivel="critica",
            prioridad=100,
            titulo="Contratos generando pérdida",
            motivo=f"{len(contratos_perdida)} contrato(s) tienen margen operativo negativo.",
            impacto=perdida_mensual,
            impacto_tipo="pérdida mensual estimada",
            accion="Revisar precio, costo técnico, químicos y condiciones comerciales de estos contratos.",
            url="/dashboard/inteligencia/rentabilidad/",
            modulo="Rentabilidad",
            dato=f"{len(contratos_perdida)} contrato(s)",
        ))

    # 2. Cartera inteligente: dinero vencido + prioridad de clientes.
    if ci["vencido"] > 0:
        decisiones.append(_decision(
            clave="cartera_vencida",
            nivel="critica",
            prioridad=95,
            titulo="Cobranza vencida pendiente",
            motivo=(
                f"Hay {ci['clientes_prioritarios']} cliente(s) de cobro prioritario "
                f"y ${ci['vencido']:,.2f} de cartera vencida."
            ),
            impacto=ci["vencido"],
            impacto_tipo="capital pendiente de cobro",
            accion="Gestionar primero los clientes con mayor puntaje, antigüedad y reincidencia.",
            url="/dashboard/inteligencia/cartera/",
            modulo="Cartera Inteligente",
            dato=f"${ci['vencido']:,.2f}",
        ))

    # Operación en campo.
    if o["atrasados"] >= 3 or o["cumplimiento"] < 90:
        decisiones.append(_decision(
            clave="riesgo_operativo",
            nivel="critica",
            prioridad=94,
            titulo="Riesgo de incumplimiento operativo",
            motivo=f"{o['atrasados']} mantenimiento(s) atrasado(s) y {o['cumplimiento']}% de cumplimiento mensual.",
            impacto=D0,
            impacto_tipo="impacto económico no cuantificado",
            accion="Redistribuir carga y resolver primero los mantenimientos con mayor atraso.",
            url="/dashboard/inteligencia/operativa/",
            modulo="Inteligencia Operativa",
            dato=f"{o['atrasados']} atraso(s)",
        ))
    elif o["atrasados"]:
        decisiones.append(_decision(
            clave="atrasos_operativos",
            nivel="atencion",
            prioridad=79,
            titulo="Mantenimientos atrasados",
            motivo=f"Existen {o['atrasados']} mantenimiento(s) pendientes con fecha vencida.",
            impacto=D0,
            impacto_tipo="impacto económico no cuantificado",
            accion="Reprogramar o cerrar los servicios pendientes antes de que se acumulen.",
            url="/dashboard/inteligencia/operativa/",
            modulo="Inteligencia Operativa",
            dato=f"{o['atrasados']} atraso(s)",
        ))

    # Inventario y consumo.
    if i["agotados"] or i["criticos"]:
        decisiones.append(_decision(
            clave="stock_critico",
            nivel="critica",
            prioridad=93,
            titulo="Stock crítico para la operación",
            motivo=f"{i['agotados']} producto(s) agotado(s) y {i['criticos']} por debajo del mínimo.",
            impacto=D0,
            impacto_tipo="riesgo operativo no cuantificado",
            accion="Reponer primero productos agotados y críticos según consumo y autonomía estimada.",
            url="/dashboard/inteligencia/inventario/",
            modulo="Inteligencia de Inventario",
            dato=f"{i['agotados'] + i['criticos']} producto(s)",
        ))
    if i["anomalos"]:
        decisiones.append(_decision(
            clave="consumo_anormal",
            nivel="atencion",
            prioridad=74,
            titulo="Consumo químico fuera del patrón",
            motivo=f"{i['anomalos']} contrato(s) consumen significativamente más que su promedio reciente.",
            impacto=D0,
            impacto_tipo="sobrecosto potencial no cuantificado",
            accion="Revisar estado del agua, dosificación, frecuencia y registro de consumo de esos contratos.",
            url="/dashboard/inteligencia/inventario/",
            modulo="Inteligencia de Inventario",
            dato=f"{i['anomalos']} contrato(s)",
        ))

    # 3. Incidencias críticas del ERP. No se inventa impacto económico.
    if h["criticas"]:
        decisiones.append(_decision(
            clave="salud_erp_critica",
            nivel="critica",
            prioridad=92,
            titulo="Incidencias críticas en el ERP",
            motivo=f"El Centro de Salud detecta {h['criticas']} tipo(s) de incidencia crítica.",
            impacto=D0,
            impacto_tipo="impacto económico no cuantificado",
            accion="Resolver primero las incidencias que puedan afectar servicio, cobro, programación o pagos.",
            url="/dashboard/salud-erp/",
            modulo="Salud del ERP",
            dato=f"{h['criticas']} incidencia(s)",
        ))

    # 4. Contracción comercial: usamos la mensualidad perdida registrada.
    if c["crecimiento_neto"] < 0:
        decisiones.append(_decision(
            clave="contraccion_comercial",
            nivel="critica",
            prioridad=90,
            titulo="Crecimiento neto negativo",
            motivo=(
                f"El balance del mes es {c['crecimiento_neto']:+d}: "
                f"{c['altas']} alta(s), {c['recuperados']} recuperado(s) y {c['bajas']} baja(s)."
            ),
            impacto=c["ingreso_perdido"],
            impacto_tipo="mensualidad perdida registrada",
            accion="Revisar motivos de baja y priorizar recuperación de clientes con mayor mensualidad.",
            url="/dashboard/inteligencia/crecimiento/",
            modulo="Crecimiento",
            dato=f"{c['crecimiento_neto']:+d} contratos",
        ))

    # 5. Contratos críticos, aunque todavía no estén en pérdida.
    contratos_criticos = [x for x in r["filas"] if x["estado"] == "critico"]
    if contratos_criticos:
        margen_actual = sum((_money(x["margen"]) for x in contratos_criticos), D0)
        ingreso = sum((_money(x["ingreso"]) for x in contratos_criticos), D0)
        objetivo_15 = _money(ingreso * Decimal("0.15"))
        brecha = max(D0, _money(objetivo_15 - margen_actual))
        decisiones.append(_decision(
            clave="margen_critico",
            nivel="atencion",
            prioridad=82,
            titulo="Contratos con margen crítico",
            motivo=f"{len(contratos_criticos)} contrato(s) están entre 0% y 14.9% de margen.",
            impacto=brecha,
            impacto_tipo="brecha mensual para llegar a 15% de margen",
            accion="Evaluar ajuste de precio, frecuencia, consumo químico o asignación técnica.",
            url="/dashboard/inteligencia/rentabilidad/",
            modulo="Rentabilidad",
            dato=f"{len(contratos_criticos)} contrato(s)",
        ))

    # 6. Retención.
    if c["retencion"] < 95:
        decisiones.append(_decision(
            clave="retencion_baja",
            nivel="atencion",
            prioridad=76,
            titulo="Retención por debajo de la referencia",
            motivo=f"La retención estimada del mes está en {c['retencion']}%.",
            impacto=c["ingreso_perdido"],
            impacto_tipo="mensualidad asociada a bajas del mes",
            accion="Contactar clientes perdidos, revisar causas recurrentes y activar recuperación.",
            url="/dashboard/inteligencia/crecimiento/",
            modulo="Retención",
            dato=f"{c['retencion']}%",
        ))

    # 7. Nómina pendiente: obligación, no pérdida.
    if s["nomina_pendiente"] > 0:
        decisiones.append(_decision(
            clave="nomina_pendiente",
            nivel="atencion",
            prioridad=58,
            titulo="Nómina pendiente del mes",
            motivo="Existen obligaciones de trabajadores todavía no cubiertas en el período.",
            impacto=s["nomina_pendiente"],
            impacto_tipo="obligación pendiente",
            accion="Revisar vencimientos y disponibilidad antes del cierre mensual.",
            url="/dashboard/finanzas/nomina/",
            modulo="Nómina",
            dato=f"${s['nomina_pendiente']:,.2f}",
        ))

    # 8. Avisos preventivos del Centro de Salud.
    salud_atencion = h["atencion"] + h["avisos"]
    if salud_atencion:
        decisiones.append(_decision(
            clave="salud_erp_preventiva",
            nivel="preventiva",
            prioridad=45,
            titulo="Puntos preventivos del ERP",
            motivo=f"Hay {h['atencion']} punto(s) de atención y {h['avisos']} aviso(s) preventivo(s).",
            impacto=D0,
            impacto_tipo="sin cuantificación económica",
            accion="Corregirlos después de resolver las prioridades críticas.",
            url="/dashboard/salud-erp/",
            modulo="Salud del ERP",
            dato=f"{salud_atencion} punto(s)",
        ))

    orden_nivel = {"critica": 0, "atencion": 1, "preventiva": 2}
    decisiones.sort(key=lambda x: (-x["prioridad"], orden_nivel.get(x["nivel"], 9), x["titulo"]))

    # Evitar sumar obligaciones/cartera con pérdidas como si fueran la misma cosa.
    impacto_riesgo = sum(
        (x["impacto"] for x in decisiones if x["clave"] in {
            "contratos_en_perdida", "contraccion_comercial", "margen_critico"
        }),
        D0,
    )
    capital_gestionar = sum(
        (x["impacto"] for x in decisiones if x["clave"] in {"cartera_vencida", "nomina_pendiente"}),
        D0,
    )

    criticas = sum(1 for x in decisiones if x["nivel"] == "critica")
    atencion = sum(1 for x in decisiones if x["nivel"] == "atencion")
    preventivas = sum(1 for x in decisiones if x["nivel"] == "preventiva")

    if criticas:
        estado = "critico"
        mensaje = "Hay decisiones que requieren atención prioritaria hoy."
    elif atencion:
        estado = "atencion"
        mensaje = "La operación está estable, pero existen puntos que conviene corregir."
    elif preventivas:
        estado = "preventivo"
        mensaje = "No hay alertas críticas; quedan acciones preventivas."
    else:
        estado = "saludable"
        mensaje = "No se detectan prioridades ejecutivas críticas con los datos actuales."

    return {
        "fecha": hoy,
        "ciudad": ciudad,
        "estado": estado,
        "mensaje": mensaje,
        "decisiones": decisiones,
        "top": decisiones[:5],
        "criticas": criticas,
        "atencion": atencion,
        "preventivas": preventivas,
        "total": len(decisiones),
        "impacto_riesgo": _money(impacto_riesgo),
        "capital_gestionar": _money(capital_gestionar),
        "snapshot": s,
    }
