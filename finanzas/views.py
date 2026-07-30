from calendar import monthrange
from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.urls import reverse

from .forms import EgresoForm, IngresoForm, PagoFacturaForm
from .models import Egreso, Factura, Ingreso, PagoFactura
from .cuentas_por_cobrar import MESES, generar_facturas_periodo, previsualizar_facturas_periodo


def _es_admin(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    grupos = {g.name.strip().lower() for g in user.groups.all()}
    return bool({"administradores", "administrador", "admins", "adimistradores"} & grupos)


def _denegado(request):
    return render(request, "dashboard/no_autorizado.html", status=403)


def _rango_mes(anio, mes):
    return date(anio, mes, 1), date(anio, mes, monthrange(anio, mes)[1])


def _sum(qs, field):
    return qs.aggregate(valor=Sum(field))["valor"] or Decimal("0.00")


def _mes_anterior(anio, mes):
    return (anio - 1, 12) if mes == 1 else (anio, mes - 1)


def _variacion(actual, anterior):
    if anterior == 0:
        return Decimal("100.00") if actual > 0 else Decimal("0.00")
    return ((actual - anterior) / abs(anterior)) * Decimal("100.00")


@login_required
def panel_financiero(request):
    if not _es_admin(request.user):
        return _denegado(request)

    hoy = timezone.localdate()
    try:
        anio = int(request.GET.get("anio", hoy.year))
        mes = int(request.GET.get("mes", hoy.month))
        if mes < 1 or mes > 12:
            raise ValueError
    except (TypeError, ValueError):
        anio, mes = hoy.year, hoy.month

    inicio, fin = _rango_mes(anio, mes)
    ingresos = Ingreso.objects.select_related("cliente", "contrato").filter(fecha__range=(inicio, fin))
    egresos = Egreso.objects.filter(fecha__range=(inicio, fin))

    ingresos_validos = ingresos.exclude(estado=Ingreso.ESTADO_ANULADO)
    egresos_validos = egresos.exclude(estado=Egreso.ESTADO_ANULADO)

    ingresos_cobrados = _sum(ingresos_validos, "monto_pagado")
    egresos_pagados = _sum(egresos_validos.filter(aprobado=True), "monto_pagado")
    utilidad_real = ingresos_cobrados - egresos_pagados

    ingresos_esperados = _sum(ingresos_validos, "total")
    egresos_previstos = _sum(egresos_validos.filter(aprobado=True), "total")
    resultado_proyectado = ingresos_esperados - egresos_previstos

    por_cobrar = sum((m.saldo for m in ingresos_validos), Decimal("0.00"))
    por_pagar = sum((m.saldo for m in egresos_validos.filter(aprobado=True)), Decimal("0.00"))

    vencidos_ingresos = [m for m in ingresos_validos if m.estado_visual == Ingreso.ESTADO_VENCIDO and m.saldo > 0]
    vencidos_egresos = [m for m in egresos_validos if m.estado_visual == Egreso.ESTADO_VENCIDO and m.saldo > 0]

    ant_anio, ant_mes = _mes_anterior(anio, mes)
    ant_inicio, ant_fin = _rango_mes(ant_anio, ant_mes)
    ingresos_ant = Ingreso.objects.filter(fecha__range=(ant_inicio, ant_fin)).exclude(estado=Ingreso.ESTADO_ANULADO)
    egresos_ant = Egreso.objects.filter(fecha__range=(ant_inicio, ant_fin), aprobado=True).exclude(estado=Egreso.ESTADO_ANULADO)
    ingresos_cobrados_ant = _sum(ingresos_ant, "monto_pagado")
    egresos_pagados_ant = _sum(egresos_ant, "monto_pagado")
    utilidad_ant = ingresos_cobrados_ant - egresos_pagados_ant

    categorias = list(
        egresos_validos.values("categoria")
        .annotate(total_categoria=Sum("monto_pagado"))
        .order_by("-total_categoria")[:6]
    )
    labels_categoria = dict(Egreso.CATEGORIA_CHOICES)
    for item in categorias:
        item["label"] = labels_categoria.get(item["categoria"], item["categoria"] or "Sin categoría")
        item["porcentaje"] = int((item["total_categoria"] / egresos_pagados) * 100) if egresos_pagados else 0

    ultimos = []
    for item in ingresos.order_by("-fecha", "-id")[:8]:
        ultimos.append({"tipo": "ingreso", "obj": item, "fecha": item.fecha})
    for item in egresos.order_by("-fecha", "-id")[:8]:
        ultimos.append({"tipo": "egreso", "obj": item, "fecha": item.fecha})
    ultimos = sorted(ultimos, key=lambda x: (x["fecha"], x["obj"].pk), reverse=True)[:10]

    return render(request, "finanzas/panel.html", {
        "anio": anio,
        "mes": mes,
        "inicio": inicio,
        "fin": fin,
        "hoy": hoy,
        "ingresos_cobrados": ingresos_cobrados,
        "egresos_pagados": egresos_pagados,
        "utilidad_real": utilidad_real,
        "ingresos_esperados": ingresos_esperados,
        "egresos_previstos": egresos_previstos,
        "resultado_proyectado": resultado_proyectado,
        "por_cobrar": por_cobrar,
        "por_pagar": por_pagar,
        "vencidos_ingresos": vencidos_ingresos[:6],
        "vencidos_egresos": vencidos_egresos[:6],
        "total_vencidos_ingresos": len(vencidos_ingresos),
        "total_vencidos_egresos": len(vencidos_egresos),
        "variacion_ingresos": _variacion(ingresos_cobrados, ingresos_cobrados_ant),
        "variacion_egresos": _variacion(egresos_pagados, egresos_pagados_ant),
        "variacion_utilidad": _variacion(utilidad_real, utilidad_ant),
        "categorias": categorias,
        "ultimos": ultimos,
        "es_admin": True,
    })


@login_required
def movimientos(request):
    if not _es_admin(request.user):
        return _denegado(request)

    tipo = (request.GET.get("tipo") or "todos").strip().lower()
    estado = (request.GET.get("estado") or "").strip().lower()
    q = (request.GET.get("q") or "").strip()
    desde = parse_date(request.GET.get("desde") or "")
    hasta = parse_date(request.GET.get("hasta") or "")

    ingresos = Ingreso.objects.select_related("cliente", "contrato").all()
    egresos = Egreso.objects.all()

    if estado:
        ingresos = ingresos.filter(estado=estado)
        egresos = egresos.filter(estado=estado)
    if desde:
        ingresos = ingresos.filter(fecha__gte=desde)
        egresos = egresos.filter(fecha__gte=desde)
    if hasta:
        ingresos = ingresos.filter(fecha__lte=hasta)
        egresos = egresos.filter(fecha__lte=hasta)
    if q:
        ingresos = ingresos.filter(Q(concepto__icontains=q) | Q(cliente__nombre__icontains=q) | Q(ciudad__icontains=q))
        egresos = egresos.filter(Q(concepto__icontains=q) | Q(proveedor__icontains=q) | Q(ciudad_proyecto__icontains=q))

    items = []
    if tipo in {"todos", "ingresos"}:
        items.extend({"tipo": "ingreso", "obj": x, "fecha": x.fecha} for x in ingresos)
    if tipo in {"todos", "egresos"}:
        items.extend({"tipo": "egreso", "obj": x, "fecha": x.fecha} for x in egresos)
    items.sort(key=lambda x: (x["fecha"], x["obj"].pk), reverse=True)

    paginator = Paginator(items, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)

    return render(request, "finanzas/movimientos.html", {
        "page_obj": page_obj,
        "tipo": tipo,
        "estado": estado,
        "q": q,
        "desde": request.GET.get("desde", ""),
        "hasta": request.GET.get("hasta", ""),
        "estados": Ingreso.ESTADO_CHOICES,
        "querystring": params.urlencode(),
        "es_admin": True,
    })


@login_required
def ingreso_form(request, pk=None):
    if not _es_admin(request.user):
        return _denegado(request)
    obj = get_object_or_404(Ingreso, pk=pk) if pk else None
    form = IngresoForm(request.POST or None, request.FILES or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        movimiento = form.save(commit=False)
        if not movimiento.creado_por_id:
            movimiento.creado_por = request.user
        if movimiento.monto_pagado >= movimiento.total:
            movimiento.estado = movimiento.ESTADO_PAGADO
        elif movimiento.monto_pagado > 0:
            movimiento.estado = movimiento.ESTADO_PARCIAL
        else:
            movimiento.estado = movimiento.ESTADO_PENDIENTE
        movimiento.save()
        messages.success(request, "Ingreso actualizado correctamente." if obj else "Ingreso registrado correctamente.")
        return redirect("finanzas_movimientos")
    return render(request, "finanzas/formulario.html", {"form": form, "tipo": "Ingreso", "obj": obj, "es_admin": True})


@login_required
def egreso_form(request, pk=None):
    if not _es_admin(request.user):
        return _denegado(request)
    obj = get_object_or_404(Egreso, pk=pk) if pk else None
    form = EgresoForm(request.POST or None, request.FILES or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        movimiento = form.save(commit=False)
        if not movimiento.creado_por_id:
            movimiento.creado_por = request.user
        if movimiento.monto_pagado >= movimiento.total:
            movimiento.estado = movimiento.ESTADO_PAGADO
        elif movimiento.monto_pagado > 0:
            movimiento.estado = movimiento.ESTADO_PARCIAL
        else:
            movimiento.estado = movimiento.ESTADO_PENDIENTE
        movimiento.save()
        messages.success(request, "Egreso actualizado correctamente." if obj else "Egreso registrado correctamente.")
        return redirect("finanzas_movimientos")
    return render(request, "finanzas/formulario.html", {"form": form, "tipo": "Egreso", "obj": obj, "es_admin": True})


@login_required
def movimiento_eliminar(request, tipo, pk):
    if not _es_admin(request.user):
        return _denegado(request)
    modelo = Ingreso if tipo == "ingreso" else Egreso if tipo == "egreso" else None
    if modelo is None:
        return redirect("finanzas_movimientos")
    obj = get_object_or_404(modelo, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Movimiento eliminado correctamente.")
        return redirect("finanzas_movimientos")
    return render(request, "finanzas/eliminar.html", {"obj": obj, "tipo": tipo, "es_admin": True})


@login_required
def facturas_lista(request):
    if not _es_admin(request.user):
        return _denegado(request)
    hoy = timezone.localdate()
    q = (request.GET.get("q") or "").strip()
    estado = (request.GET.get("estado") or "").strip()
    try:
        anio = int(request.GET.get("anio") or hoy.year)
        mes_raw = request.GET.get("mes")
        mes = int(mes_raw) if mes_raw else None
    except (TypeError, ValueError):
        anio, mes = hoy.year, None

    facturas = Factura.objects.select_related("cliente", "contrato").prefetch_related("pagos")
    facturas = facturas.filter(periodo_anio=anio)
    if mes:
        facturas = facturas.filter(periodo_mes=mes)
    if estado:
        facturas = facturas.filter(estado=estado)
    if q:
        facturas = facturas.filter(Q(numero__icontains=q) | Q(cliente__nombre__icontains=q) | Q(cliente__telefono__icontains=q))

    facturas = list(facturas)
    total_facturado = sum((f.total for f in facturas if f.estado != Factura.ESTADO_ANULADA), Decimal("0.00"))
    total_cobrado = sum((f.monto_pagado for f in facturas if f.estado != Factura.ESTADO_ANULADA), Decimal("0.00"))
    total_pendiente = sum((f.saldo for f in facturas if f.estado != Factura.ESTADO_ANULADA), Decimal("0.00"))
    total_vencido = sum((f.saldo for f in facturas if f.estado_visual == Factura.ESTADO_VENCIDA), Decimal("0.00"))

    paginator = Paginator(facturas, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    params = request.GET.copy(); params.pop("page", None)
    return render(request, "finanzas/facturas_lista.html", {
        "page_obj": page_obj, "q": q, "estado": estado, "anio": anio, "mes": mes or hoy.month,
        "estados": Factura.ESTADO_CHOICES, "querystring": params.urlencode(),
        "total_facturado": total_facturado, "total_cobrado": total_cobrado,
        "total_pendiente": total_pendiente, "total_vencido": total_vencido,
        "meses": MESES, "es_admin": True,
    })


@login_required
def factura_detalle(request, pk):
    if not _es_admin(request.user):
        return _denegado(request)
    factura = get_object_or_404(
        Factura.objects.select_related("cliente", "contrato").prefetch_related("items", "pagos__ingreso"), pk=pk
    )
    return render(request, "finanzas/factura_detalle.html", {"factura": factura, "es_admin": True})


@login_required
def factura_pago_nuevo(request, pk):
    if not _es_admin(request.user):
        return _denegado(request)
    factura = get_object_or_404(Factura, pk=pk)
    if factura.estado == Factura.ESTADO_ANULADA or factura.saldo <= 0:
        messages.warning(request, "Esta cuenta por cobrar no admite nuevos pagos.")
        return redirect("finanzas_factura_detalle", pk=factura.pk)
    form = PagoFacturaForm(request.POST or None, request.FILES or None, factura=factura)
    if request.method == "POST" and form.is_valid():
        pago = form.save(commit=False)
        pago.factura = factura
        pago.creado_por = request.user
        pago.save()
        messages.success(request, "Pago registrado. El ingreso real se creó automáticamente.")
        return redirect("finanzas_factura_detalle", pk=factura.pk)
    return render(request, "finanzas/pago_factura_form.html", {"form": form, "factura": factura, "es_admin": True})


@login_required
def factura_pago_anular(request, pk, pago_pk):
    if not _es_admin(request.user):
        return _denegado(request)
    factura = get_object_or_404(Factura, pk=pk)
    pago = get_object_or_404(PagoFactura, pk=pago_pk, factura=factura)
    if request.method == "POST":
        pago.anular()
        messages.success(request, "Pago anulado. El ingreso vinculado también fue anulado.")
    return redirect("finanzas_factura_detalle", pk=factura.pk)


@login_required
def generar_facturas_desde_contratos(request):
    if not _es_admin(request.user):
        return _denegado(request)
    if request.method != "POST":
        return redirect("finanzas_facturas")

    hoy = timezone.localdate()
    try:
        anio = int(request.POST.get("anio") or hoy.year)
        mes = int(request.POST.get("mes") or hoy.month)
        if not 1 <= mes <= 12 or not 2020 <= anio <= 2100:
            raise ValueError
    except (TypeError, ValueError):
        messages.error(request, "Selecciona un mes y un año válidos.")
        return redirect("finanzas_facturas")

    accion = (request.POST.get("accion") or "previsualizar").strip().lower()
    if accion != "generar":
        vista_previa = previsualizar_facturas_periodo(anio, mes)
        facturas = Factura.objects.select_related("cliente", "contrato").filter(
            periodo_anio=anio, periodo_mes=mes
        )
        facturas = list(facturas)
        paginator = Paginator(facturas, 20)
        page_obj = paginator.get_page(1)
        return render(request, "finanzas/facturas_lista.html", {
            "page_obj": page_obj, "q": "", "estado": "", "anio": anio, "mes": mes,
            "estados": Factura.ESTADO_CHOICES, "querystring": f"anio={anio}&mes={mes}",
            "total_facturado": sum((f.total for f in facturas if f.estado != Factura.ESTADO_ANULADA), Decimal("0.00")),
            "total_cobrado": sum((f.monto_pagado for f in facturas if f.estado != Factura.ESTADO_ANULADA), Decimal("0.00")),
            "total_pendiente": sum((f.saldo for f in facturas if f.estado != Factura.ESTADO_ANULADA), Decimal("0.00")),
            "total_vencido": sum((f.saldo for f in facturas if f.estado_visual == Factura.ESTADO_VENCIDA), Decimal("0.00")),
            "meses": MESES, "vista_previa": vista_previa, "es_admin": True,
        })

    resultado = generar_facturas_periodo(anio, mes, usuario=request.user)
    messages.success(
        request,
        f"Proceso completado: {resultado['creadas']} mensualidades creadas, "
        f"{resultado['existentes']} omitidas y ${resultado['valor_generado']:.2f} generados."
    )
    if resultado["errores"]:
        messages.warning(request, f"No se pudieron procesar {len(resultado['errores'])} contratos.")
    return redirect(f"{reverse('finanzas_facturas')}?anio={anio}&mes={mes}")
