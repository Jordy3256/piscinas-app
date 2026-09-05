"""Reglas centrales de sincronización entre contratos, cartera y nómina."""
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction

from .models import Factura, ObligacionTrabajador
from .cuentas_por_cobrar import fecha_vencimiento_contrato, valores_promocion


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


def _fecha_nomina_segun_configuracion(contrato, anio, mes):
    """Misma regla de fecha usada por Nómina, sin depender de una vista."""
    trabajador = contrato.tecnico_designado
    periodo_inicio, periodo_fin = contrato.periodo_servicio(anio, mes)

    if trabajador and trabajador.programacion_pago_nomina == "fin_periodo":
        return periodo_fin + timedelta(days=trabajador.dias_despues_fin_periodo or 0)
    if trabajador and trabajador.programacion_pago_nomina == "dia_fijo" and trabajador.dia_pago_nomina:
        return date(anio, mes, min(trabajador.dia_pago_nomina, monthrange(anio, mes)[1]))
    if trabajador and trabajador.programacion_pago_nomina == "rango" and trabajador.dia_pago_hasta:
        return date(anio, mes, min(trabajador.dia_pago_hasta, monthrange(anio, mes)[1]))

    facturas = (
        Factura.objects
        .filter(contrato=contrato, periodo_anio=anio, periodo_mes=mes)
        .exclude(estado=Factura.ESTADO_ANULADA)
        .values_list("fecha_vencimiento", flat=True)
    )
    fechas = [f for f in facturas if f]
    if fechas:
        return max(fechas)

    calendario = contrato.calendario_cobros(anio, mes)
    fechas = [item.get("fecha_vencimiento") for item in calendario if item.get("fecha_vencimiento")]
    return max(fechas) if fechas else date(anio, mes, 1) + timedelta(days=5)


@transaction.atomic
def sincronizar_contrato_activo(contrato):
    """Actualiza únicamente documentos sin pagos, preservando historia ya cobrada/pagada."""
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
            factura.observaciones = _agregar_nota(
                factura.observaciones,
                "Anulada porque la programación del contrato ya no contempla esta cuota.",
            )
            factura.save(update_fields=["estado", "observaciones", "actualizada_en"])
            continue

        # Respeta promociones/descuentos. La lógica anterior podía devolver una
        # cuenta promocionada al valor contractual al editar el contrato.
        promo = valores_promocion(contrato, factura.periodo_anio, factura.periodo_mes)
        precio_mensual = Decimal(contrato.precio_mensual or 0)
        proporcion = (Decimal(cuota["valor"]) / precio_mensual) if precio_mensual > 0 else Decimal("0")
        valor_neto = (Decimal(promo["total"]) * proporcion).quantize(Decimal("0.01"))
        descuento = max(Decimal(cuota["valor"]) - valor_neto, Decimal("0.00"))

        valores = {
            "cliente": contrato.cliente,
            "fecha_cobro_desde": cuota["fecha_cobro_desde"],
            "fecha_vencimiento": cuota["fecha_vencimiento"],
            "periodo_inicio": cuota["periodo_inicio"],
            "periodo_fin": cuota["periodo_fin"],
            "total_cuotas": cuota["total_cuotas"],
            "fecha_facturacion_programada": contrato.fecha_programada_facturacion(factura.periodo_anio, factura.periodo_mes),
            "requiere_factura": contrato.requiere_factura,
            "subtotal": valor_neto,
            "total": valor_neto,
            "valor_contractual": cuota["valor"],
            "descuento_promocion": descuento,
            "promocion": promo["promocion"],
            "promocion_nombre": promo["promocion"].nombre if promo["promocion"] else "",
        }
        cambios = []
        for campo, valor in valores.items():
            actual_id = getattr(factura, f"{campo}_id", None) if campo in {"cliente", "promocion"} else None
            valor_id = getattr(valor, "pk", None) if campo in {"cliente", "promocion"} else None
            distinto = actual_id != valor_id if campo in {"cliente", "promocion"} else getattr(factura, campo) != valor
            if distinto:
                setattr(factura, campo, valor)
                cambios.append(campo)

        estado_objetivo = (
            Factura.ESTADO_PROMOCION
            if valor_neto == 0 and promo["promocion"]
            else Factura.ESTADO_PENDIENTE
        )
        if factura.estado != estado_objetivo:
            factura.estado = estado_objetivo
            cambios.append("estado")

        if cambios:
            factura.save(update_fields=list(dict.fromkeys(cambios)) + ["actualizada_en"])
            factura.items.update(precio_unitario=valor_neto, subtotal=valor_neto)
            factura.sincronizar_estado()
            resultado["facturas_actualizadas"] += 1

    for obligacion in ObligacionTrabajador.objects.filter(contrato=contrato).prefetch_related("pagos"):
        if obligacion.estado == ObligacionTrabajador.ESTADO_ANULADO or obligacion.pagos.filter(activo=True).exists():
            continue

        nueva_fecha = _fecha_nomina_segun_configuracion(
            contrato, obligacion.periodo_anio, obligacion.periodo_mes
        )
        cambios = []
        if obligacion.fecha_pago_programada != nueva_fecha:
            obligacion.fecha_pago_programada = nueva_fecha
            cambios.append("fecha_pago_programada")
        if contrato.tecnico_designado_id and obligacion.trabajador_id != contrato.tecnico_designado_id:
            obligacion.trabajador = contrato.tecnico_designado
            cambios.append("trabajador")
        if contrato.valor_tecnico_mensual > 0 and obligacion.valor_acordado != contrato.valor_tecnico_mensual:
            obligacion.valor_acordado = contrato.valor_tecnico_mensual
            cambios.append("valor_acordado")

        if cambios:
            obligacion.save(update_fields=list(dict.fromkeys(cambios)) + ["actualizada_en"])
            obligacion.sincronizar_estado()
            resultado["obligaciones_actualizadas"] += 1

    return resultado

