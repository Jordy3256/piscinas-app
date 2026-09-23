from calendar import monthrange
from datetime import date, timedelta

from django.db import transaction
from django.utils import timezone

from contratos.models import Contrato
from .models import AvisoFacturacion


def _mover_mes(anio, mes, desplazamiento):
    indice = anio * 12 + (mes - 1) + desplazamiento
    return indice // 12, indice % 12 + 1


@transaction.atomic
def sincronizar_avisos_facturacion(*, hoy=None, meses_atras=4, meses_adelante=3):
    """
    Materializa recordatorios de facturación independientes de Cartera.

    En contratos "Por visita" crea un aviso por cada mantenimiento programado,
    usando la misma fecha de la visita. En el resto conserva un aviso por período.
    Las reprogramaciones actualizan los avisos pendientes y las visitas que dejan
    de existir anulan únicamente avisos todavía pendientes.
    """
    hoy = hoy or timezone.localdate()

    contratos = (
        Contrato.objects
        .filter(activo=True, requiere_factura=True)
        .select_related("cliente")
    )

    creados = actualizados = anulados = 0
    errores = []
    contratos_ids = set(contratos.values_list("id", flat=True))

    qs_anular = AvisoFacturacion.objects.filter(
        estado=AvisoFacturacion.ESTADO_PENDIENTE
    ).exclude(contrato_id__in=contratos_ids)
    anulados += qs_anular.update(estado=AvisoFacturacion.ESTADO_ANULADA)

    for contrato in contratos:
        try:
            for offset in range(-meses_atras, meses_adelante + 1):
                anio, mes = _mover_mes(hoy.year, hoy.month, offset)
                periodo_inicio, periodo_fin = contrato.periodo_servicio(anio, mes)

                if contrato.fecha_inicio and periodo_fin <= contrato.fecha_inicio:
                    continue
                if contrato.fecha_fin_contrato and periodo_inicio > contrato.fecha_fin_contrato:
                    continue

                por_visita = (
                    contrato.forma_pago == "por_visita"
                    or contrato.programacion_cobro == "por_visita"
                    or contrato.momento_facturacion == "por_visita"
                )

                eventos = []
                if por_visita:
                    # La facturación externa sigue el mismo hecho económico que
                    # Cartera: una visita programada no genera aviso hasta que
                    # realmente fue ejecutada.
                    from mantenimientos.models import Mantenimiento
                    for cuota in contrato.calendario_cobros(anio, mes):
                        mantenimiento_id = cuota.get("mantenimiento_id")
                        if not mantenimiento_id or not Mantenimiento.objects.filter(
                            pk=mantenimiento_id, estado="realizado"
                        ).exists():
                            continue
                        eventos.append({
                            "cuota_numero": int(cuota["cuota_numero"]),
                            "fecha_programada": cuota["fecha_cobro_desde"],
                            "periodo_inicio": cuota["periodo_inicio"],
                            "periodo_fin": cuota["periodo_fin"],
                        })
                else:
                    fecha_programada = contrato.fecha_programada_facturacion(anio, mes)
                    if fecha_programada:
                        eventos.append({
                            "cuota_numero": 1,
                            "fecha_programada": fecha_programada,
                            "periodo_inicio": periodo_inicio,
                            "periodo_fin": periodo_fin,
                        })

                esperadas = {evento["cuota_numero"] for evento in eventos}

                # Si una visita futura desapareció/reprogramó fuera de este ciclo,
                # el aviso pendiente que ya no corresponde se anula.
                pendientes_periodo = AvisoFacturacion.objects.filter(
                    contrato=contrato,
                    periodo_anio=anio,
                    periodo_mes=mes,
                    estado=AvisoFacturacion.ESTADO_PENDIENTE,
                )
                if esperadas:
                    anulados += pendientes_periodo.exclude(
                        cuota_numero__in=esperadas
                    ).update(estado=AvisoFacturacion.ESTADO_ANULADA)
                else:
                    anulados += pendientes_periodo.update(
                        estado=AvisoFacturacion.ESTADO_ANULADA
                    )

                for evento in eventos:
                    fecha_programada = evento["fecha_programada"]

                    # Conservamos la política histórica: no recrear recordatorios
                    # demasiado antiguos si ya no existían.
                    if fecha_programada < hoy - timedelta(days=31):
                        continue

                    aviso, creado = AvisoFacturacion.objects.get_or_create(
                        contrato=contrato,
                        periodo_anio=anio,
                        periodo_mes=mes,
                        cuota_numero=evento["cuota_numero"],
                        defaults={
                            "periodo_inicio": evento["periodo_inicio"],
                            "periodo_fin": evento["periodo_fin"],
                            "fecha_programada": fecha_programada,
                        },
                    )
                    if creado:
                        creados += 1
                        continue

                    if aviso.estado == AvisoFacturacion.ESTADO_PENDIENTE:
                        cambios = []
                        for campo, valor in {
                            "periodo_inicio": evento["periodo_inicio"],
                            "periodo_fin": evento["periodo_fin"],
                            "fecha_programada": fecha_programada,
                        }.items():
                            if getattr(aviso, campo) != valor:
                                setattr(aviso, campo, valor)
                                cambios.append(campo)
                        if cambios:
                            aviso.save(update_fields=cambios + ["actualizada_en"])
                            actualizados += 1

        except Exception as exc:
            errores.append({
                "contrato_id": contrato.pk,
                "cliente": str(contrato.cliente),
                "error": str(exc),
            })

    return {
        "creados": creados,
        "actualizados": actualizados,
        "anulados": anulados,
        "errores": errores,
    }


def avisos_que_deben_alertar(*, hoy=None):
    hoy = hoy or timezone.localdate()
    sincronizar_avisos_facturacion(hoy=hoy)
    avisos = (
        AvisoFacturacion.objects
        .filter(estado=AvisoFacturacion.ESTADO_PENDIENTE)
        .select_related("contrato", "contrato__cliente")
        .order_by("fecha_programada", "id")
    )
    return [aviso for aviso in avisos if aviso.fecha_alerta <= hoy]
