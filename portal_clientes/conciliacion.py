"""Resumen financiero de solo lectura para el portal de clientes.

No modifica facturas ni pagos. El vencido considera TODAS las obligaciones
exigibles vencidas, aunque se muestre solo una factura por contrato.
"""
from decimal import Decimal


def resumir_facturas(filas, hoy):
    proximas_por_contrato = {}
    historial = []
    vencido = Decimal('0.00')
    pagado = Decimal('0.00')
    for fila in filas:
        factura = fila['factura']
        if factura.estado == factura.ESTADO_ANULADA:
            continue
        restante = fila['saldo']
        pagado += fila['pagado']
        # La fecha real de cobro impide contabilizar cuotas programadas a futuro.
        exigible = factura.fecha_real_cobro <= hoy
        if restante > 0 and exigible and factura.fecha_vencimiento < hoy:
            vencido += restante
        if restante > 0:
            clave = (factura.fecha_real_cobro, factura.fecha_vencimiento, factura.pk)
            anterior = proximas_por_contrato.get(factura.contrato_id)
            if anterior is None or clave < anterior[0]:
                proximas_por_contrato[factura.contrato_id] = (clave, fila)
        if fila['pagos'] or factura.estado in (factura.ESTADO_PAGADA, factura.ESTADO_PROMOCION):
            historial.append(fila)
    proximas = [item[1] for item in proximas_por_contrato.values()]
    proximas.sort(key=lambda fila: (fila['factura'].fecha_real_cobro, fila['factura'].fecha_vencimiento, fila['factura'].pk))
    historial.sort(key=lambda fila: (fila['factura'].pagada_en or fila['factura'].fecha_vencimiento, fila['factura'].pk), reverse=True)
    saldo = sum((fila['saldo'] for fila in proximas), Decimal('0.00'))
    return proximas, historial, saldo, vencido, pagado
