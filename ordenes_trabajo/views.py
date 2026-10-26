from urllib.parse import quote
import logging

logger = logging.getLogger(__name__)

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from decimal import Decimal, InvalidOperation
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from contratos.models import Contrato
from clientes.models import Cliente
from dashboard.models import ActividadSistema, Notificacion
from trabajadores.models import Trabajador

from .forms import OrdenTrabajoForm
from .models import FotoOrdenTrabajo, OrdenTrabajo, TipoOrdenTrabajo


def _clientes_orden_json():
    """Datos públicos dentro del formulario administrativo autenticado."""
    contratos = {}
    for c in Contrato.objects.filter(activo=True).values("id", "cliente_id", "ciudad", "sector_urbanizacion", "direccion", "enlace_google_maps"):
        contratos.setdefault(str(c["cliente_id"]), []).append(c)
    return [{
        "id": c.pk, "nombre": c.nombre, "telefono": c.telefono,
        "ciudad": c.ciudad, "sector_urbanizacion": c.sector_urbanizacion,
        "direccion": c.direccion, "enlace_google_maps": c.enlace_google_maps,
        "contratos": contratos.get(str(c.pk), []),
    } for c in Cliente.objects.filter(activo=True).order_by("nombre")]


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
    """Registra el aviso y diagnostica el resultado real del envío push."""
    try:
        destinatario = orden.trabajador.user
        url = f"/dashboard/ordenes/{orden.pk}/"
        Notificacion.objects.create(
            user=destinatario,
            titulo=titulo,
            mensaje=mensaje,
            url=url,
            tipo="general",
            referencia_id=orden.pk,
        )
        logger.info(
            "ORDEN_PUSH registrado orden_id=%s user_id=%s",
            orden.pk, destinatario.pk,
        )

        def enviar_push():
            try:
                from dashboard.views import _send_push_to_user
                resultado = _send_push_to_user(
                    destinatario, titulo, mensaje, url=url,
                    tag=f"orden-{orden.pk}-{destinatario.pk}",
                )
                if resultado.get("ok"):
                    logger.info(
                        "ORDEN_PUSH enviado orden_id=%s user_id=%s sent=%s failed=%s",
                        orden.pk, destinatario.pk,
                        resultado.get("sent", 0), resultado.get("failed", 0),
                    )
                else:
                    logger.warning(
                        "ORDEN_PUSH sin_entrega orden_id=%s user_id=%s resultado=%s",
                        orden.pk, destinatario.pk, resultado,
                    )
            except Exception:
                logger.exception(
                    "ORDEN_PUSH excepcion orden_id=%s user_id=%s",
                    orden.pk, destinatario.pk,
                )

        transaction.on_commit(enviar_push)
    except Exception:
        logger.exception(
            "ORDEN_PUSH error_registro orden_id=%s", getattr(orden, "pk", None)
        )


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
                    orden.nombre_contacto = c.nombre
                    orden.telefono = c.telefono or ""
                    orden.ciudad = c.ciudad or ""
                    orden.sector_urbanizacion = c.sector_urbanizacion or ""
                    orden.direccion = c.direccion or ""
                    orden.enlace_google_maps = c.enlace_google_maps or ""
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

    return render(request, "ordenes_trabajo/orden_form.html", {"form": form, "contrato_inicial": contrato, "editando": False, "clientes_json": _clientes_orden_json()})


@login_required
@require_http_methods(["GET", "POST"])
def orden_editar_view(request, pk):
    if not _es_admin(request.user):
        return render(request, "dashboard/no_autorizado.html", status=403)
    orden = get_object_or_404(OrdenTrabajo, pk=pk)
    if request.method == "POST":
        form = OrdenTrabajoForm(request.POST, instance=orden)
        if form.is_valid():
            trabajador_anterior_id = orden.trabajador_id
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
            if orden.trabajador_id != trabajador_anterior_id and orden.estado != 'cancelada':
                _notificar_trabajador(
                    orden, 'Orden de trabajo asignada',
                    f'Se te asignó {orden.codigo} para el {orden.fecha:%d/%m/%Y}.',
                )
            _registrar(request.user, "Orden de trabajo actualizada", f"Se actualizó {orden.codigo}.", f"/dashboard/ordenes/{orden.pk}/")
            messages.success(request, "Orden actualizada correctamente.")
            return redirect("ordenes_trabajo:detalle", pk=orden.pk)
    else:
        form = OrdenTrabajoForm(instance=orden)
    return render(request, "ordenes_trabajo/orden_form.html", {"form": form, "orden": orden, "editando": True, "clientes_json": _clientes_orden_json()})


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


def _avisar_administracion(orden, titulo, mensaje):
    """Aviso interno y push sin bloquear el guardado de la orden."""
    url = f"/dashboard/ordenes/{orden.pk}/"
    for usuario in get_user_model().objects.filter(is_active=True).filter(Q(is_staff=True) | Q(is_superuser=True)).distinct():
        try:
            Notificacion.objects.create(user=usuario, titulo=titulo, mensaje=mensaje, url=url, tipo="general", referencia_id=orden.pk)
            def enviar(destinatario=usuario):
                try:
                    from dashboard.views import _send_push_to_user
                    _send_push_to_user(destinatario, titulo, mensaje, url=url, tag=f"revision-orden-{orden.pk}-{destinatario.pk}")
                except Exception:
                    logger.exception("Error push revisión de orden %s", orden.pk)
            transaction.on_commit(enviar)
        except Exception:
            logger.exception("Error aviso revisión de orden %s", orden.pk)


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
    if orden.estado in {"completada", "cancelada", "no_completada"} or orden.pendiente_revision:
        messages.warning(request, "Esta orden ya fue reportada y está pendiente de administración o cerrada.")
        return redirect("ordenes_trabajo:detalle", pk=pk)

    finalizar = request.POST.get("accion") == "finalizar"
    resultado = request.POST.get("resultado")
    if finalizar and resultado not in {"realizado", "no_realizado"}:
        messages.error(request, "Indica si el trabajo fue realizado o no completado.")
        return redirect("ordenes_trabajo:detalle", pk=pk)
    try:
        monto_texto = (request.POST.get("cobro_reportado") or "").strip().replace(",", ".")
        monto = Decimal(monto_texto) if monto_texto else None
        if monto is not None and (not monto.is_finite() or monto < 0):
            raise InvalidOperation
        if monto is not None and monto.as_tuple().exponent < -2:
            raise InvalidOperation
        if monto is not None and monto >= Decimal("100000000"):
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        messages.error(request, "El valor cobrado debe ser un importe válido no negativo con máximo dos decimales.")
        return redirect("ordenes_trabajo:detalle", pk=pk)
    imagenes = request.FILES.getlist("fotos")
    imagenes += [request.FILES[k] for k in ("foto_antes", "foto_durante", "foto_despues") if k in request.FILES]
    if any(not f.content_type.startswith("image/") or f.size > 12 * 1024 * 1024 for f in imagenes):
        messages.error(request, "Cada fotografía debe ser una imagen de máximo 12 MB.")
        return redirect("ordenes_trabajo:detalle", pk=pk)
    with transaction.atomic():
        orden.reporte_trabajador = (request.POST.get("reporte_trabajador") or "").strip()
        orden.cobro_reportado = monto
        orden.cobro_metodo = (request.POST.get("cobro_metodo") or "")[:30] if monto and monto > 0 else ""
        orden.cobro_observacion = (request.POST.get("cobro_observacion") or "").strip()
        if request.FILES.get("cobro_comprobante"):
            comprobante = request.FILES["cobro_comprobante"]
            if comprobante.size > 12 * 1024 * 1024:
                messages.error(request, "El comprobante no puede superar 12 MB.")
                return redirect("ordenes_trabajo:detalle", pk=pk)
            orden.cobro_comprobante = comprobante
        if finalizar:
            orden.resultado_reportado = resultado
            orden.pendiente_revision = True
            orden.completada_en = timezone.now()
            if not orden.iniciada_en:
                orden.iniciada_en = orden.completada_en
        elif orden.estado == "pendiente":
            orden.estado = "en_proceso"
            orden.iniciada_en = timezone.now()
        orden.save()
        for imagen in imagenes:
            FotoOrdenTrabajo.objects.create(orden=orden, imagen=imagen, tipo="otro")
        if finalizar:
            _avisar_administracion(orden, "Orden pendiente de revisión", f"{orden.codigo}: el técnico reportó {'trabajo realizado' if resultado == 'realizado' else 'trabajo no completado'}.")
    _registrar(request.user, "Orden reportada" if finalizar else "Avance de orden", f"{orden.codigo}: {orden.nombre_contacto}.", f"/dashboard/ordenes/{pk}/")
    messages.success(request, "Reporte enviado. Administración debe revisar y cerrar la orden." if finalizar else "Avance guardado correctamente.")
    return redirect("ordenes_trabajo:detalle", pk=pk)


@login_required
@require_POST
def orden_revisar_view(request, pk):
    if not _es_admin(request.user):
        return render(request, "dashboard/no_autorizado.html", status=403)
    with transaction.atomic():
        orden = get_object_or_404(OrdenTrabajo.objects.select_for_update(), pk=pk)
        if not orden.pendiente_revision:
            messages.warning(request, "No hay un reporte pendiente de revisión.")
            return redirect("ordenes_trabajo:detalle", pk=pk)
        accion = request.POST.get("accion")
        if accion == "devolver":
            orden.pendiente_revision = False
            orden.resultado_reportado = ""
            orden.estado = "en_proceso"
            orden.completada_en = None
            orden.observaciones_revision = (request.POST.get("observaciones_revision") or "").strip()
            orden.save()
            _notificar_trabajador(orden, "Orden devuelta para corrección", f"Administración devolvió {orden.codigo} para revisión.")
            messages.success(request, "Orden devuelta al trabajador.")
            return redirect("ordenes_trabajo:detalle", pk=pk)
        if accion != "aprobar":
            messages.error(request, "Acción no reconocida.")
            return redirect("ordenes_trabajo:detalle", pk=pk)
        if orden.resultado_reportado == "realizado" and orden.es_facturable:
            try:
                cobro = Decimal((request.POST.get("cobro_confirmado") or "0").replace(",", "."))
                if not cobro.is_finite() or cobro < 0 or cobro > orden.valor_cliente or cobro.as_tuple().exponent < -2:
                    raise InvalidOperation
            except (InvalidOperation, ValueError):
                messages.error(request, "Introduce un cobro verificado válido, entre $0 y el valor de la orden.")
                return redirect("ordenes_trabajo:detalle", pk=pk)
            orden.cobro_confirmado = cobro
            orden.cobro_confirmado_metodo = (request.POST.get("cobro_confirmado_metodo") or "")[:30]
            orden.cobro_verificado = True
            orden.cobro_confirmado_en = timezone.now()
            orden.cobro_confirmado_por = request.user
        orden.pendiente_revision = False
        orden.revisado_por = request.user
        orden.revision_admin_en = timezone.now()
        orden.observaciones_revision = (request.POST.get("observaciones_revision") or "").strip()
        orden.estado = "completada" if orden.resultado_reportado == "realizado" else "no_completada"
        orden.save()
    _registrar(request.user, "Orden revisada", f"Administración cerró {orden.codigo}.", f"/dashboard/ordenes/{pk}/")
    messages.success(request, "Orden revisada y cerrada. El cobro confirmado queda registrado en la orden; todavía no se contabiliza automáticamente en Finanzas.")
    return redirect("ordenes_trabajo:detalle", pk=pk)


@login_required
@require_POST
def orden_cancelar_view(request, pk):
    if not _es_admin(request.user):
        return render(request, "dashboard/no_autorizado.html", status=403)
    orden = get_object_or_404(OrdenTrabajo, pk=pk)
    if orden.estado not in {"completada", "no_completada"} and not orden.pendiente_revision:
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
