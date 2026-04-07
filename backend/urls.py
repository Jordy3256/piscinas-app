# backend/backend/urls.py
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static

from dashboard.views import login_view, logout_view


def healthz(_request):
    return HttpResponse("ok", content_type="text/plain")


def root_redirect(_request):
    return redirect("/dashboard/", permanent=False)


urlpatterns = [
    path("healthz", healthz),
    path("healthz/", healthz),

    path("admin/", admin.site.urls),

    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),

    path("dashboard/", include("dashboard.urls")),

    path("", root_redirect),
]

# Servir media también fuera de DEBUG para las fotos subidas
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)