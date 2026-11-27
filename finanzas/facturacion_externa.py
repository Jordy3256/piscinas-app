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
    contratos = list(contratos)
    contratos_ids = {contrato.pk for contrato in contratos}

    qs_anular = AvisoFacturacion.objects.filter(
        estado=AvisoFacturacion.ESTADO_PENDIENTE
    ).exclude(contrato_id__in=contratos_ids)
    if qs_anular.exists():
        anulados += qs_anular.update(estado=AvisoFacturacion.ESTADO_ANULADA)

    for contrato in contratos:
        try:
            existentes = {
                (aviso.periodo_anio, aviso.periodo_mes, aviso.cuota_numero): aviso
                for aviso in AvisoFacturacion.objects.filter(contrato=contrato)
            }
            pendientes = {}
            for (anio_aviso, mes_aviso, cuota), aviso in existentes.items():
                if aviso.estado == AvisoFacturacion.ESTADO_PENDIENTE:
                    pendientes.setdefault((anio_aviso, mes_aviso), set()).add(cuota)
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
                    cuotas = contrato.calendario_cobros(anio, mes)
                    ids = {cuota.get("mantenimiento_id") for cuota in cuotas} - {None}
                    realizadas = set(Mantenimiento.objects.filter(
                        pk__in=ids, estado="realizado"
                    ).values_list("pk", flat=True)) if ids else set()
                    for cuota in cuotas:
                        mantenimiento_id = cuota.get("mantenimiento_id")
                        if mantenimiento_id not in realizadas:
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
                sobrantes = pendientes.get((anio, mes), set()) - esperadas
                if sobrantes:
                    anulados += AvisoFacturacion.objects.filter(
                        contrato=contrato, periodo_anio=anio, periodo_mes=mes,
                        estado=AvisoFacturacion.ESTADO_PENDIENTE,
                        cuota_numero__in=sobrantes,
                    ).update(estado=AvisoFacturacion.ESTADO_ANULADA)

                for evento in eventos:
                    fecha_programada = evento["fecha_programada"]

                    # Conservamos la política histórica: no recrear recordatorios
                    # demasiado antiguos si ya no existían.
                    if fecha_programada < hoy - timedelta(days=31):
                        continue

                    aviso = existentes.get((anio, mes, evento["cuota_numero"]))
                    creado = False
                    if aviso is None:
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
                            actualizados += AvisoFacturacion.objects.filter(
                                pk=aviso.pk, estado=AvisoFacturacion.ESTADO_PENDIENTE,
                            ).update(**{campo: getattr(aviso, campo) for campo in cambios},
                                     actualizada_en=timezone.now())

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
