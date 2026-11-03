# backend/backend/urls.py
from django.contrib import admin
from django.urls import path, include, re_path
from django.http import HttpResponse, Http404
from django.shortcuts import redirect
from django.conf import settings
from django.views.static import serve

from dashboard.views import login_view, logout_view


def healthz(_request):
    return HttpResponse("ok", content_type="text/plain")


def comprobante_digital_publico_bloqueado(_request, path=""):
    """Los comprobantes de AQUO360 solo se consultan mediante vista administrativa autenticada."""
    raise Http404("Archivo privado de AQUO360")


def root_redirect(_request):
    return redirect("/dashboard/", permanent=False)


urlpatterns = [
    path("healthz", healthz),
    path("healthz/", healthz),

    path("admin/", admin.site.urls),

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
    re_path(
        r"^media/(?P<path>.*)$",
        serve,
        {"document_root": settings.MEDIA_ROOT},
    ),
]