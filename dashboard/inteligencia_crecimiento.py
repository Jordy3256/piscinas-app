from calendar import monthrange
from collections import defaultdict
import json
from datetime import date
from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone

from contratos.models import Contrato, ReactivacionContrato
from clientes.models import Ciudad


D0 = Decimal("0.00")


def _money(value):
    return Decimal(value or 0).quantize(Decimal("0.01"))


def _month_shift(base, delta):
    idx = base.year * 12 + base.month - 1 + delta
    return date(idx // 12, idx % 12 + 1, 1)


def _city_filter(ciudad):
    if ciudad is None:
        return Q()
    return Q(ciudad_ref=ciudad) | Q(ciudad_ref__isnull=True, cliente__ciudad_ref=ciudad)


def _active_at(qs, day):
    return (
        qs.filter(fecha_inicio_original__lte=day)
        .filter(Q(fecha_baja__isnull=True) | Q(fecha_baja__gt=day))
        .filter(Q(fecha_fin_contrato__isnull=True) | Q(fecha_fin_contrato__gte=day))
    )


def analizar_crecimiento_retencion(*, hoy=None, ciudad=None, meses=12):
    hoy = hoy or timezone.localdate()
    base = hoy.replace(day=1)
    contratos = Contrato.objects.select_related("cliente", "ciudad_ref", "cliente__ciudad_ref").filter(_city_filter(ciudad))
    reactivaciones = ReactivacionContrato.objects.select_related(
        "contrato", "contrato__cliente", "contrato__ciudad_ref", "contrato__cliente__ciudad_ref"
    )
    if ciudad is not None:
        reactivaciones = reactivaciones.filter(
            Q(contrato__ciudad_ref=ciudad)
            | Q(contrato__ciudad_ref__isnull=True, contrato__cliente__ciudad_ref=ciudad)
        )

    serie = []
    for offset in range(-(meses - 1), 1):
        ini = _month_shift(base, offset)
        fin = date(ini.year, ini.month, monthrange(ini.year, ini.month)[1])
        fin_real = min(fin, hoy) if ini.year == hoy.year and ini.month == hoy.month else fin
        apertura = ini if ini.day == 1 else ini
        dia_anterior = date.fromordinal(ini.toordinal() - 1)

        activos_inicio = _active_at(contratos, dia_anterior).count()
        activos_fin = _active_at(contratos, fin_real).count()
        altas_qs = contratos.filter(fecha_inicio_original__range=(ini, fin_real))
        bajas_qs = contratos.filter(fecha_baja__range=(ini, fin_real))
        rec_qs = reactivaciones.filter(fecha_reactivacion__range=(ini, fin_real))

        altas = altas_qs.count()
        bajas = bajas_qs.count()
        recuperados = rec_qs.count()
        ingreso_ganado = _money(altas_qs.aggregate(v=Sum("precio_mensual"))["v"])
        ingreso_perdido = _money(bajas_qs.aggregate(v=Sum("precio_mensual"))["v"])
        ingreso_recuperado = _money(rec_qs.aggregate(v=Sum("precio_mensual"))["v"])
        base_retencion = activos_inicio
        retencion = round(max(0.0, ((base_retencion - bajas) / base_retencion) * 100), 1) if base_retencion else 100.0

        serie.append({
            "inicio": ini, "fin": fin_real, "label": ini.strftime("%b %y"),
            "activos_inicio": activos_inicio, "activos_fin": activos_fin,
            "altas": altas, "bajas": bajas, "recuperados": recuperados,
            "crecimiento_neto": altas + recuperados - bajas,
            "ingreso_ganado": ingreso_ganado, "ingreso_perdido": ingreso_perdido,
            "ingreso_recuperado": ingreso_recuperado, "retencion": retencion,
        })

    actual = serie[-1]
    bajas_actuales = contratos.filter(fecha_baja__range=(actual["inicio"], actual["fin"]))
    motivos = []
    labels_motivos = dict(Contrato.MOTIVO_BAJA_CHOICES)
    # Count se hace aparte para conservar compatibilidad con SQLite/PostgreSQL.
    conteo = defaultdict(int)
    for codigo in bajas_actuales.values_list("motivo_baja", flat=True):
        codigo = codigo or "no_especificado"
        conteo[codigo] += 1
    for codigo, total in sorted(conteo.items(), key=lambda x: (-x[1], x[0])):
        motivos.append({"codigo": codigo, "nombre": labels_motivos.get(codigo, "No especificado"), "total": total})

    # Ranking territorial del mes actual.
    ranking_ciudades = []
    for c in Ciudad.objects.filter(activa=True).order_by("orden", "nombre"):
        cqs = Contrato.objects.filter(_city_filter(c))
        rqs = ReactivacionContrato.objects.filter(
            Q(contrato__ciudad_ref=c) | Q(contrato__ciudad_ref__isnull=True, contrato__cliente__ciudad_ref=c),
            fecha_reactivacion__range=(actual["inicio"], actual["fin"]),
        )
        altas = cqs.filter(fecha_inicio_original__range=(actual["inicio"], actual["fin"])).count()
        bajas = cqs.filter(fecha_baja__range=(actual["inicio"], actual["fin"])).count()
        recuperados = rqs.count()
        activos = _active_at(cqs, actual["fin"]).count()
        if altas or bajas or recuperados or activos:
            ranking_ciudades.append({
                "ciudad": c, "altas": altas, "bajas": bajas, "recuperados": recuperados,
                "activos": activos, "neto": altas + recuperados - bajas,
            })
    ranking_ciudades.sort(key=lambda x: (x["neto"], x["activos"]), reverse=True)

    # Señales ejecutivas, deliberadamente simples y explicables.
    alertas = []
    if actual["bajas"] > actual["altas"] + actual["recuperados"]:
        alertas.append({"nivel": "critica", "titulo": "Contracción comercial",
                        "texto": "Este mes las bajas superan las altas y recuperaciones."})
    if actual["retencion"] < 95:
        alertas.append({"nivel": "atencion", "titulo": "Retención por debajo de 95%",
                        "texto": f"La retención estimada del mes es {actual['retencion']}%."})
    if actual["ingreso_perdido"] > actual["ingreso_ganado"] + actual["ingreso_recuperado"]:
        alertas.append({"nivel": "atencion", "titulo": "Facturación mensual en riesgo",
                        "texto": "La mensualidad perdida supera la mensualidad ganada y recuperada del período."})
    if not alertas:
        alertas.append({"nivel": "saludable", "titulo": "Crecimiento bajo control",
                        "texto": "No se detectan señales comerciales críticas con los datos del mes."})

    return {
        "serie": serie, "actual": actual, "motivos": motivos,
        "ranking_ciudades": ranking_ciudades, "alertas": alertas,
        "grafico_contratos": json.dumps({
            "labels": [x["label"] for x in serie],
            "altas": [x["altas"] for x in serie],
            "bajas": [x["bajas"] for x in serie],
            "recuperados": [x["recuperados"] for x in serie],
            "activos": [x["activos_fin"] for x in serie],
        }),
        "grafico_retencion": json.dumps({
            "labels": [x["label"] for x in serie],
            "retencion": [x["retencion"] for x in serie],
        }),
    }
