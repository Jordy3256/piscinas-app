from calendar import monthrange
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.urls import reverse
from django.utils.text import slugify

from .forms import EgresoForm, IngresoForm, PagoFacturaForm, PagoTrabajadorForm, PagoConsolidadoTrabajadorForm
from .models import Egreso, Factura, Ingreso, PagoFactura, ObligacionTrabajador, PagoTrabajador, LotePagoTrabajador, AnticipoTrabajador
from clientes.models import Cliente
from contratos.models import Contrato

from .cuentas_por_cobrar import MESES, generar_facturas_periodo, previsualizar_facturas_periodo

from .servicios_financieros import obtener_resumen_financiero
from .alertas_financieras import generar_alertas_financieras

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak


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

    # Al abrir Finanzas se actualizan la campana y las alertas push del administrador.
    generar_alertas_financieras(enviar_push=True)
    resumen = obtener_resumen_financiero(anio, mes)
    inicio, fin = resumen["inicio"], resumen["fin"]

    ingresos = Ingreso.objects.select_related("cliente", "contrato").filter(fecha__range=(inicio, fin))
    egresos = Egreso.objects.filter(fecha__range=(inicio, fin))
    ingresos_validos = ingresos.exclude(estado=Ingreso.ESTADO_ANULADO)
    egresos_validos = egresos.exclude(estado=Egreso.ESTADO_ANULADO)

    ant_anio, ant_mes = _mes_anterior(anio, mes)
    resumen_anterior = obtener_resumen_financiero(ant_anio, ant_mes)

    categorias = list(
        egresos_validos.filter(aprobado=True)
        .values("categoria")
        .annotate(total_categoria=Sum("monto_pagado"))
        .order_by("-total_categoria")[:6]
    )
    labels_categoria = dict(Egreso.CATEGORIA_CHOICES)
    for item in categorias:
        item["label"] = labels_categoria.get(item["categoria"], item["categoria"] or "Sin categoría")
        item["porcentaje"] = int((item["total_categoria"] / resumen["egresos_pagados"]) * 100) if resumen["egresos_pagados"] else 0

    ultimos = []
    for item in ingresos.order_by("-fecha", "-id")[:8]:
        ultimos.append({"tipo": "ingreso", "obj": item, "fecha": item.fecha})
    for item in egresos.order_by("-fecha", "-id")[:8]:
        ultimos.append({"tipo": "egreso", "obj": item, "fecha": item.fecha})
    ultimos = sorted(ultimos, key=lambda x: (x["fecha"], x["obj"].pk), reverse=True)[:10]

    prioridades = []
    for factura in resumen["cobros_vencidos"][:4]:
        prioridades.append({
            "nivel": "critica", "icono": "🔴", "titulo": "Cobro vencido",
            "detalle": f"{factura.cliente} · ${factura.saldo:.2f}",
            "url": reverse("finanzas_factura_detalle", args=[factura.pk]),
        })
    for factura in resumen["cobros_hoy"][:4]:
        prioridades.append({
            "nivel": "importante", "icono": "🟠", "titulo": "Cobrar hoy",
            "detalle": f"{factura.cliente} · ${factura.saldo:.2f}",
            "url": reverse("finanzas_factura_detalle", args=[factura.pk]),
        })
    for factura in resumen["facturas_por_emitir"][:4]:
        prioridades.append({
            "nivel": "aviso", "icono": "📄", "titulo": "Emitir o enviar factura",
            "detalle": f"{factura.cliente} · {factura.periodo_label}",
            "url": reverse("finanzas_factura_detalle", args=[factura.pk]),
        })
    for obligacion in resumen["nomina_hoy"][:4]:
        prioridades.append({
            "nivel": "info", "icono": "🔵", "titulo": "Pagar nómina",
            "detalle": f"{obligacion.trabajador} · ${obligacion.saldo:.2f}",
            "url": f"{reverse('finanzas_nomina')}?anio={obligacion.periodo_anio}&mes={obligacion.periodo_mes}",
        })

    contexto = {
        "anio": anio,
        "mes": mes,
        "inicio": inicio,
        "fin": fin,
        "hoy": hoy,
        **resumen,
        "variacion_ingresos": _variacion(resumen["ingresos_cobrados"], resumen_anterior["ingresos_cobrados"]),
        "variacion_egresos": _variacion(resumen["egresos_pagados"], resumen_anterior["egresos_pagados"]),
        "variacion_utilidad": _variacion(resumen["utilidad_real"], resumen_anterior["utilidad_real"]),
        "categorias": categorias,
        "ultimos": ultimos,
        "prioridades": prioridades[:12],
        "es_admin": True,
    }
    return render(request, "finanzas/panel.html", contexto)


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
    anio_raw = (request.GET.get("anio") or "").strip()
    mes_raw = (request.GET.get("mes") or "").strip()

    anio_filtro = None
    mes_filtro = None
    try:
        if anio_raw:
            anio_filtro = int(anio_raw)
            if not 2020 <= anio_filtro <= 2100:
                raise ValueError
        if mes_raw:
            mes_filtro = int(mes_raw)
            if not 1 <= mes_filtro <= 12:
                raise ValueError
    except (TypeError, ValueError):
        messages.warning(request, "El periodo indicado no es válido; se mostró la lista completa.")
        anio_filtro = None
        mes_filtro = None

    facturas_qs = (
        Factura.objects.select_related("cliente", "contrato")
        .prefetch_related("pagos")
        .order_by("-periodo_anio", "-periodo_mes", "cliente__nombre", "-id")
    )
    if anio_filtro:
        facturas_qs = facturas_qs.filter(periodo_anio=anio_filtro)
    if mes_filtro:
        facturas_qs = facturas_qs.filter(periodo_mes=mes_filtro)
    if estado:
        if estado == Factura.ESTADO_VENCIDA:
            facturas_qs = facturas_qs.filter(
                estado__in=[Factura.ESTADO_PENDIENTE, Factura.ESTADO_PARCIAL, Factura.ESTADO_VENCIDA],
                fecha_vencimiento__lt=hoy,
            )
        else:
            facturas_qs = facturas_qs.filter(estado=estado)
    if q:
        facturas_qs = facturas_qs.filter(
            Q(numero__icontains=q)
            | Q(cliente__nombre__icontains=q)
            | Q(cliente__telefono__icontains=q)
            | Q(cliente__ciudad__icontains=q)
        )

    facturas = list(facturas_qs)
    activas = [f for f in facturas if f.estado != Factura.ESTADO_ANULADA]
    total_facturado = sum((f.total for f in activas), Decimal("0.00"))
    total_cobrado = sum((f.monto_pagado for f in activas), Decimal("0.00"))
    total_pendiente = sum((f.saldo for f in activas), Decimal("0.00"))
    total_vencido = sum((f.saldo for f in activas if f.estado_visual == Factura.ESTADO_VENCIDA), Decimal("0.00"))

    paginator = Paginator(facturas, 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)

    return render(request, "finanzas/facturas_lista.html", {
        "page_obj": page_obj,
        "q": q,
        "estado": estado,
        "anio_filtro": anio_filtro or "",
        "mes_filtro": mes_filtro or "",
        "anio_generacion": hoy.year,
        "mes_generacion": hoy.month,
        "estados": Factura.ESTADO_CHOICES,
        "querystring": params.urlencode(),
        "total_facturado": total_facturado,
        "total_cobrado": total_cobrado,
        "total_pendiente": total_pendiente,
        "total_vencido": total_vencido,
        "meses": MESES,
        "total_registros": paginator.count,
        "es_admin": True,
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
        facturas_qs = (
            Factura.objects.select_related("cliente", "contrato")
            .prefetch_related("pagos")
            .filter(periodo_anio=anio, periodo_mes=mes)
            .order_by("cliente__nombre", "-id")
        )
        facturas = list(facturas_qs)
        activas = [f for f in facturas if f.estado != Factura.ESTADO_ANULADA]
        paginator = Paginator(facturas, 25)
        page_obj = paginator.get_page(1)
        return render(request, "finanzas/facturas_lista.html", {
            "page_obj": page_obj,
            "q": "",
            "estado": "",
            "anio_filtro": anio,
            "mes_filtro": mes,
            "anio_generacion": anio,
            "mes_generacion": mes,
            "estados": Factura.ESTADO_CHOICES,
            "querystring": f"anio={anio}&mes={mes}",
            "total_facturado": sum((f.total for f in activas), Decimal("0.00")),
            "total_cobrado": sum((f.monto_pagado for f in activas), Decimal("0.00")),
            "total_pendiente": sum((f.saldo for f in activas), Decimal("0.00")),
            "total_vencido": sum((f.saldo for f in activas if f.estado_visual == Factura.ESTADO_VENCIDA), Decimal("0.00")),
            "meses": MESES,
            "vista_previa": vista_previa,
            "total_registros": paginator.count,
            "es_admin": True,
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


@login_required
def cartera_centro(request):
    if not _es_admin(request.user):
        return _denegado(request)

    hoy = timezone.localdate()
    q = (request.GET.get("q") or "").strip()
    estado = (request.GET.get("estado") or "todas").strip()
    ciudad = (request.GET.get("ciudad") or "").strip()
    anio_raw = (request.GET.get("anio") or "").strip()
    mes_raw = (request.GET.get("mes") or "").strip()
    por_pagina_raw = (request.GET.get("por_pagina") or "25").strip()

    try:
        anio = int(anio_raw) if anio_raw else None
        mes = int(mes_raw) if mes_raw else None
        if anio and not 2020 <= anio <= 2100: raise ValueError
        if mes and not 1 <= mes <= 12: raise ValueError
    except (TypeError, ValueError):
        anio = mes = None
        messages.warning(request, "El periodo indicado no es válido.")

    try:
        por_pagina = int(por_pagina_raw)
        if por_pagina not in {25, 50, 100}: raise ValueError
    except (TypeError, ValueError):
        por_pagina = 25

    qs = Factura.objects.select_related("cliente", "contrato").prefetch_related("pagos").all()
    if q:
        qs = qs.filter(Q(cliente__nombre__icontains=q) | Q(cliente__telefono__icontains=q) | Q(numero__icontains=q) | Q(cliente__ciudad__icontains=q))
    if ciudad:
        qs = qs.filter(cliente__ciudad__iexact=ciudad)
    if anio:
        qs = qs.filter(periodo_anio=anio)
    if mes:
        qs = qs.filter(periodo_mes=mes)
    if estado == "pendiente":
        qs = qs.filter(estado=Factura.ESTADO_PENDIENTE, fecha_vencimiento__gte=hoy)
    elif estado == "parcial":
        qs = qs.filter(estado=Factura.ESTADO_PARCIAL, fecha_vencimiento__gte=hoy)
    elif estado == "vencida":
        qs = qs.filter(estado__in=[Factura.ESTADO_PENDIENTE, Factura.ESTADO_PARCIAL, Factura.ESTADO_VENCIDA], fecha_vencimiento__lt=hoy)
    elif estado == "pagada":
        qs = qs.filter(estado=Factura.ESTADO_PAGADA)
    elif estado == "anulada":
        qs = qs.filter(estado=Factura.ESTADO_ANULADA)
    qs = qs.order_by("-periodo_anio", "-periodo_mes", "fecha_vencimiento", "cliente__nombre", "-id")

    facturas_totales = list(qs)
    activas = [f for f in facturas_totales if f.estado != Factura.ESTADO_ANULADA]
    total_por_cobrar = sum((f.saldo for f in activas), Decimal("0.00"))
    vencido = sum((f.saldo for f in activas if f.estado_visual == Factura.ESTADO_VENCIDA), Decimal("0.00"))
    cobrado_mes = PagoFactura.objects.filter(activo=True, fecha__year=hoy.year, fecha__month=hoy.month).aggregate(t=Sum("monto"))["t"] or Decimal("0.00")
    proximas = sum(1 for f in activas if f.saldo > 0 and hoy <= f.fecha_vencimiento <= hoy + timedelta(days=7))

    antiguedad = {"por_vencer": Decimal("0.00"), "dias_1_7": Decimal("0.00"), "dias_8_15": Decimal("0.00"), "dias_16_30": Decimal("0.00"), "mas_30": Decimal("0.00")}
    for factura in activas:
        if factura.saldo <= 0: continue
        dias = (hoy - factura.fecha_vencimiento).days
        if dias <= 0: antiguedad["por_vencer"] += factura.saldo
        elif dias <= 7: antiguedad["dias_1_7"] += factura.saldo
        elif dias <= 15: antiguedad["dias_8_15"] += factura.saldo
        elif dias <= 30: antiguedad["dias_16_30"] += factura.saldo
        else: antiguedad["mas_30"] += factura.saldo

    paginator = Paginator(facturas_totales, por_pagina)
    page_obj = paginator.get_page(request.GET.get("page"))
    params = request.GET.copy(); params.pop("page", None)
    ciudades = Cliente.objects.exclude(ciudad="").values_list("ciudad", flat=True).distinct().order_by("ciudad")

    return render(request, "finanzas/cartera.html", {
        "page_obj": page_obj, "total_registros": paginator.count, "total_por_cobrar": total_por_cobrar,
        "vencido": vencido, "cobrado_mes": cobrado_mes, "proximas": proximas, "antiguedad": antiguedad,
        "q": q, "estado": estado, "ciudad": ciudad, "anio_filtro": anio or "", "mes_filtro": mes or "",
        "por_pagina": por_pagina, "ciudades": ciudades, "meses": MESES, "querystring": params.urlencode(), "es_admin": True,
    })


@login_required
def nomina_lista(request):
    if not _es_admin(request.user): return _denegado(request)
    hoy=timezone.localdate()
    try:
        anio = int(request.GET.get("anio") or hoy.year)
        mes = int(request.GET.get("mes") or hoy.month)
        if mes < 1 or mes > 12 or anio < 2020 or anio > 2100:
            raise ValueError
    except (TypeError, ValueError):
        anio, mes = hoy.year, hoy.month
    qs=ObligacionTrabajador.objects.select_related("trabajador__user","contrato__cliente").prefetch_related("pagos").filter(periodo_anio=anio,periodo_mes=mes)
    trabajador=request.GET.get("trabajador"); estado=request.GET.get("estado")
    if trabajador: qs=qs.filter(trabajador_id=trabajador)
    if estado: qs=qs.filter(estado=estado)
    obligaciones=list(qs); total=sum((o.valor_acordado for o in obligaciones if o.estado!=o.ESTADO_ANULADO),Decimal("0.00")); pagado=sum((o.monto_pagado for o in obligaciones),Decimal("0.00")); pendiente=sum((o.saldo for o in obligaciones),Decimal("0.00"))
    resumen={}
    for o in obligaciones:
        r=resumen.setdefault(o.trabajador_id,{"trabajador_id":o.trabajador_id,"trabajador":o.trabajador,"contratos":0,"generado":Decimal("0"),"pagado":Decimal("0"),"pendiente":Decimal("0")})
        r["contratos"]+=1; r["generado"]+=o.valor_acordado; r["pagado"]+=o.monto_pagado; r["pendiente"]+=o.saldo
    from trabajadores.models import Trabajador
    lotes = LotePagoTrabajador.objects.filter(periodo_anio=anio, periodo_mes=mes, activo=True).select_related("trabajador__user").order_by("-fecha", "-id")[:25]
    return render(request,"finanzas/nomina_lista.html",{"obligaciones":obligaciones,"resumen":list(resumen.values()),"total":total,"pagado":pagado,"pendiente":pendiente,"anio":anio,"mes":mes,"meses":MESES,"trabajadores":Trabajador.objects.filter(activo=True).select_related("user"),"trabajador_id":trabajador,"estado":estado,"estados":ObligacionTrabajador.ESTADO_CHOICES,"lotes":lotes,"es_admin":True})

def _fecha_pago_programada_contrato(contrato, anio, mes):
    """Calcula la fecha de nómina según la regla configurada para el trabajador."""
    trabajador = contrato.tecnico_designado
    periodo_inicio, periodo_fin = contrato.periodo_servicio(anio, mes)
    if trabajador and trabajador.programacion_pago_nomina == "fin_periodo":
        return periodo_fin + timedelta(days=trabajador.dias_despues_fin_periodo or 0)
    if trabajador and trabajador.programacion_pago_nomina == "dia_fijo" and trabajador.dia_pago_nomina:
        return date(anio, mes, min(trabajador.dia_pago_nomina, monthrange(anio, mes)[1]))
    if trabajador and trabajador.programacion_pago_nomina == "rango" and trabajador.dia_pago_hasta:
        return date(anio, mes, min(trabajador.dia_pago_hasta, monthrange(anio, mes)[1]))
    factura = (
        Factura.objects
        .filter(contrato=contrato, periodo_anio=anio, periodo_mes=mes)
        .only("fecha_vencimiento")
        .first()
    )
    if factura and factura.fecha_vencimiento:
        return factura.fecha_vencimiento
    # Mantiene la regla actual de cobro: emisión el día 1 y vencimiento 5 días después.
    return date(anio, mes, 1) + timedelta(days=5)


@login_required
def nomina_generar(request):
    if not _es_admin(request.user): return _denegado(request)
    if request.method!="POST": return redirect("finanzas_nomina")
    hoy=timezone.localdate()
    try:
        anio = int(request.POST.get("anio") or hoy.year)
        mes = int(request.POST.get("mes") or hoy.month)
        if mes < 1 or mes > 12 or anio < 2020 or anio > 2100:
            raise ValueError
    except (TypeError, ValueError):
        messages.error(request, "Periodo inválido. Selecciona correctamente el mes y el año.")
        return redirect("finanzas_nomina")
    creadas=0; omitidas=0; sin_configurar=0
    for c in Contrato.objects.filter(activo=True).select_related("tecnico_designado"):
        if not c.tecnico_designado_id or not c.valor_tecnico_mensual or c.valor_tecnico_mensual<=0:
            sin_configurar+=1; continue
        fecha_programada = _fecha_pago_programada_contrato(c, anio, mes)
        periodo_inicio, periodo_fin = c.periodo_servicio(anio, mes)
        obligacion, created = ObligacionTrabajador.objects.get_or_create(
            contrato=c,
            periodo_anio=anio,
            periodo_mes=mes,
            defaults={
                "trabajador": c.tecnico_designado,
                "valor_acordado": c.valor_tecnico_mensual,
                "periodo_servicio_inicio": periodo_inicio,
                "periodo_servicio_fin": periodo_fin,
                "fecha_pago_programada": fecha_programada,
            },
        )
        campos_actualizados = []
        if not created and obligacion.fecha_pago_programada != fecha_programada:
            obligacion.fecha_pago_programada = fecha_programada
            campos_actualizados.append("fecha_pago_programada")
        # Solo se completan fechas históricas faltantes. Nunca se reescribe un periodo ya guardado.
        if not obligacion.periodo_servicio_inicio:
            obligacion.periodo_servicio_inicio = periodo_inicio
            campos_actualizados.append("periodo_servicio_inicio")
        if not obligacion.periodo_servicio_fin:
            obligacion.periodo_servicio_fin = periodo_fin
            campos_actualizados.append("periodo_servicio_fin")
        if campos_actualizados:
            obligacion.save(update_fields=campos_actualizados + ["actualizada_en"])
        creadas += int(created); omitidas += int(not created)

    # Los anticipos pendientes del periodo se descuentan automáticamente de la nómina
    # sin crear un segundo egreso: se reutiliza el egreso generado al registrar el anticipo.
    anticipos_aplicados = 0
    for anticipo in AnticipoTrabajador.objects.filter(
        periodo_anio=anio, periodo_mes=mes, descontado=False
    ).select_related("trabajador", "egreso"):
        obligaciones_trabajador = list(
            ObligacionTrabajador.objects.filter(
                trabajador=anticipo.trabajador,
                periodo_anio=anio,
                periodo_mes=mes,
            )
            .exclude(estado=ObligacionTrabajador.ESTADO_ANULADO)
            .prefetch_related("pagos")
            .order_by("fecha_pago_programada", "id")
        )
        restante = anticipo.saldo_pendiente
        if not obligaciones_trabajador or restante <= 0:
            continue
        monto_aplicar = min(restante, sum((o.saldo for o in obligaciones_trabajador), Decimal("0.00")))
        if monto_aplicar <= 0:
            continue
        with transaction.atomic():
            lote = LotePagoTrabajador.objects.create(
                trabajador=anticipo.trabajador,
                periodo_anio=anio,
                periodo_mes=mes,
                monto=monto_aplicar,
                fecha=anticipo.fecha,
                metodo_pago="transferencia",
                referencia=f"ANT-{anticipo.pk}",
                observaciones=f"Descuento automático del anticipo #{anticipo.pk}",
                egreso=anticipo.egreso,
                creado_por=anticipo.creado_por,
            )
            for obligacion in obligaciones_trabajador:
                if restante <= 0:
                    break
                aplicado = min(restante, obligacion.saldo)
                if aplicado <= 0:
                    continue
                PagoTrabajador.objects.create(
                    lote=lote,
                    obligacion=obligacion,
                    monto=aplicado,
                    fecha=anticipo.fecha,
                    metodo_pago="transferencia",
                    referencia=f"ANT-{anticipo.pk}",
                    observaciones=f"Anticipo #{anticipo.pk} descontado de la nómina",
                    creado_por=anticipo.creado_por,
                )
                restante -= aplicado
            aplicado_total = monto_aplicar - restante
            if aplicado_total > 0:
                anticipo.monto_descontado += aplicado_total
                anticipo.descontado = anticipo.monto_descontado >= anticipo.monto
                anticipo.fecha_descuento = timezone.localdate() if anticipo.descontado else None
                anticipo.save(update_fields=["monto_descontado", "descontado", "fecha_descuento"])
                anticipos_aplicados += 1
    messages.success(request,f"Nómina generada: {creadas} obligaciones nuevas, {omitidas} ya existentes, {sin_configurar} contratos sin técnico o valor configurado y {anticipos_aplicados} anticipos descontados.")
    return redirect(f"/dashboard/finanzas/nomina/?anio={anio}&mes={mes}")

def _nombre_trabajador(trabajador):
    nombre = trabajador.user.get_full_name().strip()
    return nombre or trabajador.user.username


def _pie_pagina(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.drawString(18 * mm, 12 * mm, "JVAQUA - Resumen de nómina operativa")
    canvas.drawRightString(192 * mm, 12 * mm, f"Página {doc.page}")
    canvas.restoreState()



@login_required
def trabajador_configuracion_pago(request, trabajador_pk):
    if not _es_admin(request.user):
        return _denegado(request)
    from trabajadores.models import Trabajador
    trabajador = get_object_or_404(Trabajador.objects.select_related("user"), pk=trabajador_pk)
    hoy = timezone.localdate()
    if request.method == "POST":
        accion = request.POST.get("accion", "guardar")
        if accion == "anticipo":
            try:
                monto = Decimal(request.POST.get("monto_anticipo", "0"))
                if monto <= 0:
                    raise ValueError
                anticipo = AnticipoTrabajador.objects.create(
                    trabajador=trabajador,
                    monto=monto,
                    fecha=request.POST.get("fecha_anticipo") or hoy,
                    periodo_anio=int(request.POST.get("periodo_anio") or hoy.year),
                    periodo_mes=int(request.POST.get("periodo_mes") or hoy.month),
                    observaciones=request.POST.get("observaciones_anticipo", "").strip(),
                    creado_por=request.user,
                )
                anticipo.crear_egreso()
                messages.success(request, f"Anticipo de ${monto:.2f} registrado para {trabajador}.")
            except (ValueError, TypeError):
                messages.error(request, "El valor del anticipo no es válido.")
        else:
            trabajador.forma_pago_nomina = request.POST.get("forma_pago_nomina", "fin_mes")
            trabajador.programacion_pago_nomina = request.POST.get("programacion_pago_nomina", "fecha_contratos")
            trabajador.modalidad_pago_nomina = request.POST.get("modalidad_pago_nomina", "unico")
            def entero_dia(nombre):
                valor = request.POST.get(nombre, "").strip()
                if not valor:
                    return None
                try:
                    return max(1, min(31, int(valor)))
                except ValueError:
                    return None
            trabajador.dia_pago_nomina = entero_dia("dia_pago_nomina")
            trabajador.dia_pago_desde = entero_dia("dia_pago_desde")
            trabajador.dia_pago_hasta = entero_dia("dia_pago_hasta")
            trabajador.segundo_dia_pago = entero_dia("segundo_dia_pago")
            try:
                trabajador.dias_despues_fin_periodo = max(
                    0,
                    min(90, int(request.POST.get("dias_despues_fin_periodo") or 0)),
                )
            except (TypeError, ValueError):
                trabajador.dias_despues_fin_periodo = 0
            trabajador.observaciones_pago = request.POST.get("observaciones_pago", "").strip()
            trabajador.save()

            # Reprograma solamente obligaciones pendientes y sin pagos, conservando el historial pagado.
            obligaciones_pendientes = trabajador.obligaciones_pago.filter(
                estado=ObligacionTrabajador.ESTADO_PENDIENTE,
                pagos__isnull=True,
            ).select_related("contrato").distinct()
            for obligacion in obligaciones_pendientes:
                if trabajador.programacion_pago_nomina == "fin_periodo" and obligacion.periodo_servicio_fin:
                    nueva_fecha = obligacion.periodo_servicio_fin + timedelta(
                        days=trabajador.dias_despues_fin_periodo or 0
                    )
                else:
                    nueva_fecha = _fecha_pago_programada_contrato(
                        obligacion.contrato,
                        obligacion.periodo_anio,
                        obligacion.periodo_mes,
                    )
                if obligacion.fecha_pago_programada != nueva_fecha:
                    obligacion.fecha_pago_programada = nueva_fecha
                    obligacion.save(update_fields=["fecha_pago_programada", "actualizada_en"])

            messages.success(request, "Configuración de pago actualizada correctamente.")
        return redirect("finanzas_trabajador_configuracion_pago", trabajador_pk=trabajador.pk)
    anticipos = trabajador.anticipos.select_related("egreso").all()[:30]
    return render(request, "finanzas/trabajador_configuracion_pago.html", {
        "trabajador": trabajador,
        "anticipos": anticipos,
        "hoy": hoy,
        "es_admin": True,
    })


@login_required
def nomina_pago_consolidado(request, trabajador_pk):
    if not _es_admin(request.user):
        return _denegado(request)
    from trabajadores.models import Trabajador
    trabajador = get_object_or_404(Trabajador.objects.select_related("user"), pk=trabajador_pk)
    hoy = timezone.localdate()
    try:
        anio = int(request.GET.get("anio") or request.POST.get("anio") or hoy.year)
        mes = int(request.GET.get("mes") or request.POST.get("mes") or hoy.month)
        if mes < 1 or mes > 12:
            raise ValueError
    except (TypeError, ValueError):
        anio, mes = hoy.year, hoy.month
    obligaciones = list(ObligacionTrabajador.objects.filter(
        trabajador=trabajador, periodo_anio=anio, periodo_mes=mes
    ).exclude(estado=ObligacionTrabajador.ESTADO_ANULADO).select_related("contrato__cliente").prefetch_related("pagos").order_by("fecha_pago_programada", "id"))
    saldo_total = sum((o.saldo for o in obligaciones), Decimal("0.00"))
    if saldo_total <= 0:
        messages.info(request, "Este trabajador no tiene saldo pendiente en el periodo seleccionado.")
        return redirect(f"/dashboard/finanzas/nomina/?anio={anio}&mes={mes}")
    form = PagoConsolidadoTrabajadorForm(request.POST or None, request.FILES or None, saldo_total=saldo_total)
    if request.method == "POST" and form.is_valid():
        restante = form.cleaned_data["monto"]
        with transaction.atomic():
            lote = LotePagoTrabajador.objects.create(
                trabajador=trabajador, periodo_anio=anio, periodo_mes=mes, monto=restante,
                fecha=form.cleaned_data["fecha"], metodo_pago=form.cleaned_data["metodo_pago"],
                referencia=form.cleaned_data.get("referencia", ""), comprobante=form.cleaned_data.get("comprobante"),
                observaciones=form.cleaned_data.get("observaciones", ""), creado_por=request.user,
            )
            lote.crear_egreso()
            for obligacion in obligaciones:
                if restante <= 0:
                    break
                aplicado = min(restante, obligacion.saldo)
                if aplicado <= 0:
                    continue
                PagoTrabajador.objects.create(
                    lote=lote, obligacion=obligacion, monto=aplicado, fecha=lote.fecha,
                    metodo_pago=lote.metodo_pago, referencia=lote.referencia,
                    observaciones=f"Distribución del pago consolidado #{lote.pk}", creado_por=request.user,
                )
                restante -= aplicado
        messages.success(request, f"Pago consolidado de ${lote.monto:.2f} registrado para {trabajador}.")
        return redirect(f"/dashboard/finanzas/nomina/?anio={anio}&mes={mes}")
    return render(request, "finanzas/pago_trabajador_consolidado_form.html", {
        "form": form, "trabajador": trabajador, "obligaciones": obligaciones,
        "saldo_total": saldo_total, "anio": anio, "mes": mes, "es_admin": True,
    })


@login_required
def nomina_pago_consolidado_pdf(request, lote_pk):
    lote = get_object_or_404(LotePagoTrabajador.objects.select_related("trabajador__user"), pk=lote_pk, activo=True)
    es_propietario = hasattr(request.user, "trabajador") and request.user.trabajador.pk == lote.trabajador_id
    if not _es_admin(request.user) and not es_propietario:
        return _denegado(request)
    pagos = lote.distribuciones.filter(activo=True).select_related("obligacion__contrato__cliente")
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="pago-consolidado-{lote.pk}.pdf"'
    doc = SimpleDocTemplate(response, pagesize=A4, rightMargin=18*mm, leftMargin=18*mm, topMargin=18*mm, bottomMargin=18*mm)
    styles = getSampleStyleSheet()
    story = [Paragraph("JVAQUA - COMPROBANTE DE PAGO CONSOLIDADO", styles["Title"]), Spacer(1, 8),
             Paragraph(f"Trabajador: <b>{lote.trabajador}</b>", styles["Normal"]),
             Paragraph(f"Periodo: <b>{lote.periodo_label}</b>", styles["Normal"]),
             Paragraph(f"Fecha: <b>{lote.fecha.strftime('%d/%m/%Y')}</b>", styles["Normal"]),
             Paragraph(f"Valor total: <b>${lote.monto:.2f}</b>", styles["Normal"]), Spacer(1, 10)]
    data=[["Cliente / contrato", "Periodo de servicio", "Valor aplicado"]]
    for pago in pagos:
        data.append([
            str(pago.obligacion.contrato.cliente),
            pago.obligacion.periodo_servicio_label,
            f"${pago.monto:.2f}",
        ])
    table=Table(data, colWidths=[72*mm,58*mm,30*mm])
    table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0B5ED7")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.4,colors.HexColor("#CBD5E1")),("PADDING",(0,0),(-1,-1),7),("ALIGN",(2,1),(2,-1),"RIGHT")]))
    story += [table, Spacer(1, 18), Paragraph(f"Forma de pago: {lote.get_metodo_pago_display()}", styles["Normal"]), Paragraph(f"Referencia: {lote.referencia or '—'}", styles["Normal"])]
    doc.build(story)
    return response


@login_required
def nomina_trabajador_pdf(request, trabajador_pk):
    es_propietario = hasattr(request.user, "trabajador") and request.user.trabajador.pk == trabajador_pk
    if not _es_admin(request.user) and not es_propietario:
        return _denegado(request)

    hoy = timezone.localdate()
    try:
        anio = int(request.GET.get("anio") or hoy.year)
        mes = int(request.GET.get("mes") or hoy.month)
        if mes < 1 or mes > 12 or anio < 2020 or anio > 2100:
            raise ValueError
    except (TypeError, ValueError):
        anio, mes = hoy.year, hoy.month

    from trabajadores.models import Trabajador
    trabajador = get_object_or_404(Trabajador.objects.select_related("user"), pk=trabajador_pk)
    obligaciones = list(
        ObligacionTrabajador.objects
        .select_related("contrato__cliente", "trabajador__user")
        .prefetch_related("pagos")
        .filter(trabajador=trabajador, periodo_anio=anio, periodo_mes=mes)
        .order_by("contrato__cliente__nombre", "id")
    )

    generado = sum((o.valor_acordado for o in obligaciones if o.estado != o.ESTADO_ANULADO), Decimal("0.00"))
    pagado = sum((o.monto_pagado for o in obligaciones), Decimal("0.00"))
    pendiente = sum((o.saldo for o in obligaciones), Decimal("0.00"))

    nombre = _nombre_trabajador(trabajador)
    filename = f"nomina-{slugify(nombre) or trabajador.pk}-{anio}-{mes:02d}.pdf"
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=20 * mm,
        title=f"Nómina {nombre} {mes:02d}/{anio}",
        author="JVAQUA",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TituloJVA", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=colors.HexColor("#0F4C81"), alignment=TA_CENTER, spaceAfter=4 * mm))
    styles.add(ParagraphStyle(name="SubtituloJVA", parent=styles["Normal"], fontName="Helvetica", fontSize=10, leading=14, textColor=colors.HexColor("#475569"), alignment=TA_CENTER, spaceAfter=7 * mm))
    styles.add(ParagraphStyle(name="Celda", parent=styles["Normal"], fontSize=8.5, leading=11))
    styles.add(ParagraphStyle(name="CeldaDerecha", parent=styles["Normal"], fontSize=8.5, leading=11, alignment=TA_RIGHT))

    nombre_mes = dict(MESES).get(mes, str(mes))
    story = [
        Paragraph("JVAQUA", styles["TituloJVA"]),
        Paragraph("RESUMEN INDIVIDUAL DE NÓMINA OPERATIVA", styles["Heading2"]),
        Paragraph(f"Trabajador: <b>{nombre}</b><br/>Nómina generada: <b>{nombre_mes} {anio}</b><br/>Fecha de emisión: {hoy.strftime('%d/%m/%Y')}", styles["SubtituloJVA"]),
    ]

    resumen_data = [
        ["Contratos", "Total generado", "Total pagado", "Saldo pendiente"],
        [str(len(obligaciones)), f"${generado:.2f}", f"${pagado:.2f}", f"${pendiente:.2f}"],
    ]
    resumen_tabla = Table(resumen_data, colWidths=[38 * mm, 46 * mm, 46 * mm, 46 * mm])
    resumen_tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F4C81")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#EAF3FA")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.extend([resumen_tabla, Spacer(1, 7 * mm), Paragraph("Detalle por contrato", styles["Heading2"]), Spacer(1, 2 * mm)])

    detalle = [["#", "Cliente / Contrato", "Periodo de servicio", "Fecha de pago", "Valor", "Pagado", "Saldo", "Estado"]]
    for i, o in enumerate(obligaciones, 1):
        cliente = str(o.contrato.cliente)
        detalle.append([
            str(i),
            Paragraph(cliente, styles["Celda"]),
            Paragraph(o.periodo_servicio_label, styles["Celda"]),
            o.fecha_pago_programada.strftime("%d/%m/%Y"),
            Paragraph(f"${o.valor_acordado:.2f}", styles["CeldaDerecha"]),
            Paragraph(f"${o.monto_pagado:.2f}", styles["CeldaDerecha"]),
            Paragraph(f"${o.saldo:.2f}", styles["CeldaDerecha"]),
            o.get_estado_display(),
        ])
    if not obligaciones:
        detalle.append(["", Paragraph("No existen obligaciones generadas para este trabajador en el periodo seleccionado.", styles["Celda"]), "", "", "", "", "", ""])

    tabla = Table(detalle, repeatRows=1, colWidths=[6 * mm, 42 * mm, 39 * mm, 23 * mm, 18 * mm, 18 * mm, 18 * mm, 22 * mm])
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#163A5F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (3, 1), (3, -1), "CENTER"),
        ("ALIGN", (4, 1), (6, -1), "RIGHT"),
        ("ALIGN", (7, 1), (7, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(tabla)

    pagos_activos = []
    for o in obligaciones:
        for pago in o.pagos.all():
            if pago.activo:
                pagos_activos.append((pago, o))
    if pagos_activos:
        story.extend([Spacer(1, 7 * mm), Paragraph("Pagos registrados", styles["Heading2"]), Spacer(1, 2 * mm)])
        pagos_data = [["Fecha", "Cliente", "Método", "Referencia", "Monto"]]
        for pago, obligacion in sorted(pagos_activos, key=lambda x: (x[0].fecha, x[0].pk)):
            pagos_data.append([
                pago.fecha.strftime("%d/%m/%Y"),
                Paragraph(str(obligacion.contrato.cliente), styles["Celda"]),
                pago.get_metodo_pago_display(),
                Paragraph(pago.referencia or "-", styles["Celda"]),
                Paragraph(f"${pago.monto:.2f}", styles["CeldaDerecha"]),
            ])
        pagos_table = Table(pagos_data, repeatRows=1, colWidths=[25 * mm, 61 * mm, 30 * mm, 40 * mm, 25 * mm])
        pagos_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F766E")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.2),
            ("ALIGN", (4, 1), (4, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0FDFA")]),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(pagos_table)

    story.extend([
        Spacer(1, 10 * mm),
        Paragraph("Este documento resume las obligaciones generadas y los pagos registrados en el sistema para el periodo indicado.", styles["Normal"]),
        Spacer(1, 13 * mm),
        Table([["______________________________", "______________________________"], ["Responsable JVAQUA", "Trabajador"]], colWidths=[85 * mm, 85 * mm], style=TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("FONTSIZE", (0, 0), (-1, -1), 9), ("TOPPADDING", (0, 1), (-1, 1), 5)])),
    ])

    doc.build(story, onFirstPage=_pie_pagina, onLaterPages=_pie_pagina)
    return response


@login_required
def nomina_detalle(request,pk):
    if not _es_admin(request.user): return _denegado(request)
    o=get_object_or_404(ObligacionTrabajador.objects.select_related("trabajador__user","contrato__cliente").prefetch_related("pagos__egreso"),pk=pk)
    return render(request,"finanzas/nomina_detalle.html",{"obligacion":o,"es_admin":True})

@login_required
def nomina_pago_nuevo(request,pk):
    if not _es_admin(request.user): return _denegado(request)
    o=get_object_or_404(ObligacionTrabajador,pk=pk)
    if o.estado==o.ESTADO_ANULADO or o.saldo<=0: messages.warning(request,"Esta obligación no admite nuevos pagos."); return redirect("finanzas_nomina_detalle",pk=pk)
    form=PagoTrabajadorForm(request.POST or None,request.FILES or None,obligacion=o)
    if request.method=="POST" and form.is_valid():
        pago=form.save(commit=False); pago.obligacion=o; pago.creado_por=request.user; pago.save(); messages.success(request,"Pago registrado y egreso creado automáticamente."); return redirect("finanzas_nomina_detalle",pk=pk)
    return render(request,"finanzas/pago_trabajador_form.html",{"form":form,"obligacion":o,"es_admin":True})

@login_required
def nomina_pago_anular(request,pk,pago_pk):
    if not _es_admin(request.user): return _denegado(request)
    o=get_object_or_404(ObligacionTrabajador,pk=pk); pago=get_object_or_404(PagoTrabajador,pk=pago_pk,obligacion=o)
    if request.method=="POST": pago.anular(); messages.success(request,"Pago y egreso vinculados anulados.")
    return redirect("finanzas_nomina_detalle",pk=pk)


def _pdf_response(nombre_archivo, titulo, subtitulo, filas, encabezados, resumen=None):
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{nombre_archivo}"'
    doc = SimpleDocTemplate(response, pagesize=A4, rightMargin=14*mm, leftMargin=14*mm, topMargin=14*mm, bottomMargin=14*mm)
    estilos = getSampleStyleSheet()
    elementos = [Paragraph(titulo, ParagraphStyle("TituloJVA", parent=estilos["Title"], alignment=TA_CENTER, fontSize=17)), Paragraph(subtitulo, ParagraphStyle("SubJVA", parent=estilos["Normal"], alignment=TA_CENTER, textColor=colors.HexColor("#5b6472"))), Spacer(1, 7*mm)]
    if resumen:
        datos = [[Paragraph(str(k), estilos["BodyText"]), Paragraph(str(v), estilos["BodyText"])] for k,v in resumen]
        tabla = Table(datos, colWidths=[70*mm, 80*mm]); tabla.setStyle(TableStyle([("BACKGROUND",(0,0),(0,-1),colors.HexColor("#eef4fb")),("GRID",(0,0),(-1,-1),0.25,colors.HexColor("#cbd5e1")),("PADDING",(0,0),(-1,-1),6)])); elementos += [tabla, Spacer(1, 6*mm)]
    data = [[Paragraph(str(x), estilos["BodyText"]) for x in encabezados]] + [[Paragraph(str(x), estilos["BodyText"]) for x in fila] for fila in filas]
    tabla = Table(data, repeatRows=1)
    tabla.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#123b66")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),0.25,colors.HexColor("#cbd5e1")),("VALIGN",(0,0),(-1,-1),"TOP"),("PADDING",(0,0),(-1,-1),5)]))
    elementos.append(tabla); doc.build(elementos); return response


@login_required
def cliente_estado_cuenta_pdf(request, cliente_pk):
    if not _es_admin(request.user): return _denegado(request)
    cliente = get_object_or_404(Cliente, pk=cliente_pk)
    facturas = list(Factura.objects.filter(cliente=cliente).prefetch_related("pagos").order_by("-periodo_anio", "-periodo_mes"))
    filas = [(f.numero, f.periodo_label, f.fecha_vencimiento.strftime("%d/%m/%Y"), f"${f.total:.2f}", f"${f.monto_pagado:.2f}", f"${f.saldo:.2f}", f.estado_visual.title()) for f in facturas]
    activas=[f for f in facturas if f.estado != Factura.ESTADO_ANULADA]
    resumen=[("Cliente", cliente.nombre),("Teléfono", cliente.telefono or "—"),("Total facturado", f"${sum((f.total for f in activas), Decimal('0')):.2f}"),("Total cobrado", f"${sum((f.monto_pagado for f in activas), Decimal('0')):.2f}"),("Saldo pendiente", f"${sum((f.saldo for f in activas), Decimal('0')):.2f}")]
    return _pdf_response(f"estado-cuenta-{slugify(cliente.nombre)}.pdf", "JVAQUA · Estado de cuenta", "Historial financiero del cliente", filas, ["Factura","Periodo","Vence","Total","Cobrado","Saldo","Estado"], resumen)


@login_required
def pago_factura_comprobante_pdf(request, pago_pk):
    if not _es_admin(request.user): return _denegado(request)
    pago=get_object_or_404(PagoFactura.objects.select_related("factura__cliente", "factura__contrato"), pk=pago_pk)
    f=pago.factura
    resumen=[("Comprobante", f"REC-{pago.pk:06d}"),("Cliente", f.cliente.nombre),("Factura", f.numero),("Periodo", f.periodo_label),("Fecha", pago.fecha.strftime("%d/%m/%Y")),("Forma de pago", pago.get_metodo_pago_display()),("Referencia", pago.referencia or "—"),("Valor recibido", f"${pago.monto:.2f}"),("Saldo actual", f"${f.saldo:.2f}")]
    return _pdf_response(f"recibo-{pago.pk:06d}.pdf", "JVAQUA · Comprobante de pago", "Cobro de servicio de mantenimiento", [], ["Detalle"], resumen)


@login_required
def pago_trabajador_comprobante_pdf(request, pago_pk):
    if not _es_admin(request.user): return _denegado(request)
    pago=get_object_or_404(PagoTrabajador.objects.select_related("obligacion__trabajador", "obligacion__contrato__cliente"), pk=pago_pk)
    o=pago.obligacion
    resumen=[("Comprobante", f"PAG-{pago.pk:06d}"),("Trabajador", str(o.trabajador)),("Cliente / contrato", str(o.contrato.cliente)),("Periodo", o.periodo_label),("Fecha", pago.fecha.strftime("%d/%m/%Y")),("Forma de pago", pago.get_metodo_pago_display()),("Referencia", pago.referencia or "—"),("Valor pagado", f"${pago.monto:.2f}"),("Saldo actual", f"${o.saldo:.2f}")]
    return _pdf_response(f"pago-trabajador-{pago.pk:06d}.pdf", "JVAQUA · Comprobante de pago", "Pago operativo a trabajador", [], ["Detalle"], resumen)


@login_required
def calendario_financiero(request):
    if not _es_admin(request.user): return _denegado(request)
    hoy=timezone.localdate()
    try:
        anio=int(request.GET.get("anio", hoy.year)); mes=int(request.GET.get("mes", hoy.month)); assert 1 <= mes <= 12
    except Exception: anio,mes=hoy.year,hoy.month
    inicio,fin=_rango_mes(anio,mes)
    eventos=[]
    for f in Factura.objects.filter(fecha_vencimiento__range=(inicio,fin)).exclude(estado=Factura.ESTADO_ANULADA).select_related("cliente"):
        eventos.append({"fecha":f.fecha_vencimiento,"tipo":"Cobro programado","detalle":f.cliente.nombre,"valor":f.saldo,"estado":f.estado_visual})
    for o in ObligacionTrabajador.objects.filter(fecha_pago_programada__range=(inicio,fin)).exclude(estado=ObligacionTrabajador.ESTADO_ANULADO).select_related("trabajador","contrato__cliente"):
        eventos.append({"fecha":o.fecha_pago_programada,"tipo":"Pago a trabajador","detalle":f"{o.trabajador} · {o.contrato.cliente}","valor":o.saldo,"estado":o.estado})
    for i in Ingreso.objects.filter(fecha__range=(inicio,fin)).exclude(estado=Ingreso.ESTADO_ANULADO): eventos.append({"fecha":i.fecha,"tipo":"Ingreso realizado","detalle":i.concepto,"valor":i.monto_pagado,"estado":"pagado"})
    for e in Egreso.objects.filter(fecha__range=(inicio,fin)).exclude(estado=Egreso.ESTADO_ANULADO): eventos.append({"fecha":e.fecha,"tipo":"Egreso realizado","detalle":e.concepto,"valor":e.monto_pagado,"estado":"pagado"})
    eventos.sort(key=lambda x:(x["fecha"],x["tipo"],x["detalle"]))
    return render(request,"finanzas/calendario.html",{"eventos":eventos,"anio":anio,"mes":mes,"meses":MESES,"es_admin":True})
