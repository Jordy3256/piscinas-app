# dashboard/views.py
from datetime import date
from calendar import monthrange
import json  # ✅ NUEVO

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils.dateparse import parse_date
from django.http import HttpResponse, JsonResponse
from django.contrib.staticfiles import finders
from django.templatetags.static import static
from django.views.decorators.http import require_POST  # ✅ NUEVO

from contratos.models import Contrato
from trabajadores.models import Trabajador
from inventario.models import Insumo
from mantenimientos.models import Mantenimiento, UsoInsumo, FotoMantenimiento
from finanzas.models import Ingreso, Egreso

from .models import PushSubscription  # ✅ NUEVO (asegúrate de tener este modelo)


# -------------------
# Helpers de roles
# -------------------
def es_admin(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True

    grupos = {g.name.strip().lower() for g in user.groups.all()}

    return (
        "administradores" in grupos
        or "administrador" in grupos
        or "admins" in grupos
        or "adimistradores" in grupos
    )


def es_trabajador(user):
    if not user.is_authenticated:
        return False
    grupos = {g.name.strip().lower() for g in user.groups.all()}
    return "trabajadores" in grupos or "trabajador" in grupos


# -------------------
# ✅ PASO 4 — Guardar suscripción Push (PWA)
# -------------------
@login_required
@require_POST
def save_subscription_view(request):
    """
    Guarda la suscripción Web Push del dispositivo del usuario logueado.
    Espera un JSON con formato:
    {
      "endpoint": "...",
      "keys": { "p256dh": "...", "auth": "..." }
    }
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
        endpoint = (payload.get("endpoint") or "").strip()
        keys = payload.get("keys") or {}
        p256dh = (keys.get("p256dh") or "").strip()
        auth = (keys.get("auth") or "").strip()

        if not endpoint or not p256dh or not auth:
            return JsonResponse(
                {"ok": False, "error": "Suscripción incompleta (endpoint/keys)."},
                status=400,
            )

        # ✅ Guarda o actualiza por endpoint (un dispositivo = un endpoint)
        sub, created = PushSubscription.objects.update_or_create(
            user=request.user,
            endpoint=endpoint,
            defaults={"p256dh": p256dh, "auth": auth},
        )

        return JsonResponse(
            {
                "ok": True,
                "created": created,
                "id": sub.id,
            }
        )
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "JSON inválido."}, status=400)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


# -------------------
# Login / Logout
# -------------------
def login_view(request):
    ctx = {"error": ""}

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, "Bienvenido.")
            return redirect("/dashboard/")

        ctx["error"] = "Usuario o contraseña incorrectos"
        messages.error(request, ctx["error"])
        return render(request, "dashboard/login.html", ctx)

    return render(request, "dashboard/login.html", ctx)


def logout_view(request):
    logout(request)
    return redirect("/login/")


# -------------------
# ✅ /dashboard/sw.js (SW REAL con scope /dashboard/)
# -------------------
def sw_js_view(request):
    path = finders.find("dashboard/sw-dashboard.js")

    if path:
        with open(path, "rb") as f:
            content = f.read()
        resp = HttpResponse(content, content_type="application/javascript; charset=utf-8")
    else:
        resp = HttpResponse(
            "/* ERROR: dashboard/sw-dashboard.js no encontrado en staticfiles */",
            content_type="application/javascript; charset=utf-8",
        )

    resp["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp["Pragma"] = "no-cache"
    resp["Expires"] = "0"
    resp["Service-Worker-Allowed"] = "/dashboard/"
    return resp


# -------------------
# ✅ Manifest servido por Django
# -------------------
def manifest_json_view(request):
    data = {
        "name": "Piscinas App",
        "short_name": "Piscinas",
        "description": "Gestión de mantenimientos, operativo y finanzas.",
        "id": "/dashboard/",
        "start_url": "/dashboard/home/",
        "scope": "/dashboard/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#0d6efd",
        "orientation": "portrait",
        "icons": [
            {"src": static("dashboard/icons/icon-192.png"), "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": static("dashboard/icons/icon-192-maskable.png"), "sizes": "192x192", "type": "image/png", "purpose": "maskable"},
            {"src": static("dashboard/icons/icon-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": static("dashboard/icons/icon-512-maskable.png"), "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }

    resp = JsonResponse(data)
    resp["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp["Pragma"] = "no-cache"
    resp["Expires"] = "0"
    return resp


# -------------------
# Home
# -------------------
@login_required
def home_view(request):
    if es_admin(request.user):
        return render(request, "dashboard/home_admin.html", {"es_admin": True})
    if es_trabajador(request.user):
        return render(request, "dashboard/home_trabajador.html", {"es_admin": False})
    return render(request, "dashboard/no_autorizado.html", status=403)


# -------------------
# Dashboard por rol
# -------------------
@login_required
def dashboard_view(request):
    if es_admin(request.user):
        total_ingresos = (
            Contrato.objects.filter(activo=True).aggregate(total=Sum("precio_mensual"))["total"] or 0
        )
        total_egresos = Egreso.objects.aggregate(total=Sum("total"))["total"] or 0
        balance = total_ingresos - total_egresos

        return render(
            request,
            "dashboard/dashboard.html",
            {
                "modo": "admin",
                "total_ingresos": float(total_ingresos),
                "total_egresos": float(total_egresos),
                "balance": float(balance),
                "es_admin": True,
            },
        )

    if es_trabajador(request.user):
        hoy = date.today()
        try:
            trabajador = request.user.trabajador
            mantenimientos_hoy = (
                Mantenimiento.objects.filter(trabajadores=trabajador, fecha=hoy)
                .select_related("cliente", "contrato")
                .order_by("fecha")
            )
            mantenimientos_proximos = (
                Mantenimiento.objects.filter(trabajadores=trabajador, fecha__gt=hoy)
                .select_related("cliente", "contrato")
                .order_by("fecha")[:20]
            )
        except Exception:
            mantenimientos_hoy = Mantenimiento.objects.none()
            mantenimientos_proximos = Mantenimiento.objects.none()

        return render(
            request,
            "dashboard/dashboard_trabajador.html",
            {
                "modo": "trabajador",
                "hoy": hoy,
                "mantenimientos_hoy": mantenimientos_hoy,
                "mantenimientos_proximos": mantenimientos_proximos,
                "es_admin": False,
            },
        )

    return render(request, "dashboard/no_autorizado.html", status=403)

# (👇 el resto de tu archivo queda igual)
# ... todo lo que ya tienes sin cambios ...
#
@login_required
def offline_view(request):
    return render(request, "dashboard/offline.html")
