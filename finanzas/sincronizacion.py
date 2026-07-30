"""Reglas centrales de sincronización entre contratos, cartera y nómina."""
from django.db import transaction

from .models import Factura, ObligacionTrabajador


@transaction.atomic
def sincronizar_contrato_desactivado(contrato):
    """
    Retira de la operación financiera las cuentas generadas por un contrato inactivo.

    - Sin ningún pago histórico: elimina la factura/obligación.
    - Con uno o más pagos (activos o anulados): conserva el historial y marca anulada.
    """
    resultado = {
        "facturas_eliminadas": 0,
        "facturas_anuladas": 0,
        "obligaciones_eliminadas": 0,
        "obligaciones_anuladas": 0,
    }

    for factura in Factura.objects.filter(contrato=contrato).prefetch_related("pagos"):
        if factura.pagos.exists() or factura.ingreso_generado_id:
            if factura.estado != Factura.ESTADO_ANULADA:
                factura.estado = Factura.ESTADO_ANULADA
                factura.observaciones = _agregar_nota(
                    factura.observaciones,
                    "Anulada automáticamente porque el contrato fue desactivado.",
                )
                factura.save(update_fields=["estado", "observaciones", "actualizada_en"])
                resultado["facturas_anuladas"] += 1
        else:
            factura.delete()
            resultado["facturas_eliminadas"] += 1

    for obligacion in ObligacionTrabajador.objects.filter(contrato=contrato).prefetch_related("pagos"):
        if obligacion.pagos.exists():
            if obligacion.estado != ObligacionTrabajador.ESTADO_ANULADO:
                obligacion.estado = ObligacionTrabajador.ESTADO_ANULADO
                obligacion.observaciones = _agregar_nota(
                    obligacion.observaciones,
                    "Anulada automáticamente porque el contrato fue desactivado.",
                )
                obligacion.save(update_fields=["estado", "observaciones", "actualizada_en"])
                resultado["obligaciones_anuladas"] += 1
        else:
            obligacion.delete()
            resultado["obligaciones_eliminadas"] += 1

    return resultado


def _agregar_nota(texto, nota):
    texto = (texto or "").strip()
    if nota in texto:
        return texto
    return f"{texto}\n{nota}".strip()
