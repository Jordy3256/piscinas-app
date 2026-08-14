# backend/backend/urls.py
from django.contrib import admin
from django.urls import path, include, re_path
from django.http import HttpResponse
from django.shortcuts import redirect
from django.conf import settings
from django.views.static import serve

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

# Servir media también con DEBUG=False
urlpatterns += [
    re_path(
        r"^media/(?P<path>.*)$",
        serve,
        {"document_root": settings.MEDIA_ROOT},
    ),
]