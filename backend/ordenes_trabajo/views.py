from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from contratos.models import Contrato
from dashboard.models import ActividadSistema, Notificacion
from trabajadores.models import Trabajador

from .forms import OrdenTrabajoForm
from .models import FotoOrdenTrabajo, OrdenTrabajo, TipoOrdenTrabajo


def _es_admin(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    grupos = {g.name.strip().lower() for g in user.groups.all()}
    return bool({"administradores", "administrador", "admins", "adimistradores"} & grupos)


def _es_trabajador(user):
    if not user.is_authenticated:
        return False
    grupos = {g.name.strip().lower() for g in user.groups.all()}
    return "trabajadores" in grupos or "trabajador" in grupos


def _normalizar_whatsapp(telefono):
    digitos = "".join(ch for ch in str(telefono or "") if ch.isdigit())
    if digitos.startswith("00"):
        digitos = digitos[2:]
    if digitos.startswith("593"):
        return digitos
    if digitos.startswith("0") and len(digitos) >= 9:
        return "593" + digitos[1:]
    return digitos


def _registrar(user, titulo, descripcion, url=""):
    try:
        ActividadSistema.objects.create(user=user, titulo=titulo, descripcion=descripcion, url=url)
    except Exception:
        pass


def _notificar_trabajador(orden, titulo, mensaje):
    try:
        Notificacion.objects.create(
            user=orden.trabajador.user,
            titulo=titulo,
            mensaje=mensaje,
            url=f"/dashboard/ordenes/{orden.pk}/",
            tipo="general",
            referencia_id=None,
        )
    except Exception:
        pass


@login_required
def orden_list_view(request):
    if not _es_admin(request.user):
        return render(request, "dashboard/no_autorizado.html", status=403)
    hoy = timezone.localdate()
    estado = (request.GET.get("estado") or "").strip()
    q = (request.GET.get("q") or "").strip()
    qs = OrdenTrabajo.objects.select_related("tipo", "trabajador__user", "cliente", "contrato").all()
    if estado:
        qs = qs.filter(estado=estado)
    if q:
        qs = qs.filter(Q(nombre_contacto__icontains=q) | Q(titulo__icontains=q) | Q(telefono__icontains=q) | Q(direccion__icontains=q))
    return render(request, "ordenes_trabajo/orden_list.html", {
        "ordenes": qs.order_by("fecha", "hora", "id")[:250],
        "estado": estado,
        "q": q,
        "hoy": hoy,
        "pendientes": OrdenTrabajo.objects.filter(estado="pendiente").count(),
        "hoy_count": OrdenTrabajo.objects.filter(fecha=hoy).exclude(estado="cancelada").count(),
        "completadas_mes": OrdenTrabajo.objects.filter(estado="completada", fecha__year=hoy.year, fecha__month=hoy.month).count(),
    })


@login_required
@require_http_methods(["GET", "POST"])
def orden_crear_view(request, contrato_id=None):
    if not _es_admin(request.user):
        return render(request, "dashboard/no_autorizado.html", status=403)
    contrato = None
    if contrato_id:
        contrato = get_object_or_404(Contrato.objects.select_related("cliente", "tecnico_designado__user"), pk=contrato_id)

    if request.method == "POST":
        form = OrdenTrabajoForm(request.POST, contrato_inicial=contrato)
        if form.is_valid():
            with transaction.atomic():
                orden = form.save(commit=False)
                if orden.contrato_id:
                    orden.sincronizar_desde_contrato()
                elif orden.cliente_id:
                    c = orden.cliente
                    orden.nombre_contacto = orden.nombre_contacto or c.nombre
                    orden.telefono = orden.telefono or c.telefono or ""
                    orden.ciudad = orden.ciudad or c.ciudad or ""
                    orden.sector_urbanizacion = orden.sector_urbanizacion or c.sector_urbanizacion or ""
                    orden.direccion = orden.direccion or c.direccion or ""
                    orden.enlace_google_maps = orden.enlace_google_maps or c.enlace_google_maps or ""
                orden.creada_por = request.user
                orden.save()
            _notificar_trabajador(
                orden,
                "Nueva orden de trabajo",
                f"Tienes una {orden.tipo.nombre.lower()} asignada para el {orden.fecha:%d/%m/%Y}.",
            )
            _registrar(request.user, "Orden de trabajo creada", f"{orden.codigo}: {orden.descripcion_corta} para {orden.nombre_contacto}.", f"/dashboard/ordenes/{orden.pk}/")
            messages.success(request, f"{orden.codigo} creada y asignada correctamente.")
            return redirect("ordenes_trabajo:detalle", pk=orden.pk)
    else:
        form = OrdenTrabajoForm(contrato_inicial=contrato)

    return render(request, "ordenes_trabajo/orden_form.html", {"form": form, "contrato_inicial": contrato, "editando": False})


@login_required
@require_http_methods(["GET", "POST"])
def orden_editar_view(request, pk):
    if not _es_admin(request.user):
        return render(request, "dashboard/no_autorizado.html", status=403)
    orden = get_object_or_404(OrdenTrabajo, pk=pk)
    if request.method == "POST":
        form = OrdenTrabajoForm(request.POST, instance=orden)
        if form.is_valid():
            orden = form.save(commit=False)
            if orden.contrato_id:
                orden.sincronizar_desde_contrato()
            elif orden.cliente_id:
                c = orden.cliente
                orden.nombre_contacto = orden.nombre_contacto or c.nombre
                orden.telefono = orden.telefono or c.telefono or ""
                orden.ciudad = orden.ciudad or c.ciudad or ""
                orden.sector_urbanizacion = orden.sector_urbanizacion or c.sector_urbanizacion or ""
                orden.direccion = orden.direccion or c.direccion or ""
                orden.enlace_google_maps = orden.enlace_google_maps or c.enlace_google_maps or ""
            orden.save()
            _registrar(request.user, "Orden de trabajo actualizada", f"Se actualizó {orden.codigo}.", f"/dashboard/ordenes/{orden.pk}/")
            messages.success(request, "Orden actualizada correctamente.")
            return redirect("ordenes_trabajo:detalle", pk=orden.pk)
    else:
        form = OrdenTrabajoForm(instance=orden)
    return render(request, "ordenes_trabajo/orden_form.html", {"form": form, "orden": orden, "editando": True})


@login_required
def orden_detalle_view(request, pk):
    orden = get_object_or_404(OrdenTrabajo.objects.select_related("tipo", "trabajador__user", "cliente", "contrato"), pk=pk)
    admin = _es_admin(request.user)
    trabajador = None
    if not admin:
        if not _es_trabajador(request.user):
            return render(request, "dashboard/no_autorizado.html", status=403)
        try:
            trabajador = request.user.trabajador
        except Exception:
            return render(request, "dashboard/no_autorizado.html", status=403)
        if orden.trabajador_id != trabajador.id:
            return render(request, "dashboard/no_autorizado.html", status=403)

    telefono = _normalizar_whatsapp(orden.telefono)
    nombre_tecnico = (request.user.get_full_name() or request.user.username).strip()
    texto = f"Hola, buenos días. Soy {nombre_tecnico}, técnico de JVAQUA. Me encuentro aquí en su domicilio para realizar el trabajo programado."
    whatsapp_url = f"https://wa.me/{telefono}?text={quote(texto)}" if telefono and not admin else ""
    return render(request, "ordenes_trabajo/orden_detalle.html", {
        "orden": orden,
        "es_admin": admin,
        "base_template": "dashboard/base_admin.html" if admin else "dashboard/base_trabajador.html",
        "whatsapp_url": whatsapp_url,
    })


@login_required
@require_POST
def orden_iniciar_view(request, pk):
    orden = get_object_or_404(OrdenTrabajo, pk=pk)
    try:
        trabajador = request.user.trabajador
    except Exception:
        trabajador = None
    if not trabajador or orden.trabajador_id != trabajador.id:
        return render(request, "dashboard/no_autorizado.html", status=403)
    if orden.estado == "pendiente":
        orden.estado = "en_proceso"
        orden.iniciada_en = timezone.now()
        orden.save(update_fields=["estado", "iniciada_en", "actualizada_en"])
        _registrar(request.user, "Orden iniciada", f"{request.user.username} inició {orden.codigo}.", f"/dashboard/ordenes/{orden.pk}/")
        messages.success(request, "Orden marcada en proceso.")
    return redirect("ordenes_trabajo:detalle", pk=orden.pk)


@login_required
@require_POST
def orden_guardar_trabajador_view(request, pk):
    orden = get_object_or_404(OrdenTrabajo, pk=pk)
    try:
        trabajador = request.user.trabajador
    except Exception:
        trabajador = None
    if not trabajador or orden.trabajador_id != trabajador.id:
        return render(request, "dashboard/no_autorizado.html", status=403)
    if orden.estado in {"completada", "cancelada"}:
        messages.warning(request, "Esta orden ya está cerrada.")
        return redirect("ordenes_trabajo:detalle", pk=orden.pk)

    orden.reporte_trabajador = (request.POST.get("reporte_trabajador") or "").strip()
    finalizar = request.POST.get("accion") == "finalizar"
    if finalizar:
        orden.estado = "completada"
        orden.completada_en = timezone.now()
        if not orden.iniciada_en:
            orden.iniciada_en = orden.completada_en
    elif orden.estado == "pendiente":
        orden.estado = "en_proceso"
        orden.iniciada_en = timezone.now()
    orden.save()

    tipos = ["antes", "durante", "despues"]
    for tipo in tipos:
        archivo = request.FILES.get(f"foto_{tipo}")
        if archivo:
            FotoOrdenTrabajo.objects.create(orden=orden, imagen=archivo, tipo=tipo)

    _registrar(request.user, "Orden de trabajo completada" if finalizar else "Orden de trabajo actualizada", f"{orden.codigo}: {orden.nombre_contacto}.", f"/dashboard/ordenes/{orden.pk}/")
    messages.success(request, "Orden completada correctamente." if finalizar else "Avance guardado correctamente.")
    return redirect("ordenes_trabajo:detalle", pk=orden.pk)


@login_required
@require_POST
def orden_cancelar_view(request, pk):
    if not _es_admin(request.user):
        return render(request, "dashboard/no_autorizado.html", status=403)
    orden = get_object_or_404(OrdenTrabajo, pk=pk)
    if orden.estado != "completada":
        orden.estado = "cancelada"
        orden.save(update_fields=["estado", "actualizada_en"])
        _registrar(request.user, "Orden cancelada", f"Se canceló {orden.codigo}.", f"/dashboard/ordenes/{orden.pk}/")
        messages.success(request, "Orden cancelada.")
    return redirect("ordenes_trabajo:detalle", pk=orden.pk)


@login_required
def mis_ordenes_view(request):
    if not _es_trabajador(request.user):
        return render(request, "dashboard/no_autorizado.html", status=403)
    try:
        trabajador = request.user.trabajador
    except Exception:
        return render(request, "dashboard/no_autorizado.html", status=403)
    hoy = timezone.localdate()
    qs = OrdenTrabajo.objects.filter(trabajador=trabajador).select_related("tipo", "cliente", "contrato")
    return render(request, "ordenes_trabajo/mis_ordenes.html", {
        "hoy": hoy,
        "hoy_ordenes": qs.filter(fecha=hoy).exclude(estado="cancelada").order_by("hora", "id"),
        "atrasadas": qs.filter(fecha__lt=hoy, estado__in=["pendiente", "en_proceso"]).order_by("fecha", "hora")[:30],
        "proximas": qs.filter(fecha__gt=hoy, estado__in=["pendiente", "en_proceso"]).order_by("fecha", "hora")[:30],
    })
