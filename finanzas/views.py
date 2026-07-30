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

from .forms import EgresoForm, IngresoForm
from .models import Egreso, Ingreso


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
