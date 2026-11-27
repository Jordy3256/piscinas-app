# backend/backend/urls.py
from django.contrib import admin
from django.urls import path, include, re_path
from django.http import HttpResponse, Http404
from django.shortcuts import redirect
from django.conf import settings
from django.views.static import serve
from django.utils import timezone
from django.http import FileResponse
from django.views.decorators.cache import never_cache

from dashboard.views import login_view, logout_view


def healthz(_request):
    return HttpResponse("ok", content_type="text/plain")


def comprobante_digital_publico_bloqueado(_request, path=""):
    """Los comprobantes de AQUO360 solo se consultan mediante vista administrativa autenticada."""
    raise Http404("Archivo privado de AQUO360")


@never_cache
def foto_mantenimiento_privada(request, path):
    """No servir evidencias por URL publica sin validar objeto y rol."""
    from dashboard.views import es_admin
    from mantenimientos.models import FotoMantenimiento
    from portal_clientes.models import AccesoCliente
    from trabajadores.models import Trabajador

    if not request.user.is_authenticated:
        raise Http404
    nombre = "mantenimientos/" + path
    foto = FotoMantenimiento.objects.select_related("mantenimiento").filter(imagen=nombre).first()
    if foto is None:
        raise Http404
    mantenimiento = foto.mantenimiento
    autorizado = es_admin(request.user)
    if not autorizado:
        tecnico = Trabajador.objects.filter(user=request.user, activo=True).first()
        if tecnico is not None:
            autorizado = mantenimiento.trabajadores.filter(pk=tecnico.pk).exists()
        else:
            autorizado = (
                mantenimiento.estado == "realizado"
                and mantenimiento.fecha <= timezone.localdate()
                and mantenimiento.cliente_id == mantenimiento.contrato.cliente_id
                and AccesoCliente.objects.filter(
                    usuario=request.user, habilitado=True, cliente__activo=True,
                    cliente_id=mantenimiento.cliente_id,
                ).exists()
            )
    if not autorizado:
        raise Http404
    try:
        archivo = foto.imagen.open("rb")
    except (OSError, IOError, ValueError):
        raise Http404
    respuesta = FileResponse(archivo)
    respuesta["Cache-Control"] = "private, no-store, max-age=0"
    respuesta["X-Content-Type-Options"] = "nosniff"
    respuesta["Referrer-Policy"] = "no-referrer"
    return respuesta


@never_cache
def archivo_orden_trabajo_privado(request, path):
    """Autoriza cada evidencia o comprobante por orden y asignación vigente."""
    from ordenes_trabajo.models import FotoOrdenTrabajo, OrdenTrabajo
    from ordenes_trabajo.views import _es_admin
    from trabajadores.models import Trabajador

    if not request.user.is_authenticated:
        raise Http404
    nombre = "ordenes_trabajo/" + path
    archivo = None
    orden = None
    if path.startswith("comprobantes/"):
        orden = OrdenTrabajo.objects.filter(cobro_comprobante=nombre).first()
        if orden is not None:
            archivo = orden.cobro_comprobante
    else:
        foto = FotoOrdenTrabajo.objects.select_related("orden").filter(imagen=nombre).first()
        if foto is not None:
            orden, archivo = foto.orden, foto.imagen
    if orden is None or archivo is None:
        raise Http404
    autorizado = _es_admin(request.user)
    if not autorizado:
        autorizado = Trabajador.objects.filter(
            user=request.user, activo=True, pk=orden.trabajador_id
        ).exists()
    if not autorizado:
        raise Http404
    try:
        fichero = archivo.open("rb")
    except (OSError, IOError, ValueError):
        raise Http404
    respuesta = FileResponse(fichero)
    respuesta["Cache-Control"] = "private, no-store, max-age=0"
    respuesta["X-Content-Type-Options"] = "nosniff"
    respuesta["Referrer-Policy"] = "no-referrer"
    return respuesta


def comprobante_financiero_publico_bloqueado(_request, path=""):
    """Impide el acceso directo a comprobantes sin validar permisos."""
    raise Http404("Comprobante financiero privado")


def root_redirect(request):
    if request.user.is_authenticated:
        from portal_clientes.models import AccesoCliente
        if AccesoCliente.objects.filter(usuario=request.user).exists():
            return redirect("/portal/inicio/", permanent=False)
        return redirect("/dashboard/inicio/", permanent=False)
    return redirect("/login/", permanent=False)


urlpatterns = [
    path("healthz", healthz),
    path("healthz/", healthz),

    path("admin/", admin.site.urls),
    path("portal/", include("portal_clientes.urls")),

    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),

    path("dashboard/finanzas/", include("finanzas.urls")),
    path("dashboard/asistente/", include("asistente_tecnico.urls")),
    path("dashboard/ordenes/", include("ordenes_trabajo.urls")),
    path("dashboard/", include("dashboard.urls")),

    path("", root_redirect),
]

# Servir media también con DEBUG=False
urlpatterns += [
    # Debe preceder a la ruta generica de media. No cambia las fotos del ERP JVAQUA.
    re_path(
        r"^media/jvaqua_digital/comprobantes(?:/(?P<path>.*))?$",
        comprobante_digital_publico_bloqueado,
    ),
    re_path(r"^media/mantenimientos/(?P<path>.*)$", foto_mantenimiento_privada),
    re_path(r"^media/ordenes_trabajo/(?P<path>.*)$", archivo_orden_trabajo_privado),
    # Los comprobantes financieros solo se sirven por la vista autenticada.
    re_path(r"^media/finanzas(?:/(?P<path>.*))?$", comprobante_financiero_publico_bloqueado),
    re_path(
        r"^media/(?P<path>.*)$",
        serve,
        {"document_root": settings.MEDIA_ROOT},
    ),
]