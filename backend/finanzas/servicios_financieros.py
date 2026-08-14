from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone

from .models import (
    Egreso,
    Factura,
    Ingreso,
    MovimientoRecurrente,
    ObligacionTrabajador,
)

CERO = Decimal("0.00")


def _sumar(qs, campo: str) -> Decimal:
    return qs.aggregate(valor=Sum(campo))["valor"] or CERO


def _rango_mes(anio: int, mes: int) -> tuple[date, date]:
    return date(anio, mes, 1), date(anio, mes, monthrange(anio, mes)[1])


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


def obtener_resumen_financiero(anio: int, mes: int) -> dict:
    """Calcula el estado real y proyectado sin duplicar cartera ni nómina.

    Real:
      - Ingresos: movimientos de ingreso efectivamente cobrados en el mes.
      - Egresos: movimientos de egreso efectivamente pagados en el mes.

    Proyectado:
      - Ingresos: facturas del periodo + ingresos manuales del mes.
      - Egresos: obligaciones cuya fecha programada de pago cae en el mes + egresos no vinculados a nómina.
    """
    inicio, fin = _rango_mes(anio, mes)

    ingresos_reales_qs = Ingreso.objects.filter(fecha__range=(inicio, fin)).exclude(
        estado=Ingreso.ESTADO_ANULADO
    )
    egresos_reales_qs = Egreso.objects.filter(
        fecha__range=(inicio, fin), aprobado=True
    ).exclude(estado=Egreso.ESTADO_ANULADO)

    ingresos_cobrados = _sumar(ingresos_reales_qs, "monto_pagado")
    egresos_pagados = _sumar(egresos_reales_qs, "monto_pagado")

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

    total_facturado = _sumar(facturas, "total")
    total_ingresos_manuales = _sumar(ingresos_manuales, "total")
    ingresos_esperados = total_facturado + total_ingresos_manuales

    total_nomina = _sumar(obligaciones, "valor_acordado")
    total_egresos_no_nomina = _sumar(egresos_no_nomina, "total")

    # Los recurrentes que aún no fueron procesados también son previsiones del mes.
    recurrentes_pendientes = MovimientoRecurrente.objects.filter(
        activo=True,
        tipo="egreso",
        proxima_fecha__range=(inicio, fin),
    )
    total_recurrentes_pendientes = _sumar(recurrentes_pendientes, "monto")
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
