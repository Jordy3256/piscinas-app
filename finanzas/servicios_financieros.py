from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone

from contratos.models import Contrato

from .models import (
    Egreso,
    Factura,
    Ingreso,
    MovimientoRecurrente,
    ObligacionTrabajador,
    PagoTrabajador,
    PromocionContrato,
)

CERO = Decimal("0.00")


def _sumar(qs, campo: str) -> Decimal:
    return qs.aggregate(valor=Sum(campo))["valor"] or CERO


def _rango_mes(anio: int, mes: int) -> tuple[date, date]:
    return date(anio, mes, 1), date(anio, mes, monthrange(anio, mes)[1])


def _filtro_ciudad_contrato(ciudad: str) -> Q:
    return (Q(ciudad_ref__nombre__iexact=ciudad) | Q(ciudad_ref__isnull=True, ciudad__iexact=ciudad) | Q(ciudad_ref__isnull=True, cliente__ciudad_ref__nombre__iexact=ciudad) | Q(ciudad_ref__isnull=True, cliente__ciudad__iexact=ciudad))


def _contratos_del_periodo(anio: int, mes: int, ciudad: str):
    inicio, fin = _rango_mes(anio, mes)
    qs = Contrato.objects.select_related("cliente", "ciudad_ref").filter(fecha_inicio__lte=fin).filter(Q(activo=True) | Q(fecha_baja__gte=inicio))
    if ciudad:
        qs = qs.filter(_filtro_ciudad_contrato(ciudad))
    return qs.distinct()


def _ingresos_manuales(anio: int, mes: int):
    inicio, fin = _rango_mes(anio, mes)
    return (
        Ingreso.objects.filter(fecha__range=(inicio, fin))
        .exclude(estado=Ingreso.ESTADO_ANULADO)
        .filter(pago_factura__isnull=True, factura_origen__isnull=True)
    )


def _egresos_no_nomina(anio: int, mes: int):
    inicio, fin = _rango_mes(anio, mes)
    return (
        Egreso.objects.filter(fecha__range=(inicio, fin), aprobado=True)
        .exclude(estado=Egreso.ESTADO_ANULADO)
        .filter(pago_trabajador__isnull=True, lote_pago_trabajador__isnull=True)
    )


def obtener_resumen_financiero(anio: int, mes: int, ciudad: str = "") -> dict:
    """Calcula el estado real y proyectado sin duplicar cartera ni nómina.

    Real:
      - Ingresos: movimientos de ingreso efectivamente cobrados en el mes.
      - Egresos: movimientos de egreso efectivamente pagados en el mes.

    Proyectado:
      - Ingresos: facturas del periodo + ingresos manuales del mes.
      - Egresos: obligaciones cuya fecha programada de pago cae en el mes + egresos no vinculados a nómina.
    """
    inicio, fin = _rango_mes(anio, mes)
    ciudad = (ciudad or "").strip()

    ingresos_reales_qs = Ingreso.objects.filter(fecha__range=(inicio, fin)).exclude(
        estado=Ingreso.ESTADO_ANULADO
    )
    egresos_reales_qs = Egreso.objects.filter(
        fecha__range=(inicio, fin), aprobado=True
    ).exclude(estado=Egreso.ESTADO_ANULADO)

    pagos_consolidados_ciudad = CERO
    if ciudad:
        ingresos_reales_qs = ingresos_reales_qs.filter(
            Q(contrato__ciudad_ref__nombre__iexact=ciudad) | Q(contrato__ciudad__iexact=ciudad) | Q(cliente__ciudad_ref__nombre__iexact=ciudad) | Q(cliente__ciudad__iexact=ciudad) | Q(ciudad__iexact=ciudad)
        ).distinct()
        # Los pagos individuales ya guardan ciudad_proyecto. Los consolidados se
        # distribuyen por obligación para no atribuir todo el lote a una sola ciudad.
        egresos_reales_qs = egresos_reales_qs.exclude(
            lote_pago_trabajador__isnull=False
        ).filter(ciudad_proyecto__iexact=ciudad)
        pagos_consolidados_ciudad = (
            PagoTrabajador.objects.filter(
                activo=True,
                lote__isnull=False,
                lote__activo=True,
                fecha__range=(inicio, fin),
                obligacion__contrato__ciudad_ref__nombre__iexact=ciudad,
            ).aggregate(valor=Sum("monto"))["valor"] or CERO
        )

    ingresos_cobrados = _sumar(ingresos_reales_qs, "monto_pagado")
    egresos_pagados = _sumar(egresos_reales_qs, "monto_pagado") + pagos_consolidados_ciudad

    facturas = (
        Factura.objects.filter(periodo_anio=anio, periodo_mes=mes)
        .exclude(estado=Factura.ESTADO_ANULADA)
        .select_related("cliente", "contrato")
        .prefetch_related("pagos")
    )
    obligaciones = (
        ObligacionTrabajador.objects.filter(
            fecha_pago_programada__year=anio,
            fecha_pago_programada__month=mes,
        )
        .exclude(estado=ObligacionTrabajador.ESTADO_ANULADO)
        .select_related("trabajador", "contrato", "contrato__cliente")
        .prefetch_related("pagos")
    )
    ingresos_manuales = _ingresos_manuales(anio, mes)
    egresos_no_nomina = _egresos_no_nomina(anio, mes)

    if ciudad:
        facturas = facturas.filter(Q(contrato__ciudad_ref__nombre__iexact=ciudad) | Q(contrato__ciudad__iexact=ciudad) | Q(cliente__ciudad_ref__nombre__iexact=ciudad) | Q(cliente__ciudad__iexact=ciudad)).distinct()
        obligaciones = obligaciones.filter(Q(contrato__ciudad_ref__nombre__iexact=ciudad) | Q(contrato__ciudad__iexact=ciudad) | Q(contrato__cliente__ciudad_ref__nombre__iexact=ciudad) | Q(contrato__cliente__ciudad__iexact=ciudad)).distinct()
        ingresos_manuales = ingresos_manuales.filter(
            Q(contrato__ciudad_ref__nombre__iexact=ciudad) | Q(contrato__ciudad__iexact=ciudad) | Q(cliente__ciudad_ref__nombre__iexact=ciudad) | Q(cliente__ciudad__iexact=ciudad) | Q(ciudad__iexact=ciudad)
        ).distinct()
        egresos_no_nomina = egresos_no_nomina.filter(ciudad_proyecto__iexact=ciudad)

    total_facturado = _sumar(facturas, "total")
    total_ingresos_manuales = _sumar(ingresos_manuales, "total")
    total_nomina = _sumar(obligaciones, "valor_acordado")
    total_egresos_no_nomina = _sumar(egresos_no_nomina, "total")

    # Completa la proyección territorial desde contratos cuando todavía no se han
    # materializado la factura o la obligación del período. No duplica documentos existentes.
    if ciudad:
        contratos_periodo = _contratos_del_periodo(anio, mes, ciudad)
        ids_facturados = set(facturas.values_list("contrato_id", flat=True))
        ids_obligados = set(obligaciones.values_list("contrato_id", flat=True))
        promos = {}
        for promo in PromocionContrato.objects.filter(contrato__in=contratos_periodo, activa=True):
            if promo.aplica_a(anio, mes):
                promos[promo.contrato_id] = promo
        for contrato in contratos_periodo:
            if contrato.id not in ids_facturados:
                valor = Decimal(contrato.precio_mensual or 0)
                if contrato.id in promos:
                    valor = promos[contrato.id].calcular(valor)["total"]
                total_facturado += valor
            if contrato.id not in ids_obligados:
                total_nomina += Decimal(contrato.valor_tecnico_mensual or 0)

    ingresos_esperados = total_facturado + total_ingresos_manuales

    # Los recurrentes que aún no fueron procesados también son previsiones del mes.
    recurrentes_pendientes = MovimientoRecurrente.objects.filter(
        activo=True,
        tipo="egreso",
        proxima_fecha__range=(inicio, fin),
    )
    # Los recurrentes actuales no tienen ciudad asignada; por eso solo forman
    # parte de la vista Global y no contaminan una ciudad específica.
    total_recurrentes_pendientes = CERO if ciudad else _sumar(recurrentes_pendientes, "monto")
    egresos_previstos = total_nomina + total_egresos_no_nomina + total_recurrentes_pendientes

    cobrado_facturas = sum((factura.monto_pagado for factura in facturas), CERO)
    cobrado_manual = _sumar(ingresos_manuales, "monto_pagado")
    por_cobrar = max(ingresos_esperados - cobrado_facturas - cobrado_manual, CERO)

    pagado_nomina = sum((obligacion.monto_pagado for obligacion in obligaciones), CERO)
    pagado_no_nomina = _sumar(egresos_no_nomina, "monto_pagado")
    por_pagar = max(
        egresos_previstos - pagado_nomina - pagado_no_nomina,
        CERO,
    )

    utilidad_real = ingresos_cobrados - egresos_pagados
    resultado_proyectado = ingresos_esperados - egresos_previstos

    cumplimiento_cobranza = (
        min(Decimal("100.00"), (ingresos_cobrados / ingresos_esperados) * 100)
        if ingresos_esperados > 0
        else CERO
    )
    cumplimiento_pagos = (
        min(Decimal("100.00"), (egresos_pagados / egresos_previstos) * 100)
        if egresos_previstos > 0
        else CERO
    )
    margen_proyectado = (
        (resultado_proyectado / ingresos_esperados) * 100
        if ingresos_esperados > 0
        else CERO
    )

    hoy = timezone.localdate()
    cobros_vencidos = [f for f in facturas if f.saldo > 0 and f.fecha_vencimiento < hoy]
    cobros_hoy = [
        f
        for f in facturas
        if f.saldo > 0
        and (f.fecha_cobro_desde or f.fecha_vencimiento) <= hoy <= f.fecha_vencimiento
    ]
    facturas_por_emitir = [
        f
        for f in facturas
        if f.requiere_factura
        and not f.factura_enviada
        and f.fecha_facturacion_programada
        and f.fecha_facturacion_programada <= hoy
        and f.estado != Factura.ESTADO_ANULADA
    ]
    nomina_hoy = [
        o
        for o in obligaciones
        if o.saldo > 0 and o.fecha_pago_programada <= hoy
    ]

    return {
        "inicio": inicio,
        "fin": fin,
        "ingresos_cobrados": ingresos_cobrados,
        "egresos_pagados": egresos_pagados,
        "utilidad_real": utilidad_real,
        "ingresos_esperados": ingresos_esperados,
        "egresos_previstos": egresos_previstos,
        "resultado_proyectado": resultado_proyectado,
        "por_cobrar": por_cobrar,
        "por_pagar": por_pagar,
        "cumplimiento_cobranza": cumplimiento_cobranza,
        "cumplimiento_pagos": cumplimiento_pagos,
        "margen_proyectado": margen_proyectado,
        "total_facturado": total_facturado,
        "total_nomina": total_nomina,
        "cobros_vencidos": cobros_vencidos,
        "cobros_hoy": cobros_hoy,
        "facturas_por_emitir": facturas_por_emitir,
        "nomina_hoy": nomina_hoy,
        "total_cobros_vencidos": len(cobros_vencidos),
        "total_cobros_hoy": len(cobros_hoy),
        "total_facturas_por_emitir": len(facturas_por_emitir),
        "total_nomina_hoy": len(nomina_hoy),
    }
