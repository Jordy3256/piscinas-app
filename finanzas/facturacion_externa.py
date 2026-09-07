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

    Una configuración histórica/incompleta en un contrato no debe impedir abrir
    el módulo completo. Los errores se devuelven para diagnóstico y el resto de
    contratos continúa sincronizándose.
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

                fecha_programada = contrato.fecha_programada_facturacion(anio, mes)
                if not fecha_programada:
                    continue

                if fecha_programada < hoy - timedelta(days=31):
                    continue

                aviso, creado = AvisoFacturacion.objects.get_or_create(
                    contrato=contrato,
                    periodo_anio=anio,
                    periodo_mes=mes,
                    defaults={
                        "periodo_inicio": periodo_inicio,
                        "periodo_fin": periodo_fin,
                        "fecha_programada": fecha_programada,
                    },
                )
                if creado:
                    creados += 1
                    continue

                if aviso.estado == AvisoFacturacion.ESTADO_PENDIENTE:
                    cambios = []
                    for campo, valor in {
                        "periodo_inicio": periodo_inicio,
                        "periodo_fin": periodo_fin,
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
