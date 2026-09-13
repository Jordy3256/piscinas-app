from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from contratos.models import Contrato
from inventario.models import Insumo, InventarioContrato, MovimientoInventario


D0 = Decimal("0.00")
Q3 = Decimal("0.001")


def _money(value):
    return Decimal(value or 0).quantize(Decimal("0.01"))


def _qty(value):
    return Decimal(value or 0).quantize(Q3)


def _contrato_vigente_q(hoy):
    return Q(activo=True, fecha_inicio__lte=hoy) & (
        Q(fecha_fin_contrato__isnull=True) | Q(fecha_fin_contrato__gte=hoy)
    )


def _contrato_ciudad(contrato):
    if not contrato:
        return None
    return contrato.ciudad_ref or getattr(contrato.cliente, "ciudad_ref", None)


def _movimiento_contrato(mov):
    if mov.contrato_id:
        return mov.contrato
    if mov.mantenimiento_id and mov.mantenimiento:
        return mov.mantenimiento.contrato
    return None


def _acepta_ciudad(contrato, ciudad):
    if ciudad is None:
        return True
    return bool(contrato and _contrato_ciudad(contrato) and _contrato_ciudad(contrato).pk == ciudad.pk)


def analizar_inventario_inteligente(*, hoy=None, ciudad=None):
    """
    Analítica ejecutiva de inventario.

    Usa movimientos reales registrados. Las autonomías son estimaciones basadas
    en consumo reciente y no sustituyen conteos físicos.
    """
    hoy = hoy or timezone.localdate()
    inicio_mes = hoy.replace(day=1)
    inicio_30 = hoy - timedelta(days=29)
    inicio_hist = inicio_mes - timedelta(days=90)

    consumo_tipos = ["mantenimiento", "consumo_contrato"]

    movimientos = list(
        MovimientoInventario.objects.filter(
            tipo__in=consumo_tipos,
            fecha__gte=inicio_hist,
            fecha__lte=hoy,
        ).select_related(
            "insumo",
            "contrato__cliente",
            "contrato__ciudad_ref",
            "contrato__cliente__ciudad_ref",
            "mantenimiento__contrato__cliente",
            "mantenimiento__contrato__ciudad_ref",
            "mantenimiento__contrato__cliente__ciudad_ref",
        )
    )

    # Filtrado territorial después de resolver el contrato real del movimiento.
    movimientos = [
        m for m in movimientos
        if _acepta_ciudad(_movimiento_contrato(m), ciudad)
    ]

    consumo_mes = [m for m in movimientos if m.fecha >= inicio_mes]
    consumo_30 = [m for m in movimientos if m.fecha >= inicio_30]
    historico_prev = [m for m in movimientos if inicio_hist <= m.fecha < inicio_mes]

    costo_mes = sum((_money(m.total_costo) for m in consumo_mes), D0)
    cantidad_mes = sum((_qty(m.cantidad) for m in consumo_mes), Decimal("0.000"))

    # Consumo por producto.
    productos = defaultdict(lambda: {
        "insumo": None,
        "cantidad_mes": Decimal("0.000"),
        "costo_mes": D0,
        "cantidad_30": Decimal("0.000"),
        "costo_30": D0,
        "movimientos": 0,
    })
    for m in movimientos:
        p = productos[m.insumo_id]
        p["insumo"] = m.insumo
        if m.fecha >= inicio_30:
            p["cantidad_30"] += _qty(m.cantidad)
            p["costo_30"] += _money(m.total_costo)
        if m.fecha >= inicio_mes:
            p["cantidad_mes"] += _qty(m.cantidad)
            p["costo_mes"] += _money(m.total_costo)
            p["movimientos"] += 1

    ranking_productos = []
    for p in productos.values():
        dias = 30
        consumo_diario = p["cantidad_30"] / Decimal(dias) if p["cantidad_30"] > 0 else Decimal("0")
        stock = _qty(p["insumo"].stock)
        autonomia = int(stock / consumo_diario) if consumo_diario > 0 else None
        if stock <= 0:
            estado = "agotado"
        elif stock <= Decimal(p["insumo"].stock_minimo or 0):
            estado = "critico"
        elif autonomia is not None and autonomia <= 7:
            estado = "proximo"
        else:
            estado = "correcto"
        ranking_productos.append({
            **p,
            "stock": stock,
            "stock_minimo": _qty(p["insumo"].stock_minimo),
            "consumo_diario": _qty(consumo_diario),
            "autonomia_dias": autonomia,
            "estado": estado,
            "url": reverse("inventario_producto_detalle", args=[p["insumo"].pk]),
        })
    ranking_productos.sort(key=lambda x: x["costo_mes"], reverse=True)

    # Productos activos sin consumo reciente también deben aparecer si el stock está crítico.
    ids_productos = {x["insumo"].pk for x in ranking_productos}
    for insumo in Insumo.objects.filter(activo=True, controla_inventario=True):
        if insumo.pk in ids_productos:
            continue
        stock = _qty(insumo.stock)
        if stock <= Decimal(insumo.stock_minimo or 0):
            ranking_productos.append({
                "insumo": insumo, "cantidad_mes": Decimal("0.000"), "costo_mes": D0,
                "cantidad_30": Decimal("0.000"), "costo_30": D0, "movimientos": 0,
                "stock": stock, "stock_minimo": _qty(insumo.stock_minimo),
                "consumo_diario": Decimal("0.000"), "autonomia_dias": None,
                "estado": "agotado" if stock <= 0 else "critico",
                "url": reverse("inventario_producto_detalle", args=[insumo.pk]),
            })

    # Costos y desvíos por contrato.
    actual = defaultdict(lambda: {"contrato": None, "costo": D0, "cantidad": Decimal("0.000")})
    previo = defaultdict(lambda: {"costo": D0, "meses": set()})
    for m in consumo_mes:
        c = _movimiento_contrato(m)
        if not c:
            continue
        a = actual[c.pk]
        a["contrato"] = c
        a["costo"] += _money(m.total_costo)
        a["cantidad"] += _qty(m.cantidad)
    for m in historico_prev:
        c = _movimiento_contrato(m)
        if not c:
            continue
        previo[c.pk]["costo"] += _money(m.total_costo)
        previo[c.pk]["meses"].add((m.fecha.year, m.fecha.month))

    contratos = []
    for cid, a in actual.items():
        hist = previo[cid]
        n_meses = max(len(hist["meses"]), 1)
        promedio = _money(hist["costo"] / Decimal(n_meses)) if hist["costo"] else D0
        variacion = (
            round(float((a["costo"] - promedio) / promedio * 100), 1)
            if promedio > 0 else None
        )
        anomalo = bool(
            promedio >= Decimal("5.00")
            and a["costo"] >= promedio * Decimal("1.50")
            and (a["costo"] - promedio) >= Decimal("5.00")
        )
        c = a["contrato"]
        contratos.append({
            **a,
            "promedio_previo": promedio,
            "variacion_pct": variacion,
            "anomalo": anomalo,
            "ciudad": (
                _contrato_ciudad(c).nombre if _contrato_ciudad(c)
                else (c.ciudad or getattr(c.cliente, "ciudad", "") or "Sin ciudad")
            ),
            "url": reverse("contrato_detalle", args=[c.pk]),
        })
    contratos.sort(key=lambda x: (x["anomalo"], x["costo"]), reverse=True)

    # Costos por ciudad.
    ciudades = defaultdict(lambda: {"nombre": "", "costo": D0, "cantidad": Decimal("0.000"), "contratos": set()})
    for m in consumo_mes:
        c = _movimiento_contrato(m)
        if not c:
            continue
        city = _contrato_ciudad(c)
        nombre = city.nombre if city else (c.ciudad or getattr(c.cliente, "ciudad", "") or "Sin ciudad")
        item = ciudades[nombre]
        item["nombre"] = nombre
        item["costo"] += _money(m.total_costo)
        item["cantidad"] += _qty(m.cantidad)
        item["contratos"].add(c.pk)
    ranking_ciudades = []
    for item in ciudades.values():
        ranking_ciudades.append({
            "nombre": item["nombre"],
            "costo": _money(item["costo"]),
            "cantidad": _qty(item["cantidad"]),
            "contratos": len(item["contratos"]),
        })
    ranking_ciudades.sort(key=lambda x: x["costo"], reverse=True)

    # Inventario en sitio: utiliza la lógica de estimación ya existente.
    sitio_qs = (
        InventarioContrato.objects.filter(contrato__in=Contrato.objects.filter(_contrato_vigente_q(hoy)))
        .select_related("contrato__cliente", "contrato__ciudad_ref", "contrato__cliente__ciudad_ref", "insumo")
    )
    if ciudad is not None:
        sitio_qs = sitio_qs.filter(
            Q(contrato__ciudad_ref=ciudad)
            | Q(contrato__ciudad_ref__isnull=True, contrato__cliente__ciudad_ref=ciudad)
        )

    sitio_critico = []
    for inv in sitio_qs:
        if inv.estado_stock in {"agotado", "critico", "proximo"}:
            sitio_critico.append({
                "inventario": inv,
                "contrato": inv.contrato,
                "insumo": inv.insumo,
                "stock_estimado": _qty(inv.stock_estimado),
                "dias_hasta_minimo": inv.dias_hasta_minimo,
                "estado": inv.estado_stock,
                "url": reverse("contrato_detalle", args=[inv.contrato_id]),
            })
    sitio_critico.sort(
        key=lambda x: (
            {"agotado": 0, "critico": 1, "proximo": 2}.get(x["estado"], 9),
            x["dias_hasta_minimo"] if x["dias_hasta_minimo"] is not None else 9999,
        )
    )

    agotados = sum(1 for x in ranking_productos if x["estado"] == "agotado")
    criticos = sum(1 for x in ranking_productos if x["estado"] == "critico")
    proximos = sum(1 for x in ranking_productos if x["estado"] == "proximo")
    anomalos = sum(1 for x in contratos if x["anomalo"])

    senales = []
    if agotados:
        senales.append({
            "nivel": "critico",
            "titulo": "Productos agotados",
            "texto": f"{agotados} producto(s) activos están sin stock.",
        })
    if criticos:
        senales.append({
            "nivel": "critico",
            "titulo": "Stock por debajo del mínimo",
            "texto": f"{criticos} producto(s) requieren reposición.",
        })
    if sitio_critico:
        senales.append({
            "nivel": "atencion",
            "titulo": "Inventario en sitio requiere atención",
            "texto": f"{len(sitio_critico)} posición(es) de inventario en contratos están agotadas, críticas o próximas al mínimo.",
        })
    if anomalos:
        senales.append({
            "nivel": "atencion",
            "titulo": "Consumo anormal detectado",
            "texto": f"{anomalos} contrato(s) consumen al menos 50% más que su promedio histórico reciente.",
        })
    if not senales:
        senales.append({
            "nivel": "saludable",
            "titulo": "Inventario bajo control",
            "texto": "No se detectan alertas críticas de stock o desviaciones relevantes con los registros actuales.",
        })

    valor_stock = sum(
        (_qty(i.stock) * Decimal(i.costo or 0) for i in Insumo.objects.filter(activo=True, controla_inventario=True)),
        D0,
    )

    return {
        "costo_mes": _money(costo_mes),
        "cantidad_mes": _qty(cantidad_mes),
        "valor_stock": _money(valor_stock),
        "agotados": agotados,
        "criticos": criticos,
        "proximos": proximos,
        "anomalos": anomalos,
        "ranking_productos": ranking_productos,
        "contratos": contratos,
        "ranking_ciudades": ranking_ciudades,
        "sitio_critico": sitio_critico,
        "senales": senales,
    }
