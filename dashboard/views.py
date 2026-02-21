# dashboard/views.py
from datetime import date
from calendar import monthrange
import json

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils.dateparse import parse_date
from django.http import HttpResponse, JsonResponse
from django.contrib.staticfiles import finders
from django.templatetags.static import static
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt

from contratos.models import Contrato
from trabajadores.models import Trabajador
from inventario.models import Insumo
from mantenimientos.models import Mantenimiento, UsoInsumo, FotoMantenimiento
from finanzas.models import Ingreso, Egreso

from .models import PushSubscription


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
# ✅ VAPID Public Key (para JS)
# GET /dashboard/push/public-key/
# -------------------
@require_GET
def vapid_public_key_view(request):
    # ⚠️ NO login_required (para que fetch() no reciba HTML/login)
    key = getattr(settings, "VAPID_PUBLIC_KEY", "") or ""
    key = key.replace("\n", "").replace("\r", "").strip()
    return JsonResponse({"publicKey": key})


# -------------------
# ✅ PASO 4 — Guardar suscripción Push (PWA)
# -------------------
@login_required
@require_POST
@csrf_exempt  # ✅ evita 403 CSRF en fetch() desde JS (si no mandas CSRF)
def save_subscription_view(request):
    """
    Espera JSON (PushSubscription.toJSON()):
    {
      "endpoint": "...",
      "keys": { "p256dh": "...", "auth": "..." }
    }
    """
    try:
        if not request.body:
            return JsonResponse({"ok": False, "error": "Body vacío."}, status=400)

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

        sub, created = PushSubscription.objects.update_or_create(
            user=request.user,
            endpoint=endpoint,
            defaults={"p256dh": p256dh, "auth": auth},
        )

        return JsonResponse({"ok": True, "created": created, "id": sub.id})
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


# -------------------
# Operativo Admin
# -------------------
@login_required
def admin_operativo_view(request):
    if not es_admin(request.user):
        return render(request, "dashboard/no_autorizado.html", status=403)

    hoy = date.today()
    fecha = hoy
    modo = (request.GET.get("modo") or "").strip().lower()

    if modo == "manana":
        fecha = date.fromordinal(hoy.toordinal() + 1)
    elif modo == "semana":
        fecha = hoy
    else:
        fecha_get = request.GET.get("fecha")
        fecha_parseada = parse_date(fecha_get) if fecha_get else None
        if fecha_parseada:
            fecha = fecha_parseada

    dia_list = (
        Mantenimiento.objects.filter(fecha=fecha)
        .select_related("cliente", "contrato")
        .prefetch_related("trabajadores")
        .order_by("estado", "fecha")
    )

    atrasados = (
        Mantenimiento.objects.filter(fecha__lt=hoy, estado="pendiente")
        .select_related("cliente", "contrato")
        .prefetch_related("trabajadores")
        .order_by("fecha")
    )

    proximos = (
        Mantenimiento.objects.filter(fecha__gt=hoy, estado="pendiente")
        .select_related("cliente", "contrato")
        .prefetch_related("trabajadores")
        .order_by("fecha")[:30]
    )

    resumen_trabajadores = (
        Mantenimiento.objects.values("trabajadores__id", "trabajadores__user__username")
        .annotate(
            dia=Count("id", filter=Q(fecha=fecha)),
            atrasados=Count("id", filter=Q(fecha__lt=hoy, estado="pendiente")),
            proximos=Count("id", filter=Q(fecha__gt=hoy, estado="pendiente")),
        )
        .exclude(trabajadores__id__isnull=True)
        .order_by("-atrasados", "-dia", "-proximos")
    )

    return render(
        request,
        "dashboard/admin_operativo.html",
        {
            "hoy": hoy,
            "fecha": fecha,
            "dia_list": dia_list,
            "atrasados": atrasados,
            "proximos": proximos,
            "resumen_trabajadores": resumen_trabajadores,
            "es_admin": True,
        },
    )


# -------------------
# (EL RESTO DE TUS VIEWS QUEDA IGUAL)
# -------------------
# ... aquí pegas sin cambios el resto de tu archivo tal como lo tienes


@login_required
def offline_view(request):
    tpl = "dashboard/offline_admin.html" if es_admin(request.user) else "dashboard/offline_trabajador.html"
    return render(request, tpl, {"es_admin": es_admin(request.user)})