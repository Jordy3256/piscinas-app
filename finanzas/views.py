from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.urls import reverse
from django.utils.text import slugify

from .forms import EgresoForm, IngresoForm, PagoFacturaForm, PagoTrabajadorForm
from .models import Egreso, Factura, Ingreso, PagoFactura, ObligacionTrabajador, PagoTrabajador
from clientes.models import Cliente
from contratos.models import Contrato

from .cuentas_por_cobrar import MESES, generar_facturas_periodo, previsualizar_facturas_periodo

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


@login_required
def cartera_centro(request):
    if not _es_admin(request.user): return _denegado(request)
    hoy = timezone.localdate()
    q=(request.GET.get("q") or "").strip(); estado=(request.GET.get("estado") or "").strip(); ciudad=(request.GET.get("ciudad") or "").strip()
    qs=Factura.objects.select_related("cliente","contrato").prefetch_related("pagos").exclude(estado=Factura.ESTADO_ANULADA)
    if q: qs=qs.filter(Q(cliente__nombre__icontains=q)|Q(cliente__telefono__icontains=q)|Q(numero__icontains=q))
    if ciudad: qs=qs.filter(cliente__ciudad__icontains=ciudad)
    facturas=list(qs)
    if estado: facturas=[f for f in facturas if f.estado_visual==estado]
    total_por_cobrar=sum((f.saldo for f in facturas),Decimal("0.00")); vencido=sum((f.saldo for f in facturas if f.estado_visual==Factura.ESTADO_VENCIDA),Decimal("0.00"))
    cobrado_mes=PagoFactura.objects.filter(activo=True,fecha__year=hoy.year,fecha__month=hoy.month).aggregate(t=Sum("monto"))["t"] or Decimal("0.00")
    proximas=sum(1 for f in facturas if f.saldo>0 and f.fecha_vencimiento>=hoy and f.fecha_vencimiento<=hoy+timedelta(days=7))
    paginator=Paginator(facturas,25); page_obj=paginator.get_page(request.GET.get("page"))
    ciudades=Cliente.objects.exclude(ciudad="").values_list("ciudad",flat=True).distinct().order_by("ciudad")
    return render(request,"finanzas/cartera.html",{"page_obj":page_obj,"total_por_cobrar":total_por_cobrar,"vencido":vencido,"cobrado_mes":cobrado_mes,"proximas":proximas,"q":q,"estado":estado,"ciudad":ciudad,"ciudades":ciudades,"es_admin":True})

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
    return render(request,"finanzas/nomina_lista.html",{"obligaciones":obligaciones,"resumen":list(resumen.values()),"total":total,"pagado":pagado,"pendiente":pendiente,"anio":anio,"mes":mes,"meses":MESES,"trabajadores":Trabajador.objects.filter(activo=True).select_related("user"),"trabajador_id":trabajador,"estado":estado,"estados":ObligacionTrabajador.ESTADO_CHOICES,"es_admin":True})

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
        _,created=ObligacionTrabajador.objects.get_or_create(contrato=c,periodo_anio=anio,periodo_mes=mes,defaults={"trabajador":c.tecnico_designado,"valor_acordado":c.valor_tecnico_mensual})
        creadas += int(created); omitidas += int(not created)
    messages.success(request,f"Nómina generada: {creadas} obligaciones nuevas, {omitidas} ya existentes y {sin_configurar} contratos sin técnico o valor configurado.")
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
def nomina_trabajador_pdf(request, trabajador_pk):
    if not _es_admin(request.user):
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
        Paragraph(f"Trabajador: <b>{nombre}</b><br/>Periodo: <b>{nombre_mes} {anio}</b><br/>Fecha de emisión: {hoy.strftime('%d/%m/%Y')}", styles["SubtituloJVA"]),
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

    detalle = [["#", "Cliente / Contrato", "Valor", "Pagado", "Saldo", "Estado"]]
    for i, o in enumerate(obligaciones, 1):
        cliente = str(o.contrato.cliente)
        detalle.append([
            str(i),
            Paragraph(cliente, styles["Celda"]),
            Paragraph(f"${o.valor_acordado:.2f}", styles["CeldaDerecha"]),
            Paragraph(f"${o.monto_pagado:.2f}", styles["CeldaDerecha"]),
            Paragraph(f"${o.saldo:.2f}", styles["CeldaDerecha"]),
            o.get_estado_display(),
        ])
    if not obligaciones:
        detalle.append(["", Paragraph("No existen obligaciones generadas para este trabajador en el periodo seleccionado.", styles["Celda"]), "", "", "", ""])

    tabla = Table(detalle, repeatRows=1, colWidths=[9 * mm, 73 * mm, 25 * mm, 25 * mm, 25 * mm, 24 * mm])
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#163A5F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 1), (4, -1), "RIGHT"),
        ("ALIGN", (5, 1), (5, -1), "CENTER"),
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
