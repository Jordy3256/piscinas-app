# dashboard/views.py
import json
import logging
from datetime import date, timedelta
from calendar import monthrange

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.staticfiles import finders
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.templatetags.static import static
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_GET

from pywebpush import webpush, WebPushException

from contratos.models import Contrato
from trabajadores.models import Trabajador
from inventario.models import Insumo
from mantenimientos.models import Mantenimiento, UsoInsumo, FotoMantenimiento
from finanzas.models import Ingreso, Egreso

try:
    from .models import PushSubscription
except Exception:
    PushSubscription = None

try:
    from .models import Notificacion
except Exception:
    Notificacion = None

logger = logging.getLogger(__name__)


# -------------------
# Helpers de roles
# -------------------
def es_admin(user):
    if not user.is_authenticated:
        return False

    if user.is_superuser or user.is_staff:
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
# Login / Logout
# -------------------
def login_view(request):
    ctx = {"error": ""}

    next_url = (request.GET.get("next", "") or "").strip()
    if request.method == "POST":
        next_url = (request.POST.get("next", next_url) or "").strip()

    def safe_redirect_target(url: str) -> str:
        if url and url_has_allowed_host_and_scheme(
            url=url,
            allowed_hosts={request.get_host()},
            require_https=not settings.DEBUG,
        ):
            return url
        return "/dashboard/inicio/"

    if request.method == "POST":
        username = (request.POST.get("username", "") or "").strip()
        password = (request.POST.get("password", "") or "").strip()
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, "Bienvenido.")
            return redirect(safe_redirect_target(next_url))

        ctx["error"] = "Usuario o contraseña incorrectos"
        ctx["next"] = next_url
        messages.error(request, ctx["error"])
        return render(request, "dashboard/login.html", ctx)

    ctx["next"] = next_url
    return render(request, "dashboard/login.html", ctx)


def logout_view(request):
    logout(request)
    return redirect("/login/")


# -------------------
# /dashboard/sw.js
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
# Manifest servido por Django
# -------------------
def manifest_json_view(request):
    data = {
        "name": "Piscinas App",
        "short_name": "Piscinas",
        "description": "Gestión de mantenimientos, operativo y finanzas.",
        "id": "/dashboard/",
        "start_url": "/dashboard/inicio/",
        "scope": "/dashboard/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#0d6efd",
        "orientation": "portrait",
        "icons": [
            {
                "src": static("dashboard/icons/icon-192.png"),
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any",
            },
            {
                "src": static("dashboard/icons/icon-192-maskable.png"),
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "maskable",
            },
            {
                "src": static("dashboard/icons/icon-512.png"),
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any",
            },
            {
                "src": static("dashboard/icons/icon-512-maskable.png"),
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable",
            },
        ],
    }

    resp = JsonResponse(data)
    resp["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp["Pragma"] = "no-cache"
    resp["Expires"] = "0"
    return resp


# ==========================================================
# PUSH / NOTIFICACIONES HELPERS
# ==========================================================
def _clean_str(value) -> str:
    return (value or "").replace("\n", "").replace("\r", "").strip()


def _normalize_subscription_payload(data: dict) -> dict:
    """
    Acepta:
    - subscription completo
    - dict con {endpoint, keys:{p256dh,auth}}
    - dict con {subscription: {...}}
    """
    if not isinstance(data, dict):
        return {}

    if "subscription" in data and isinstance(data["subscription"], dict):
        data = data["subscription"]

    endpoint = _clean_str(data.get("endpoint"))
    keys = data.get("keys") if isinstance(data.get("keys"), dict) else {}

    p256dh = _clean_str(keys.get("p256dh"))
    auth = _clean_str(keys.get("auth"))

    if not endpoint or not p256dh or not auth:
        return {}

    return {
        "endpoint": endpoint,
        "p256dh": p256dh,
        "auth": auth,
        "raw": data,
    }


def _push_status_code_from_exception(ex):
    try:
        return getattr(getattr(ex, "response", None), "status_code", None)
    except Exception:
        return None


def _push_response_body_from_exception(ex) -> str:
    try:
        response = getattr(ex, "response", None)
        if response is not None:
            return response.text or ""
    except Exception:
        pass
    return ""


def _send_push_to_user(user, title, body, url="/dashboard/notificaciones/", tag=None):
    if PushSubscription is None:
        return {"ok": False, "error": "Modelo PushSubscription no disponible"}

    vapid_private_key = (getattr(settings, "VAPID_PRIVATE_KEY", "") or "").strip()
    if not vapid_private_key:
        return {"ok": False, "error": "VAPID_PRIVATE_KEY vacío en settings/env"}

    vapid_subject = (
        getattr(settings, "VAPID_SUBJECT", "") or "mailto:admin@piscinas-app.local"
    ).strip()

    subs = PushSubscription.objects.filter(user=user).order_by("-updated_at", "-created_at")
    if not subs.exists():
        return {"ok": False, "error": "Usuario sin suscripciones push"}

    payload = json.dumps(
        {
            "title": title,
            "body": body,
            "url": url or "/dashboard/notificaciones/",
            "tag": tag or f"notif-{user.pk}",
        }
    )

    sent = 0
    failed = 0

    for s in subs:
        subscription_info = {
            "endpoint": s.endpoint,
            "keys": {"p256dh": s.p256dh, "auth": s.auth},
        }

        try:
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=vapid_private_key,
                vapid_claims={"sub": vapid_subject},
                content_encoding="aes128gcm",
                ttl=60,
            )
            sent += 1

        except WebPushException as ex:
            failed += 1
            status = _push_status_code_from_exception(ex)

            logger.warning(
                "Push falló user=%s sub_id=%s status=%s error=%s",
                getattr(user, "username", "unknown"),
                s.id,
                status,
                str(ex),
            )

            if status in (404, 410):
                try:
                    s.delete()
                except Exception:
                    logger.exception("No se pudo borrar sub expirada id=%s", s.id)

        except Exception:
            failed += 1
            logger.exception(
                "Error inesperado enviando push a user=%s",
                getattr(user, "username", "unknown"),
            )

    return {"ok": sent > 0, "sent": sent, "failed": failed}


def _crear_notificacion(user, titulo, mensaje, url="/dashboard/notificaciones/", enviar_push=False):
    if not user or not getattr(user, "is_authenticated", False):
        return None

    notif = None

    if Notificacion is not None:
        try:
            notif = Notificacion.objects.create(
                user=user,
                titulo=titulo,
                mensaje=mensaje,
                url=url,
                leida=False,
            )
        except Exception:
            logger.exception(
                "No se pudo crear Notificacion para user=%s",
                getattr(user, "username", "unknown"),
            )

    if enviar_push:
        try:
            _send_push_to_user(
                user=user,
                title=titulo,
                body=mensaje,
                url=url or "/dashboard/notificaciones/",
                tag=f"notif-{user.pk}",
            )
        except Exception:
            logger.exception(
                "No se pudo enviar push para user=%s",
                getattr(user, "username", "unknown"),
            )

    return notif


def _admins_queryset():
    ids_admins = []

    for user in User.objects.filter(is_active=True):
        try:
            if es_admin(user):
                ids_admins.append(user.id)
        except Exception:
            pass

    return User.objects.filter(id__in=ids_admins)


def _notificar_admins(titulo, mensaje, url="/dashboard/notificaciones/", enviar_push=False, excluir_user_id=None):
    admins = _admins_queryset()

    if excluir_user_id:
        admins = admins.exclude(id=excluir_user_id)

    for admin_user in admins:
        _crear_notificacion(
            user=admin_user,
            titulo=titulo,
            mensaje=mensaje,
            url=url,
            enviar_push=enviar_push,
        )


# ==========================================================
# Helpers operativo admin
# ==========================================================
def _mantenimiento_match_busqueda(mantenimiento, q: str) -> bool:
    if not q:
        return True

    q = q.strip().lower()
    if not q:
        return True

    bloques = [
        str(getattr(mantenimiento, "cliente", "") or ""),
        str(getattr(mantenimiento, "contrato", "") or ""),
        str(getattr(mantenimiento, "estado", "") or ""),
        str(getattr(mantenimiento, "fecha", "") or ""),
    ]

    try:
        for trabajador in mantenimiento.trabajadores.all():
            bloques.append(str(getattr(getattr(trabajador, "user", None), "username", "") or ""))
    except Exception:
        pass

    texto = " ".join(bloques).lower()
    return q in texto


def _filtrar_mantenimientos_por_busqueda(items, q: str):
    if not q:
        return list(items)
    return [m for m in items if _mantenimiento_match_busqueda(m, q)]


def _resumen_trabajadores_desde_listas(dia_list, atrasados, proximos):
    resumen = {}

    def asegurar_trabajador(trabajador):
        trabajador_id = getattr(trabajador, "id", None)
        username = str(getattr(getattr(trabajador, "user", None), "username", "") or "Sin usuario")

        if trabajador_id not in resumen:
            resumen[trabajador_id] = {
                "trabajadores__id": trabajador_id,
                "trabajadores__user__username": username,
                "dia": 0,
                "atrasados": 0,
                "proximos": 0,
            }
        return resumen[trabajador_id]

    for mantenimiento in dia_list:
        try:
            for trabajador in mantenimiento.trabajadores.all():
                asegurar_trabajador(trabajador)["dia"] += 1
        except Exception:
            pass

    for mantenimiento in atrasados:
        try:
            for trabajador in mantenimiento.trabajadores.all():
                asegurar_trabajador(trabajador)["atrasados"] += 1
        except Exception:
            pass

    for mantenimiento in proximos:
        try:
            for trabajador in mantenimiento.trabajadores.all():
                asegurar_trabajador(trabajador)["proximos"] += 1
        except Exception:
            pass

    return sorted(
        resumen.values(),
        key=lambda x: (-x["atrasados"], -x["dia"], -x["proximos"], x["trabajadores__user__username"]),
    )


def _sin_asignar_count(items):
    total = 0
    for m in items:
        try:
            if not m.trabajadores.exists():
                total += 1
        except Exception:
            pass
    return total


# ==========================================================
# PUSH
# ==========================================================
@login_required
@require_http_methods(["GET"])
def vapid_public_key_view(request):
    key = _clean_str(getattr(settings, "VAPID_PUBLIC_KEY", ""))
    if not key:
        return JsonResponse(
            {"publicKey": "", "warning": "VAPID_PUBLIC_KEY vacío"},
            status=200,
        )
    return JsonResponse({"publicKey": key})


@login_required
@require_http_methods(["GET"])
def push_status_view(request):
    if PushSubscription is None:
        return JsonResponse(
            {"ok": False, "enabled": False, "count": 0, "error": "Modelo PushSubscription no disponible"},
            status=500,
        )

    qs = PushSubscription.objects.filter(user=request.user).order_by("-updated_at", "-created_at")
    return JsonResponse(
        {
            "ok": True,
            "enabled": qs.exists(),
            "count": qs.count(),
        }
    )


@login_required
@require_http_methods(["POST"])
def save_subscription_view(request):
    if PushSubscription is None:
        return JsonResponse(
            {"ok": False, "error": "Modelo PushSubscription no disponible"},
            status=500,
        )

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "JSON inválido"}, status=400)

    norm = _normalize_subscription_payload(data)
    if not norm:
        return JsonResponse({"ok": False, "error": "Payload incompleto"}, status=400)

    user_agent = (request.META.get("HTTP_USER_AGENT", "") or "").strip()

    try:
        with transaction.atomic():
            obj, created = PushSubscription.objects.update_or_create(
                endpoint=norm["endpoint"],
                defaults={
                    "user": request.user,
                    "p256dh": norm["p256dh"],
                    "auth": norm["auth"],
                    "user_agent": user_agent,
                },
            )
    except Exception as ex:
        logger.exception("Error guardando push subscription para user=%s", request.user.pk)
        return JsonResponse(
            {"ok": False, "error": f"No se pudo guardar la suscripción: {str(ex)}"},
            status=500,
        )

    logger.info(
        "Push subscription guardada user=%s endpoint=%s created=%s",
        request.user.username,
        norm["endpoint"][:80],
        created,
    )

    return JsonResponse(
        {
            "ok": True,
            "created": created,
            "updated": not created,
            "id": obj.id,
            "user": request.user.username,
        },
        status=201 if created else 200,
    )


@login_required
@require_http_methods(["POST"])
def delete_subscription_view(request):
    if PushSubscription is None:
        return JsonResponse(
            {"ok": False, "error": "Modelo PushSubscription no disponible"},
            status=500,
        )

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "JSON inválido"}, status=400)

    norm = _normalize_subscription_payload(data)
    endpoint = norm.get("endpoint") if norm else _clean_str(data.get("endpoint"))

    if not endpoint:
        return JsonResponse({"ok": False, "error": "Endpoint requerido"}, status=400)

    deleted, _ = PushSubscription.objects.filter(
        user=request.user,
        endpoint=endpoint,
    ).delete()

    return JsonResponse({"ok": True, "deleted": bool(deleted)})


@login_required
@require_http_methods(["GET", "POST"])
def push_test_view(request):
    if request.method == "GET":
        return JsonResponse(
            {"ok": True, "msg": "push_test_view OK. Usa POST para enviar push."}
        )

    result = _send_push_to_user(
        user=request.user,
        title="✅ Prueba Piscinas App",
        body=f"Hola {request.user.username}, tu Push está funcionando 🎉",
        url="/dashboard/notificaciones/",
        tag=f"piscinas-{request.user.username}",
    )

    if not result.get("ok"):
        return JsonResponse(result, status=400)

    return JsonResponse(result)


# -------------------
# INICIO por rol (menú)
# -------------------
@login_required
def inicio_view(request):
    ctx = {"VAPID_PUBLIC_KEY": getattr(settings, "VAPID_PUBLIC_KEY", "")}

    if es_admin(request.user):
        ctx["es_admin"] = True
        return render(request, "dashboard/home_admin.html", ctx)

    if es_trabajador(request.user):
        ctx["es_admin"] = False
        return render(request, "dashboard/home_trabajador.html", ctx)

    return render(request, "dashboard/no_autorizado.html", status=403)


# -------------------
# /dashboard/home/ = pantalla REAL por rol
# -------------------
@login_required
def home_view(request):
    return dashboard_view(request)


# -------------------
# /dashboard/ = alias de la pantalla REAL por rol
# -------------------
@login_required
def dashboard_view(request):
    base_ctx = {"VAPID_PUBLIC_KEY": getattr(settings, "VAPID_PUBLIC_KEY", "")}

    if es_admin(request.user):
        total_ingresos = Ingreso.objects.aggregate(total=Sum("total"))["total"] or 0
        total_egresos = Egreso.objects.aggregate(total=Sum("total"))["total"] or 0
        balance = total_ingresos - total_egresos

        ctx = {
            **base_ctx,
            "modo": "admin",
            "total_ingresos": float(total_ingresos),
            "total_egresos": float(total_egresos),
            "balance": float(balance),
            "es_admin": True,
        }
        return render(request, "dashboard/dashboard.html", ctx)

    if es_trabajador(request.user):
        hoy = date.today()

        try:
            trabajador = request.user.trabajador
        except Exception:
            return render(request, "dashboard/no_autorizado.html", status=403)

        mantenimientos_hoy = (
            Mantenimiento.objects.filter(fecha=hoy, trabajadores=trabajador)
            .select_related("cliente", "contrato")
            .order_by("estado", "fecha")
        )

        mantenimientos_proximos = (
            Mantenimiento.objects.filter(fecha__gt=hoy, trabajadores=trabajador)
            .select_related("cliente", "contrato")
            .order_by("fecha")[:30]
        )

        ctx = {
            **base_ctx,
            "modo": "trabajador",
            "hoy": hoy,
            "mantenimientos_hoy": mantenimientos_hoy,
            "mantenimientos_proximos": mantenimientos_proximos,
            "es_admin": False,
        }
        return render(request, "dashboard/dashboard_trabajador.html", ctx)

    return render(request, "dashboard/no_autorizado.html", status=403)


# -------------------
# Pantalla de notificaciones
# -------------------
@login_required
def notificaciones_view(request):
    subs_count = 0
    push_enabled = False

    if PushSubscription is not None:
        subs_count = PushSubscription.objects.filter(user=request.user).count()
        push_enabled = subs_count > 0

    notificaciones = []
    no_modelo_notificaciones = False

    if Notificacion is not None:
        notificaciones = list(
            Notificacion.objects.filter(user=request.user)
            .order_by("-creada_en")[:20]
        )

        ids_no_leidas = [n.id for n in notificaciones if not n.leida]
        if ids_no_leidas:
            ahora = timezone.now()
            Notificacion.objects.filter(
                id__in=ids_no_leidas,
                user=request.user,
                leida=False,
            ).update(
                leida=True,
                leida_en=ahora,
            )

            for n in notificaciones:
                if n.id in ids_no_leidas:
                    n.leida = True
                    n.leida_en = ahora
    else:
        no_modelo_notificaciones = True

    return render(
        request,
        "dashboard/notificaciones.html",
        {
            "subs_count": subs_count,
            "push_enabled": push_enabled,
            "notificaciones": notificaciones,
            "no_modelo_notificaciones": no_modelo_notificaciones,
            "es_admin": es_admin(request.user),
            "base_template": "dashboard/base_admin.html" if es_admin(request.user) else "dashboard/base_trabajador.html",
        },
    )


@login_required
@require_GET
def notificaciones_json_view(request):
    if Notificacion is None:
        return JsonResponse({
            "ok": True,
            "items": [],
            "unread_count": 0,
        })

    qs = Notificacion.objects.filter(user=request.user).order_by("-creada_en")[:10]

    items = []
    for n in qs:
        items.append({
            "id": n.id,
            "titulo": n.titulo,
            "mensaje": n.mensaje,
            "url": n.url or "/dashboard/notificaciones/",
            "leida": n.leida,
            "creada_en": n.creada_en.strftime("%d/%m/%Y %H:%M"),
        })

    unread_count = Notificacion.objects.filter(
        user=request.user,
        leida=False
    ).count()

    return JsonResponse({
        "ok": True,
        "items": items,
        "unread_count": unread_count,
    })


@login_required
def notificaciones_historial_view(request):
    if Notificacion is None:
        page_obj = None
    else:
        qs = Notificacion.objects.filter(user=request.user).order_by("-creada_en")
        paginator = Paginator(qs, 15)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

    return render(
        request,
        "dashboard/notificaciones_historial.html",
        {
            "page_obj": page_obj,
            "es_admin": es_admin(request.user),
            "base_template": "dashboard/base_admin.html" if es_admin(request.user) else "dashboard/base_trabajador.html",
        },
    )


@login_required
@require_http_methods(["POST"])
def marcar_notificacion_leida_view(request, pk):
    if Notificacion is None:
        return JsonResponse({"ok": False, "error": "Modelo no disponible"}, status=500)

    notificacion = get_object_or_404(Notificacion, pk=pk, user=request.user)

    if not notificacion.leida:
        notificacion.leida = True
        notificacion.leida_en = timezone.now()
        notificacion.save(update_fields=["leida", "leida_en"])

    return JsonResponse({"ok": True})


@login_required
@require_http_methods(["POST"])
def notificacion_eliminar_view(request, pk):
    if Notificacion is None:
        return JsonResponse({"ok": False, "error": "Modelo no disponible"}, status=500)

    notificacion = get_object_or_404(Notificacion, pk=pk, user=request.user)
    notificacion.delete()

    return JsonResponse({"ok": True})


@login_required
@require_http_methods(["POST"])
def notificaciones_eliminar_todas_view(request):
    if Notificacion is None:
        return JsonResponse({"ok": False, "error": "Modelo no disponible"}, status=500)

    Notificacion.objects.filter(user=request.user).delete()
    return JsonResponse({"ok": True})


@login_required
@require_http_methods(["POST"])
def marcar_todas_leidas_view(request):
    if Notificacion is None:
        return JsonResponse({"ok": False, "error": "Modelo no disponible"}, status=500)

    ahora = timezone.now()

    Notificacion.objects.filter(
        user=request.user,
        leida=False,
    ).update(
        leida=True,
        leida_en=ahora,
    )

    return JsonResponse({"ok": True})


# -------------------
# Operativo Admin
# -------------------
@login_required
def admin_operativo_view(request):
    if not es_admin(request.user):
        return render(request, "dashboard/no_autorizado.html", status=403)

    hoy = date.today()
    fecha = hoy
    fecha_desde = hoy
    fecha_hasta = hoy
    q = (request.GET.get("q", "") or "").strip()
    modo = (request.GET.get("modo", "") or "").strip().lower()

    if modo == "manana":
        fecha = hoy + timedelta(days=1)
        fecha_desde = fecha
        fecha_hasta = fecha
        etiqueta_periodo = f"Mañana ({fecha})"
    elif modo == "semana":
        fecha_desde = hoy
        fecha_hasta = hoy + timedelta(days=6)
        fecha = fecha_desde
        etiqueta_periodo = f"Semana ({fecha_desde} a {fecha_hasta})"
    elif modo == "hoy" or not modo:
        fecha_get = request.GET.get("fecha")
        fecha_parseada = parse_date(fecha_get) if fecha_get else None

        if fecha_parseada:
            fecha = fecha_parseada
            fecha_desde = fecha_parseada
            fecha_hasta = fecha_parseada
            etiqueta_periodo = f"Fecha seleccionada ({fecha_parseada})"
        else:
            fecha = hoy
            fecha_desde = hoy
            fecha_hasta = hoy
            modo = "hoy"
            etiqueta_periodo = f"Hoy ({hoy})"
    else:
        fecha_get = request.GET.get("fecha")
        fecha_parseada = parse_date(fecha_get) if fecha_get else None
        if fecha_parseada:
            fecha = fecha_parseada
            fecha_desde = fecha_parseada
            fecha_hasta = fecha_parseada
            etiqueta_periodo = f"Fecha seleccionada ({fecha_parseada})"
        else:
            fecha = hoy
            fecha_desde = hoy
            fecha_hasta = hoy
            modo = "hoy"
            etiqueta_periodo = f"Hoy ({hoy})"

    base_dia_qs = (
        Mantenimiento.objects.filter(fecha__range=(fecha_desde, fecha_hasta))
        .select_related("cliente", "contrato")
        .prefetch_related("trabajadores")
        .order_by("fecha", "estado", "id")
    )

    base_atrasados_qs = (
        Mantenimiento.objects.filter(fecha__lt=hoy, estado="pendiente")
        .select_related("cliente", "contrato")
        .prefetch_related("trabajadores")
        .order_by("fecha", "id")
    )

    base_proximos_qs = (
        Mantenimiento.objects.filter(fecha__gt=hoy, estado="pendiente")
        .select_related("cliente", "contrato")
        .prefetch_related("trabajadores")
        .order_by("fecha", "id")[:50]
    )

    dia_list = _filtrar_mantenimientos_por_busqueda(base_dia_qs, q)
    atrasados = _filtrar_mantenimientos_por_busqueda(base_atrasados_qs, q)
    proximos = _filtrar_mantenimientos_por_busqueda(base_proximos_qs, q)

    resumen_trabajadores = _resumen_trabajadores_desde_listas(dia_list, atrasados, proximos)

    sin_asignar_dia = _sin_asignar_count(dia_list)
    sin_asignar_atrasados = _sin_asignar_count(atrasados)
    sin_asignar_proximos = _sin_asignar_count(proximos)
    total_sin_asignar = sin_asignar_dia + sin_asignar_atrasados + sin_asignar_proximos

    return render(
        request,
        "dashboard/admin_operativo.html",
        {
            "hoy": hoy,
            "fecha": fecha,
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
            "modo_actual": modo,
            "q": q,
            "etiqueta_periodo": etiqueta_periodo,
            "dia_list": dia_list,
            "atrasados": atrasados,
            "proximos": proximos,
            "resumen_trabajadores": resumen_trabajadores,
            "sin_asignar_dia": sin_asignar_dia,
            "sin_asignar_atrasados": sin_asignar_atrasados,
            "sin_asignar_proximos": sin_asignar_proximos,
            "total_sin_asignar": total_sin_asignar,
            "es_admin": True,
        },
    )


# -------------------
# Detalle mantenimiento
# -------------------
@login_required
def mantenimiento_detalle_view(request, pk):
    mantenimiento = get_object_or_404(Mantenimiento, pk=pk)

    if es_admin(request.user):
        permitido = True
    elif es_trabajador(request.user):
        try:
            trabajador = request.user.trabajador
            permitido = mantenimiento.trabajadores.filter(pk=trabajador.pk).exists()
        except Exception:
            permitido = False
    else:
        permitido = False

    if not permitido:
        return render(request, "dashboard/no_autorizado.html", status=403)

    insumos = Insumo.objects.all().order_by("nombre")

    if request.method == "POST":
        accion = request.POST.get("accion")
        next_url = (request.POST.get("next", "") or "").strip()

        def safe_return_url():
            if next_url and url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=not settings.DEBUG,
            ):
                return next_url
            return f"/dashboard/mantenimientos/{mantenimiento.pk}/"

        if accion == "marcar_realizado":
            mantenimiento.estado = "realizado"
            mantenimiento.save()

            actor = request.user.username
            _notificar_admins(
                titulo="✅ Mantenimiento realizado",
                mensaje=f"El mantenimiento de {mantenimiento.cliente} fue marcado como realizado por {actor}.",
                url=f"/dashboard/mantenimientos/{mantenimiento.pk}/",
                enviar_push=True,
                excluir_user_id=request.user.id if es_admin(request.user) else None,
            )

            messages.success(request, f"Mantenimiento de {mantenimiento.cliente} marcado como realizado.")
            return redirect(safe_return_url())

        if accion == "marcar_pendiente":
            mantenimiento.estado = "pendiente"
            mantenimiento.save()

            actor = request.user.username
            _notificar_admins(
                titulo="🟡 Mantenimiento pendiente",
                mensaje=f"El mantenimiento de {mantenimiento.cliente} fue marcado como pendiente por {actor}.",
                url=f"/dashboard/mantenimientos/{mantenimiento.pk}/",
                enviar_push=False,
                excluir_user_id=request.user.id if es_admin(request.user) else None,
            )

            messages.success(request, f"Mantenimiento de {mantenimiento.cliente} marcado como pendiente.")
            return redirect(safe_return_url())

        if accion == "agregar_insumo":
            insumo_id = request.POST.get("insumo_id")
            cantidad_str = request.POST.get("cantidad")

            try:
                cantidad = int(cantidad_str)
                if cantidad <= 0:
                    raise ValueError
            except Exception:
                messages.error(request, "Cantidad inválida.")
                return redirect(f"/dashboard/mantenimientos/{mantenimiento.pk}/")

            insumo = get_object_or_404(Insumo, pk=insumo_id)

            if hasattr(insumo, "stock"):
                if insumo.stock < cantidad:
                    messages.error(
                        request,
                        f"Stock insuficiente de {insumo.nombre}. Disponible: {insumo.stock}",
                    )
                    return redirect(f"/dashboard/mantenimientos/{mantenimiento.pk}/")
                insumo.stock -= cantidad
                insumo.save()

            if hasattr(insumo, "precio"):
                costo_unitario = insumo.precio
            elif hasattr(insumo, "costo"):
                costo_unitario = insumo.costo
            else:
                costo_unitario = 0

            egreso = Egreso.objects.create(
                mantenimiento=mantenimiento,
                insumo=insumo,
                cantidad=cantidad,
                costo_unitario=costo_unitario,
                total=0,
            )

            UsoInsumo.objects.create(
                mantenimiento=mantenimiento,
                insumo=insumo,
                cantidad=cantidad,
                egreso=egreso,
            )

            actor = request.user.username
            _notificar_admins(
                titulo="🧪 Insumo registrado",
                mensaje=f"{actor} registró {insumo.nombre} x {cantidad} en {mantenimiento.cliente}.",
                url=f"/dashboard/mantenimientos/{mantenimiento.pk}/",
                enviar_push=False,
                excluir_user_id=request.user.id if es_admin(request.user) else None,
            )

            messages.success(request, f"Insumo registrado: {insumo.nombre} x {cantidad}")
            return redirect(f"/dashboard/mantenimientos/{mantenimiento.pk}/")

        if accion == "subir_foto":
            imagen = request.FILES.get("imagen")
            descripcion = request.POST.get("descripcion", "").strip()

            if not imagen:
                messages.error(request, "Debes seleccionar una imagen.")
                return redirect(f"/dashboard/mantenimientos/{mantenimiento.pk}/")

            FotoMantenimiento.objects.create(
                mantenimiento=mantenimiento,
                imagen=imagen,
                descripcion=descripcion,
            )

            actor = request.user.username
            _notificar_admins(
                titulo="📸 Nueva foto subida",
                mensaje=f"{actor} subió una foto en el mantenimiento de {mantenimiento.cliente}.",
                url=f"/dashboard/mantenimientos/{mantenimiento.pk}/",
                enviar_push=False,
                excluir_user_id=request.user.id if es_admin(request.user) else None,
            )

            messages.success(request, "Foto subida correctamente.")
            return redirect(f"/dashboard/mantenimientos/{mantenimiento.pk}/")

    lista_usos = mantenimiento.usos_insumos.all()
    lista_egresos = mantenimiento.egresos.all() if hasattr(mantenimiento, "egresos") else []
    total_egresos = sum(e.total for e in lista_egresos) if lista_egresos else 0
    fotos = mantenimiento.fotos.all().order_by("-creada_en")

    return render(
        request,
        "dashboard/mantenimiento_detalle.html",
        {
            "m": mantenimiento,
            "insumos": insumos,
            "lista_usos": lista_usos,
            "lista_egresos": lista_egresos,
            "total_egresos": total_egresos,
            "es_admin": es_admin(request.user),
            "fotos": fotos,
        },
    )


@login_required
def usoinsumo_eliminar_view(request, pk):
    uso = get_object_or_404(UsoInsumo, pk=pk)
    mantenimiento = uso.mantenimiento

    if es_admin(request.user):
        permitido = True
    elif es_trabajador(request.user):
        try:
            trabajador = request.user.trabajador
            permitido = mantenimiento.trabajadores.filter(pk=trabajador.pk).exists()
        except Exception:
            permitido = False
    else:
        permitido = False

    if not permitido:
        return render(request, "dashboard/no_autorizado.html", status=403)

    if request.method == "POST":
        insumo = uso.insumo
        if hasattr(insumo, "stock"):
            insumo.stock += uso.cantidad
            insumo.save()

        if getattr(uso, "egreso_id", None):
            uso.egreso.delete()

        uso.delete()

        actor = request.user.username
        _notificar_admins(
            titulo="🗑 Insumo eliminado",
            mensaje=f"{actor} eliminó un uso de insumo en {mantenimiento.cliente}.",
            url=f"/dashboard/mantenimientos/{mantenimiento.pk}/",
            enviar_push=False,
            excluir_user_id=request.user.id if es_admin(request.user) else None,
        )

        messages.success(request, "Uso de insumo eliminado y stock devuelto.")
        return redirect(f"/dashboard/mantenimientos/{mantenimiento.pk}/")

    return render(
        request,
        "dashboard/usoinsumo_confirmar_eliminar.html",
        {"uso": uso, "es_admin": es_admin(request.user)},
    )


@login_required
def usoinsumo_editar_view(request, pk):
    uso = get_object_or_404(UsoInsumo, pk=pk)
    mantenimiento = uso.mantenimiento

    if es_admin(request.user):
        permitido = True
    elif es_trabajador(request.user):
        try:
            trabajador = request.user.trabajador
            permitido = mantenimiento.trabajadores.filter(pk=trabajador.pk).exists()
        except Exception:
            permitido = False
    else:
        permitido = False

    if not permitido:
        return render(request, "dashboard/no_autorizado.html", status=403)

    if request.method == "POST":
        nueva_cantidad_str = request.POST.get("cantidad", "").strip()
        try:
            nueva_cantidad = int(nueva_cantidad_str)
            if nueva_cantidad <= 0:
                raise ValueError
        except Exception:
            messages.error(request, "Cantidad inválida.")
            return redirect(f"/dashboard/usos/{uso.pk}/editar/")

        anterior = uso.cantidad
        diff = nueva_cantidad - anterior

        insumo = uso.insumo
        if hasattr(insumo, "stock"):
            if diff > 0 and insumo.stock < diff:
                messages.error(request, f"Stock insuficiente. Disponible: {insumo.stock}")
                return redirect(f"/dashboard/usos/{uso.pk}/editar/")
            insumo.stock -= diff
            insumo.save()

        uso.cantidad = nueva_cantidad
        uso.save()

        if getattr(uso, "egreso_id", None):
            eg = uso.egreso
            eg.cantidad = nueva_cantidad
            eg.save()

        actor = request.user.username
        _notificar_admins(
            titulo="✏️ Insumo actualizado",
            mensaje=f"{actor} actualizó un uso de insumo en {mantenimiento.cliente}.",
            url=f"/dashboard/mantenimientos/{mantenimiento.pk}/",
            enviar_push=False,
            excluir_user_id=request.user.id if es_admin(request.user) else None,
        )

        messages.success(request, "Uso de insumo actualizado correctamente.")
        return redirect(f"/dashboard/mantenimientos/{mantenimiento.pk}/")

    return render(
        request,
        "dashboard/usoinsumo_editar.html",
        {"uso": uso, "es_admin": es_admin(request.user)},
    )


@login_required
def asignar_trabajadores_view(request, pk):
    if not es_admin(request.user):
        return render(request, "dashboard/no_autorizado.html", status=403)

    mantenimiento = get_object_or_404(Mantenimiento, pk=pk)
    trabajadores = list(
        Trabajador.objects.select_related("user").all().order_by("user__username")
    )
    hoy = date.today()

    trabajadores_info = []
    for trabajador in trabajadores:
        qs_base = (
            Mantenimiento.objects.filter(trabajadores=trabajador)
            .select_related("cliente", "contrato")
            .prefetch_related("trabajadores")
        )

        qs_mismo_dia = qs_base.filter(fecha=mantenimiento.fecha).exclude(pk=mantenimiento.pk).order_by("fecha", "id")
        carga_hoy = qs_mismo_dia.count()
        atrasados = qs_base.filter(fecha__lt=hoy, estado="pendiente").exclude(pk=mantenimiento.pk).count()
        proximos = qs_base.filter(fecha__gt=hoy, estado="pendiente").exclude(pk=mantenimiento.pk).count()

        clientes_mismo_dia = [str(getattr(mh, "cliente", "") or "") for mh in qs_mismo_dia[:5]]

        carga_total = carga_hoy + atrasados + proximos

        if carga_hoy == 0 and carga_total <= 1:
            carga_label = "Más libre"
            carga_badge = "success"
            choque_label = "Sin choque"
            choque_badge = "success"
        elif carga_hoy == 1:
            carga_label = "Carga media"
            carga_badge = "warning"
            choque_label = "Ocupación media"
            choque_badge = "warning"
        elif carga_hoy >= 2:
            carga_label = "Carga alta"
            carga_badge = "danger"
            choque_label = "Posible choque"
            choque_badge = "danger"
        else:
            carga_label = "Carga media"
            carga_badge = "warning"
            choque_label = "Ocupación media"
            choque_badge = "warning"

        ya_asignado = mantenimiento.trabajadores.filter(pk=trabajador.pk).exists()

        trabajadores_info.append({
            "obj": trabajador,
            "ya_asignado": ya_asignado,
            "carga_hoy": carga_hoy,
            "atrasados": atrasados,
            "proximos": proximos,
            "carga_total": carga_total,
            "carga_label": carga_label,
            "carga_badge": carga_badge,
            "choque_label": choque_label,
            "choque_badge": choque_badge,
            "clientes_mismo_dia": clientes_mismo_dia,
            "es_recomendado": False,
        })

    trabajadores_info.sort(
        key=lambda x: (
            x["ya_asignado"] is False,
            x["carga_hoy"],
            x["atrasados"],
            x["carga_total"],
            getattr(getattr(x["obj"], "user", None), "username", ""),
        )
    )

    recomendacion = None
    candidatos = [item for item in trabajadores_info if not item["ya_asignado"]]
    if not candidatos:
        candidatos = trabajadores_info

    if candidatos:
        recomendado = min(
            candidatos,
            key=lambda x: (
                x["carga_hoy"],
                x["atrasados"],
                x["carga_total"],
                getattr(getattr(x["obj"], "user", None), "username", ""),
            ),
        )
        recomendado["es_recomendado"] = True

        razones = []
        if recomendado["carga_hoy"] == 0:
            razones.append("no tiene mantenimientos ese día")
        else:
            razones.append(f"solo tiene {recomendado['carga_hoy']} ese día")

        if recomendado["atrasados"] == 0:
            razones.append("no tiene atrasados")
        else:
            razones.append(f"tiene {recomendado['atrasados']} atrasados")

        razones.append(f"carga total visible: {recomendado['carga_total']}")

        recomendacion = {
            "trabajador": recomendado["obj"],
            "motivo": " · ".join(razones),
        }

    if request.method == "POST":
        ids = request.POST.getlist("trabajadores")
        mantenimiento.trabajadores.set(ids)

        asignados = list(mantenimiento.trabajadores.select_related("user").all())

        for trabajador in asignados:
            if getattr(trabajador, "user", None):
                _crear_notificacion(
                    user=trabajador.user,
                    titulo="🛠 Nuevo mantenimiento asignado",
                    mensaje=f"Se te asignó el mantenimiento de {mantenimiento.cliente} para {mantenimiento.fecha}.",
                    url=f"/dashboard/mantenimientos/{mantenimiento.pk}/",
                    enviar_push=True,
                )

        messages.success(request, "Trabajadores asignados correctamente.")
        return redirect("/dashboard/operativo/")

    return render(
        request,
        "dashboard/asignar_trabajadores.html",
        {
            "m": mantenimiento,
            "trabajadores": trabajadores,
            "trabajadores_info": trabajadores_info,
            "recomendacion": recomendacion,
            "es_admin": True,
        },
    )


@login_required
def flujo_mensual_view(request):
    if not es_admin(request.user):
        return render(request, "dashboard/no_autorizado.html", status=403)

    hoy = date.today()
    anio = int(request.GET.get("anio", hoy.year))
    mes = int(request.GET.get("mes", hoy.month))

    primer_dia = date(anio, mes, 1)
    ultimo_dia = date(anio, mes, monthrange(anio, mes)[1])

    ingresos_qs = Ingreso.objects.filter(fecha__range=(primer_dia, ultimo_dia)).order_by("fecha")
    egresos_qs = Egreso.objects.filter(fecha__range=(primer_dia, ultimo_dia)).order_by("fecha")

    total_ingresos = ingresos_qs.aggregate(total=Sum("total"))["total"] or 0
    total_egresos = egresos_qs.aggregate(total=Sum("total"))["total"] or 0
    balance = total_ingresos - total_egresos

    dias, ingresos_por_dia, egresos_por_dia = [], [], []
    for d in range(1, ultimo_dia.day + 1):
        fecha_d = date(anio, mes, d)
        ing_d = ingresos_qs.filter(fecha=fecha_d).aggregate(total=Sum("total"))["total"] or 0
        egr_d = egresos_qs.filter(fecha=fecha_d).aggregate(total=Sum("total"))["total"] or 0
        dias.append(str(d))
        ingresos_por_dia.append(float(ing_d))
        egresos_por_dia.append(float(egr_d))

    return render(
        request,
        "dashboard/flujo_mensual.html",
        {
            "anio": anio,
            "mes": mes,
            "primer_dia": primer_dia,
            "ultimo_dia": ultimo_dia,
            "ingresos_qs": ingresos_qs,
            "egresos_qs": egresos_qs,
            "total_ingresos": float(total_ingresos),
            "total_egresos": float(total_egresos),
            "balance": float(balance),
            "dias": dias,
            "ingresos_por_dia": ingresos_por_dia,
            "egresos_por_dia": egresos_por_dia,
            "es_admin": True,
        },
    )


@login_required
def ingreso_list_view(request):
    if not es_admin(request.user):
        return render(request, "dashboard/no_autorizado.html", status=403)

    ingresos = Ingreso.objects.all().order_by("-fecha", "-id")[:200]
    total = sum(float(i.total) for i in ingresos) if ingresos else 0

    return render(
        request,
        "dashboard/ingresos_list.html",
        {"ingresos": ingresos, "total": total, "es_admin": True},
    )


@login_required
def ingreso_crear_view(request):
    if not es_admin(request.user):
        return render(request, "dashboard/no_autorizado.html", status=403)

    if request.method == "POST":
        concepto = request.POST.get("concepto", "").strip()
        total_str = request.POST.get("total", "").strip()
        fecha_str = request.POST.get("fecha", "").strip()

        if not concepto:
            messages.error(request, "Debes escribir un concepto.")
            return redirect("/dashboard/finanzas/ingresos/nuevo/")

        try:
            total = float(total_str)
            if total <= 0:
                raise ValueError
        except Exception:
            messages.error(request, "Total inválido.")
            return redirect("/dashboard/finanzas/ingresos/nuevo/")

        fecha = parse_date(fecha_str)
        if not fecha:
            messages.error(request, "Fecha inválida.")
            return redirect("/dashboard/finanzas/ingresos/nuevo/")

        Ingreso.objects.create(concepto=concepto, total=total, fecha=fecha)
        messages.success(request, "Ingreso creado correctamente.")
        return redirect("/dashboard/finanzas/ingresos/")

    return render(request, "dashboard/ingreso_form.html", {"modo": "crear", "es_admin": True})


@login_required
def ingreso_editar_view(request, pk):
    if not es_admin(request.user):
        return render(request, "dashboard/no_autorizado.html", status=403)

    ingreso = get_object_or_404(Ingreso, pk=pk)

    if request.method == "POST":
        concepto = request.POST.get("concepto", "").strip()
        total_str = request.POST.get("total", "").strip()
        fecha_str = request.POST.get("fecha", "").strip()

        if not concepto:
            messages.error(request, "Debes escribir un concepto.")
            return redirect(f"/dashboard/finanzas/ingresos/{pk}/editar/")

        try:
            total = float(total_str)
            if total <= 0:
                raise ValueError
        except Exception:
            messages.error(request, "Total inválido.")
            return redirect(f"/dashboard/finanzas/ingresos/{pk}/editar/")

        fecha = parse_date(fecha_str)
        if not fecha:
            messages.error(request, "Fecha inválido.")
            return redirect(f"/dashboard/finanzas/ingresos/{pk}/editar/")

        ingreso.concepto = concepto
        ingreso.total = total
        ingreso.fecha = fecha
        ingreso.save()

        messages.success(request, "Ingreso actualizado.")
        return redirect("/dashboard/finanzas/ingresos/")

    return render(
        request,
        "dashboard/ingreso_form.html",
        {"modo": "editar", "ingreso": ingreso, "es_admin": True},
    )


@login_required
def ingreso_eliminar_view(request, pk):
    if not es_admin(request.user):
        return render(request, "dashboard/no_autorizado.html", status=403)

    ingreso = get_object_or_404(Ingreso, pk=pk)

    if request.method == "POST":
        ingreso.delete()
        messages.success(request, "Ingreso eliminado.")
        return redirect("/dashboard/finanzas/ingresos/")

    return render(
        request,
        "dashboard/ingreso_eliminar.html",
        {"ingreso": ingreso, "es_admin": True},
    )


def offline_view(request):
    return render(request, "dashboard/offline.html")


@require_GET
@login_required
def unread_count_view(request):
    if Notificacion is None:
        return JsonResponse({"count": 0})

    count = Notificacion.objects.filter(
        user_id=request.user.id,
        leida=False
    ).count()

    return JsonResponse({"count": count})
