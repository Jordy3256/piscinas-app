# backend/backend/urls.py
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.shortcuts import redirect

from dashboard.views import login_view, logout_view


# ✅ Health check para Render
def healthz(_request):
    return HttpResponse("ok", content_type="text/plain")


def root_redirect(_request):
    # Si quieres raíz -> dashboard
    return redirect("/dashboard/", permanent=False)


urlpatterns = [
    # ✅ Health checks (con y sin slash)
    path("healthz", healthz),
    path("healthz/", healthz),

    # Admin
    path("admin/", admin.site.urls),

    # Auth
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),

    # Dashboard
    path("dashboard/", include("dashboard.urls")),

    # Root -> dashboard
    path("", root_redirect),
]