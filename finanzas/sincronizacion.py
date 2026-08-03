"""Reglas centrales de sincronización entre contratos, cartera y nómina."""
from django.db import transaction

from .models import Factura, ObligacionTrabajador
from .cuentas_por_cobrar import fecha_vencimiento_contrato


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


@transaction.atomic
def sincronizar_contrato_activo(contrato):
    """Actualiza documentos pendientes y sin pagos con el calendario vigente."""
    if not contrato.activo:
        return sincronizar_contrato_desactivado(contrato)
    resultado = {"facturas_actualizadas": 0, "obligaciones_actualizadas": 0}
    for factura in Factura.objects.filter(contrato=contrato).prefetch_related("pagos"):
        if factura.estado == Factura.ESTADO_ANULADA or factura.pagos.filter(activo=True).exists():
            continue
        cuotas = contrato.calendario_cobros(factura.periodo_anio, factura.periodo_mes)
        cuota = next((item for item in cuotas if item["cuota_numero"] == factura.cuota_numero), None)
        if not cuota:
            factura.estado = Factura.ESTADO_ANULADA
            factura.observaciones = _agregar_nota(factura.observaciones, "Anulada porque la programación del contrato ya no contempla esta cuota.")
            factura.save(update_fields=["estado", "observaciones", "actualizada_en"])
            continue
        cambios = []
        valores = {
            "fecha_cobro_desde": cuota["fecha_cobro_desde"],
            "fecha_vencimiento": cuota["fecha_vencimiento"],
            "periodo_inicio": cuota["periodo_inicio"],
            "periodo_fin": cuota["periodo_fin"],
            "total_cuotas": cuota["total_cuotas"],
            "fecha_facturacion_programada": contrato.fecha_programada_facturacion(factura.periodo_anio, factura.periodo_mes),
            "requiere_factura": contrato.requiere_factura,
        }
        for campo, valor in valores.items():
            if getattr(factura, campo) != valor:
                setattr(factura, campo, valor); cambios.append(campo)
        if factura.cliente_id != contrato.cliente_id:
            factura.cliente = contrato.cliente; cambios.append("cliente")
        if factura.total != cuota["valor"]:
            factura.subtotal = cuota["valor"]; factura.total = cuota["valor"]
            cambios.extend(["subtotal", "total"])
            factura.items.update(precio_unitario=cuota["valor"], subtotal=cuota["valor"])
        if cambios:
            cambios.append("actualizada_en")
            factura.save(update_fields=list(dict.fromkeys(cambios)))
            factura.sincronizar_estado()
            resultado["facturas_actualizadas"] += 1
    for obligacion in ObligacionTrabajador.objects.filter(contrato=contrato).prefetch_related("pagos"):
        if obligacion.estado == ObligacionTrabajador.ESTADO_ANULADO or obligacion.pagos.filter(activo=True).exists():
            continue
        cuotas = contrato.calendario_cobros(obligacion.periodo_anio, obligacion.periodo_mes)
        nueva_fecha = max(item["fecha_vencimiento"] for item in cuotas)
        cambios=[]
        if obligacion.fecha_pago_programada != nueva_fecha:
            obligacion.fecha_pago_programada=nueva_fecha; cambios.append("fecha_pago_programada")
        if contrato.tecnico_designado_id and obligacion.trabajador_id != contrato.tecnico_designado_id:
            obligacion.trabajador=contrato.tecnico_designado; cambios.append("trabajador")
        if contrato.valor_tecnico_mensual > 0 and obligacion.valor_acordado != contrato.valor_tecnico_mensual:
            obligacion.valor_acordado=contrato.valor_tecnico_mensual; cambios.append("valor_acordado")
        if cambios:
            cambios.append("actualizada_en"); obligacion.save(update_fields=cambios); resultado["obligaciones_actualizadas"] += 1
    return resultado
