"""Reglas centrales de sincronización entre contratos, cartera y nómina."""
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import Factura, ObligacionTrabajador
from .cuentas_por_cobrar import generar_factura_contrato, valores_promocion


@transaction.atomic
def sincronizar_contrato_desactivado(contrato):
    """
    Sincroniza Cartera y Nómina cuando un contrato se desactiva.

    Regla contable:
    - Lo ya pagado/cobrado se conserva siempre como historia.
    - Lo correspondiente a periodos ya cerrados antes de la baja se conserva.
    - Lo pendiente del periodo que todavía no cerró y todo lo futuro se elimina.
      Así desaparecen automáticamente Cartera y Nómina que ya no corresponden.
    """
    fecha_baja = contrato.fecha_baja or timezone.localdate()

    resultado = {
        "facturas_eliminadas": 0,
        "facturas_conservadas": 0,
        "obligaciones_eliminadas": 0,
        "obligaciones_conservadas": 0,
    }

    for factura in Factura.objects.filter(contrato=contrato).prefetch_related("pagos"):
        tiene_pago = factura.pagos.filter(activo=True).exists() or bool(factura.ingreso_generado_id)
        periodo_fin = factura.periodo_fin

        if tiene_pago or (periodo_fin and periodo_fin <= fecha_baja):
            resultado["facturas_conservadas"] += 1
            continue

        factura.delete()
        resultado["facturas_eliminadas"] += 1

    for obligacion in ObligacionTrabajador.objects.filter(contrato=contrato).prefetch_related("pagos"):
        tiene_pago = obligacion.pagos.filter(activo=True).exists()
        periodo_fin = obligacion.periodo_servicio_fin

        # Compatibilidad con obligaciones antiguas que no tenían fechas de servicio.
        if not periodo_fin:
            _, periodo_fin = contrato.periodo_servicio(
                obligacion.periodo_anio,
                obligacion.periodo_mes,
            )

        if tiene_pago or (periodo_fin and periodo_fin <= fecha_baja):
            resultado["obligaciones_conservadas"] += 1
            continue

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

    if (
        contrato.programacion_cobro == "semestral_adelantado"
        and trabajador
        and trabajador.programacion_pago_nomina == "fecha_contratos"
    ):
        return periodo_fin

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


def _mover_mes(anio, mes, desplazamiento):
    indice = (int(anio) * 12 + (int(mes) - 1)) + int(desplazamiento)
    return indice // 12, indice % 12 + 1


def _periodos_a_materializar(contrato, desde_fecha=None, horizonte_meses=12):
    """
    Devuelve claves (año, mes) de periodos de servicio a mantener creados.

    Un contrato recién creado puede comenzar en el pasado o futuro; en ese caso
    `desde_fecha` permite comenzar exactamente desde su fecha de inicio.
    """
    hoy = timezone.localdate()
    desde_fecha = desde_fecha or hoy

    if contrato.fecha_inicio and contrato.fecha_inicio > desde_fecha:
        desde_fecha = contrato.fecha_inicio

    inicio_anio, inicio_mes = desde_fecha.year, desde_fecha.month

    for offset in range(0, max(int(horizonte_meses), 0) + 1):
        anio, mes = _mover_mes(inicio_anio, inicio_mes, offset)
        periodo_inicio, periodo_fin = contrato.periodo_servicio(anio, mes)

        # Un periodo que terminó antes (o el mismo día) de iniciar el contrato
        # nunca puede producir Cartera ni Nómina.
        if contrato.fecha_inicio and periodo_fin <= contrato.fecha_inicio:
            continue

        yield anio, mes, periodo_inicio, periodo_fin


def _materializar_nomina_periodo(contrato, anio, mes, periodo_inicio, periodo_fin):
    """
    Crea/actualiza la obligación mensual del técnico.

    La forma de pago del cliente no altera esta periodicidad: incluso contratos
    semestrales/anuales mantienen Nómina mensual.
    """
    if (
        not contrato.tecnico_designado_id
        or not contrato.valor_tecnico_mensual
        or contrato.valor_tecnico_mensual <= 0
    ):
        return None, False

    fecha_programada = _fecha_nomina_segun_configuracion(contrato, anio, mes)

    obligacion, creada = ObligacionTrabajador.objects.get_or_create(
        contrato=contrato,
        periodo_anio=anio,
        periodo_mes=mes,
        defaults={
            "trabajador": contrato.tecnico_designado,
            "valor_acordado": contrato.valor_tecnico_mensual,
            "periodo_servicio_inicio": periodo_inicio,
            "periodo_servicio_fin": periodo_fin,
            "fecha_pago_programada": fecha_programada,
        },
    )

    if creada or obligacion.pagos.filter(activo=True).exists():
        return obligacion, creada

    cambios = []
    valores = {
        "trabajador": contrato.tecnico_designado,
        "valor_acordado": contrato.valor_tecnico_mensual,
        "periodo_servicio_inicio": periodo_inicio,
        "periodo_servicio_fin": periodo_fin,
        "fecha_pago_programada": fecha_programada,
    }
    for campo, valor in valores.items():
        if campo == "trabajador":
            distinto = obligacion.trabajador_id != getattr(valor, "pk", None)
        else:
            distinto = getattr(obligacion, campo) != valor
        if distinto:
            setattr(obligacion, campo, valor)
            cambios.append(campo)

    if obligacion.estado == ObligacionTrabajador.ESTADO_ANULADO:
        obligacion.estado = ObligacionTrabajador.ESTADO_PENDIENTE
        cambios.append("estado")

    if cambios:
        obligacion.save(update_fields=list(dict.fromkeys(cambios)) + ["actualizada_en"])
        obligacion.sincronizar_estado()

    return obligacion, False


def materializar_finanzas_contrato(
    contrato,
    *,
    desde_fecha=None,
    horizonte_meses=12,
):
    """
    Mantiene automáticamente Cartera y Nómina del contrato.

    Se ejecuta desde la señal post_save de Contrato, por lo que:
    - crear un contrato crea inmediatamente sus cuentas y nómina;
    - editarlo actualiza los documentos futuros no pagados;
    - no hace falta pulsar "Generar cuentas" ni "Generar nómina".
    """
    if not contrato.activo:
        return sincronizar_contrato_desactivado(contrato)

    resultado = {
        "facturas_creadas": 0,
        "obligaciones_creadas": 0,
    }

    for anio, mes, periodo_inicio, periodo_fin in _periodos_a_materializar(
        contrato,
        desde_fecha=desde_fecha,
        horizonte_meses=horizonte_meses,
    ):
        # Cartera respeta la programación comercial. En meses sin cobro (por
        # ejemplo, un contrato semestral), generar_factura_contrato no crea nada.
        facturas, creadas = generar_factura_contrato(contrato, anio, mes)
        resultado["facturas_creadas"] += creadas

        _, creada_nomina = _materializar_nomina_periodo(
            contrato,
            anio,
            mes,
            periodo_inicio,
            periodo_fin,
        )
        resultado["obligaciones_creadas"] += int(creada_nomina)

    return resultado


@transaction.atomic
def sincronizar_contrato_activo(contrato, *, desde_fecha=None, horizonte_meses=12):
    """Actualiza lo existente y crea automáticamente Cartera/Nómina faltante."""
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
        desglose = contrato.desglose_valor(valor_neto)
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
            "subtotal": desglose["base"],
            "impuesto": desglose["impuesto"],
            "total": desglose["total"],
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
            factura.items.update(precio_unitario=desglose["base"], subtotal=desglose["base"])
            factura.sincronizar_estado()
            resultado["facturas_actualizadas"] += 1

    hoy = timezone.localdate()

    for obligacion in ObligacionTrabajador.objects.filter(contrato=contrato).prefetch_related("pagos"):
        if obligacion.pagos.filter(activo=True).exists():
            continue

        # Si se retiró técnico/valor, las obligaciones que todavía no han cerrado
        # ya no corresponden y se eliminan automáticamente.
        if (
            not contrato.tecnico_designado_id
            or not contrato.valor_tecnico_mensual
            or contrato.valor_tecnico_mensual <= 0
        ):
            periodo_fin = obligacion.periodo_servicio_fin
            if not periodo_fin:
                _, periodo_fin = contrato.periodo_servicio(
                    obligacion.periodo_anio,
                    obligacion.periodo_mes,
                )
            if periodo_fin > hoy:
                obligacion.delete()
            continue

        if obligacion.estado == ObligacionTrabajador.ESTADO_ANULADO:
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

    materializados = materializar_finanzas_contrato(
        contrato,
        desde_fecha=desde_fecha,
        horizonte_meses=horizonte_meses,
    )
    resultado.update(materializados)
    return resultado

