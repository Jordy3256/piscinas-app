"""Auditoría y autocorrección liviana de Cartera y Nómina.

No crea ni elimina obligaciones financieras. Solo vuelve a calcular estados a
partir de pagos activos y corrige vínculos contables derivados cuando es seguro.
"""
from decimal import Decimal

from django.db import transaction

from .models import (
    Egreso,
    Factura,
    Ingreso,
    LotePagoTrabajador,
    ObligacionTrabajador,
    PagoFactura,
    PagoTrabajador,
)


@transaction.atomic
def reconciliar_cartera_nomina():
    resultado = {
        "facturas_estado": 0,
        "obligaciones_estado": 0,
        "ingresos_pago": 0,
        "egresos_pago": 0,
        "egresos_lote": 0,
    }

    # CARTERA: el estado siempre debe derivarse de pagos activos.
    for factura in Factura.objects.prefetch_related("pagos").exclude(
        estado=Factura.ESTADO_ANULADA
    ):
        anterior = factura.estado
        factura.sincronizar_estado()
        if factura.estado != anterior:
            resultado["facturas_estado"] += 1

    # Pagos de clientes: un pago activo debe tener su ingreso real activo y por
    # el mismo monto; un pago anulado no debe seguir sumando como ingreso.
    for pago in PagoFactura.objects.select_related("factura", "ingreso").all():
        if pago.activo:
            if pago.ingreso_id:
                ingreso = pago.ingreso
                cambios = []
                valores = {
                    "cliente": pago.factura.cliente,
                    "contrato": pago.factura.contrato,
                    "total": pago.monto,
                    "monto_pagado": pago.monto,
                    "estado": Ingreso.ESTADO_PAGADO,
                    "fecha": pago.fecha,
                    "fecha_cobro": pago.fecha,
                    "metodo_pago": pago.metodo_pago,
                }
                for campo, valor in valores.items():
                    actual = getattr(ingreso, campo)
                    actual_id = getattr(ingreso, f"{campo}_id", None) if campo in {"cliente", "contrato"} else None
                    valor_id = getattr(valor, "pk", None) if campo in {"cliente", "contrato"} else None
                    distinto = actual_id != valor_id if campo in {"cliente", "contrato"} else actual != valor
                    if distinto:
                        setattr(ingreso, campo, valor)
                        cambios.append(campo)
                if cambios:
                    ingreso.save(update_fields=list(dict.fromkeys(cambios)) + ["actualizado_en"])
                    resultado["ingresos_pago"] += 1
        elif pago.ingreso_id and pago.ingreso.estado != Ingreso.ESTADO_ANULADO:
            pago.ingreso.estado = Ingreso.ESTADO_ANULADO
            pago.ingreso.monto_pagado = Decimal("0.00")
            pago.ingreso.save(update_fields=["estado", "monto_pagado", "actualizado_en"])
            resultado["ingresos_pago"] += 1

    # NÓMINA: no confiar en un estado guardado antiguo; el saldo sale de pagos
    # activos. Así, un trabajador totalmente pagado deja de aparecer pendiente.
    for obligacion in ObligacionTrabajador.objects.prefetch_related("pagos").exclude(
        estado=ObligacionTrabajador.ESTADO_ANULADO
    ):
        anterior = obligacion.estado
        obligacion.sincronizar_estado()
        if obligacion.estado != anterior:
            resultado["obligaciones_estado"] += 1

    # Pagos individuales: mantener su egreso derivado sincronizado.
    for pago in PagoTrabajador.objects.select_related(
        "obligacion__trabajador", "obligacion__contrato__cliente", "egreso"
    ).filter(lote__isnull=True):
        if pago.activo and pago.egreso_id:
            egreso = pago.egreso
            cambios = []
            valores = {
                "costo_unitario": pago.monto,
                "total": pago.monto,
                "monto_pagado": pago.monto,
                "estado": Egreso.ESTADO_PAGADO,
                "fecha": pago.fecha,
                "metodo_pago": pago.metodo_pago,
                "proveedor": str(pago.obligacion.trabajador),
            }
            for campo, valor in valores.items():
                if getattr(egreso, campo) != valor:
                    setattr(egreso, campo, valor)
                    cambios.append(campo)
            if cambios:
                egreso.save(update_fields=list(dict.fromkeys(cambios)) + ["actualizado_en"])
                resultado["egresos_pago"] += 1
        elif not pago.activo and pago.egreso_id and pago.egreso.estado != Egreso.ESTADO_ANULADO:
            pago.egreso.estado = Egreso.ESTADO_ANULADO
            pago.egreso.monto_pagado = Decimal("0.00")
            pago.egreso.save(update_fields=["estado", "monto_pagado", "actualizado_en"])
            resultado["egresos_pago"] += 1

    # Pagos consolidados: el egreso debe reflejar únicamente lotes activos.
    for lote in LotePagoTrabajador.objects.select_related("egreso", "trabajador").all():
        if lote.activo and lote.egreso_id:
            egreso = lote.egreso
            cambios = []
            valores = {
                "costo_unitario": lote.monto,
                "total": lote.monto,
                "monto_pagado": lote.monto,
                "estado": Egreso.ESTADO_PAGADO,
                "fecha": lote.fecha,
                "metodo_pago": lote.metodo_pago,
                "proveedor": str(lote.trabajador),
            }
            for campo, valor in valores.items():
                if getattr(egreso, campo) != valor:
                    setattr(egreso, campo, valor)
                    cambios.append(campo)
            if cambios:
                egreso.save(update_fields=list(dict.fromkeys(cambios)) + ["actualizado_en"])
                resultado["egresos_lote"] += 1
        elif not lote.activo and lote.egreso_id and lote.egreso.estado != Egreso.ESTADO_ANULADO:
            lote.egreso.estado = Egreso.ESTADO_ANULADO
            lote.egreso.monto_pagado = Decimal("0.00")
            lote.egreso.save(update_fields=["estado", "monto_pagado", "actualizado_en"])
            resultado["egresos_lote"] += 1

    return resultado
