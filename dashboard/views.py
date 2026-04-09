# dashboard/views.py
import json
import logging
from datetime import date, timedelta
from calendar import monthrange, monthcalendar

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.staticfiles import finders
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum
from django.db.models import F
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.templatetags.static import static
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_GET

from pywebpush import webpush, WebPushException

from trabajadores.models import Trabajador
from inventario.models import Insumo
from mantenimientos.models import Mantenimiento, UsoInsumo, FotoMantenimiento
from finanzas.models import Ingreso, Egreso, MovimientoRecurrente

try:
    from .models import PushSubscription
except Exception:
    PushSubscription = None

try:
    from .models import Notificacion
except Exception:
    Notificacion = None

try:
    from .models import ActividadSistema
except Exception:
    ActividadSistema = None

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
# Fotos requeridas
# -------------------
FOTOS_REQUERIDAS = [
    "Inicio de Mantenimiento",
    "Fin de Mantenimiento",
    "Nivel PH y Cl",
]


def _nombre_foto_valido(nombre: str) -> bool:
    return nombre in FOTOS_REQUERIDAS


# -------------------
# Helpers de fechas recurrentes
# -------------------
def _sumar_un_mes(fecha_base):
    nuevo_mes = fecha_base.month + 1
    nuevo_anio = fecha_base.year

    if nuevo_mes > 12:
        nuevo_mes = 1
        nuevo_anio += 1

    ultimo_dia = monthrange(nuevo_anio, nuevo_mes)[1]
    nuevo_dia = min(fecha_base.day, ultimo_dia)

    return date(nuevo_anio, nuevo_mes, nuevo_dia)


def _siguiente_fecha_recurrente(fecha_actual, frecuencia):
    if frecuencia == "semanal":
        return fecha_actual + timedelta(days=7)
    return _sumar_un_mes(fecha_actual)


def _inicio_fin_mes(anio, mes):
    primer_dia = date(anio, mes, 1)
    ultimo_dia = date(anio, mes, monthrange(anio, mes)[1])
    return primer_dia, ultimo_dia


def _mes_anterior(anio, mes):
    if mes == 1:
        return anio - 1, 12
    return anio, mes - 1


def _mes_siguiente(anio, mes):
    if mes == 12:
        return anio + 1, 1
    return anio, mes + 1


# -------------------
# Helpers ingresos / egresos manuales
# -------------------
def _ingreso_es_manual(ingreso):
    try:
        return bool(getattr(ingreso, "es_manual"))
    except Exception:
        pass

    cliente_id = getattr(ingreso, "cliente_id", None)
    contrato_id = getattr(ingreso, "contrato_id", None)
    return cliente_id is None and contrato_id is None


def _egreso_es_manual(egreso):
    try:
        return bool(getattr(egreso, "es_manual"))
    except Exception:
        pass

    mantenimiento_id = getattr(egreso, "mantenimiento_id", None)
    insumo_id = getattr(egreso, "insumo_id", None)
    return mantenimiento_id is None and insumo_id is None


def _crear_egreso_manual(concepto, categoria, total, fecha):
    kwargs = {
        "cantidad": 1,
        "costo_unitario": total,
        "fecha": fecha,
    }

    try:
        kwargs["mantenimiento"] = None
    except Exception:
        pass

    try:
        kwargs["insumo"] = None
    except Exception:
        pass

    if hasattr(Egreso, "concepto"):
        kwargs["concepto"] = concepto
    if hasattr(Egreso, "categoria"):
        kwargs["categoria"] = categoria or "Manual"

    egreso = Egreso.objects.create(**kwargs)
    return egreso


# -------------------
# Helpers notificaciones recurrentes
# -------------------
def _notificacion_recurrente_ya_existe_hoy(user, titulo, mensaje, url):
    if Notificacion is None:
        return False

    hoy = timezone.localdate()

    try:
        return Notificacion.objects.filter(
            user=user,
            titulo=titulo,
            mensaje=mensaje,
            url=url,
            creada_en__date=hoy,
        ).exists()
    except Exception:
        return False


def _notificacion_mantenimiento_hoy_ya_existe(user, mantenimiento):
    if Notificacion is None:
        return False

    hoy = timezone.localdate()
    titulo = "📅 Mantenimiento para hoy"
    mensaje = f"Hoy te toca el mantenimiento de {mantenimiento.cliente}."
    url = f"/dashboard/mantenimientos/{mantenimiento.pk}/"

    try:
        return Notificacion.objects.filter(
            user=user,
            titulo=titulo,
            mensaje=mensaje,
            url=url,
            creada_en__date=hoy,
        ).exists()
    except Exception:
        return False


def notificar_movimientos_recurrentes_proximos():
    """
    Recordatorio automático 1 día antes.
    Se ejecuta al entrar a vistas admin para avisar cobros/pagos próximos.
    """
    hoy = date.today()
    manana = hoy + timedelta(days=1)

    movimientos = MovimientoRecurrente.objects.filter(
        activo=True,
        proxima_fecha=manana
    ).order_by("proxima_fecha", "id")

    if not movimientos.exists():
        return

    admins = _admins_queryset()
    url = "/dashboard/finanzas/recurrentes/"

    for mov in movimientos:
        if mov.tipo == "ingreso":
            titulo = "💰 Cobro recurrente próximo"
            mensaje = (
                f"Mañana debes cobrar '{mov.concepto}' por ${mov.monto} "
                f"(fecha {mov.proxima_fecha})."
            )
        else:
            titulo = "💸 Pago recurrente próximo"
            mensaje = (
                f"Mañana debes pagar '{mov.concepto}' por ${mov.monto} "
                f"(fecha {mov.proxima_fecha})."
            )

        for admin_user in admins:
            if _notificacion_recurrente_ya_existe_hoy(admin_user, titulo, mensaje, url):
                continue

            _crear_notificacion(
                user=admin_user,
                titulo=titulo,
                mensaje=mensaje,
                url=url,
                enviar_push=True,
            )


def notificar_trabajadores_mantenimientos_hoy():
    """
    Envía notificación al trabajador el mismo día del mantenimiento.
    Evita duplicados por día/mantenimiento.
    """
    hoy = timezone.localdate()

    mantenimientos_hoy = (
        Mantenimiento.objects.filter(fecha=hoy)
        .select_related("cliente", "contrato")
        .prefetch_related("trabajadores", "trabajadores__user")
        .order_by("id")
    )

    for mantenimiento in mantenimientos_hoy:
        try:
            trabajadores = mantenimiento.trabajadores.all()
        except Exception:
            trabajadores = []

        for trabajador in trabajadores:
            user = getattr(trabajador, "user", None)
            if not user or not getattr(user, "is_active", False):
                continue

            if _notificacion_mantenimiento_hoy_ya_existe(user, mantenimiento):
                continue

            _crear_notificacion(
                user=user,
                titulo="📅 Mantenimiento para hoy",
                mensaje=f"Hoy te toca el mantenimiento de {mantenimiento.cliente}.",
                url=f"/dashboard/mantenimientos/{mantenimiento.pk}/",
                enviar_push=True,
            )


# -------------------
# Helpers calendario visual
# -------------------
def _build_calendario_mantenimientos(anio, mes, trabajador=None):
    primer_dia, ultimo_dia = _inicio_fin_mes(anio, mes)

    qs = (
        Mantenimiento.objects.filter(fecha__range=(primer_dia, ultimo_dia))
        .select_related("cliente", "contrato")
        .prefetch_related("trabajadores")
        .order_by("fecha", "estado", "id")
    )

    if trabajador is not None:
        qs = qs.filter(trabajadores=trabajador)

    mantenimientos = list(qs)

    por_fecha = {}
    for mantenimiento in mantenimientos:
        por_fecha.setdefault(mantenimiento.fecha, []).append(mantenimiento)

    semanas = []
    for semana in monthcalendar(anio, mes):
        fila = []
        for dia in semana:
            if dia == 0:
                fila.append({
                    "dia": 0,
                    "fecha": None,
                    "es_hoy": False,
                    "items": [],
                    "total": 0,
                    "realizados": 0,
                    "pendientes": 0,
                    "atrasados": 0,
                    "sin_asignar": 0,
                })
                continue

            fecha_actual = date(anio, mes, dia)
            items = por_fecha.get(fecha_actual, [])
            realizados = len([m for m in items if getattr(m, "estado", "") == "realizado"])
            pendientes = len([m for m in items if getattr(m, "estado", "") == "pendiente"])
            atrasados = len([
                m for m in items
                if getattr(m, "estado", "") == "pendiente" and fecha_actual < timezone.localdate()
            ])

            sin_asignar = 0
            for m in items:
                try:
                    if not m.trabajadores.exists():
                        sin_asignar += 1
                except Exception:
                    pass

            fila.append({
                "dia": dia,
                "fecha": fecha_actual,
                "es_hoy": fecha_actual == timezone.localdate(),
                "items": items[:4],
                "total": len(items),
                "realizados": realizados,
                "pendientes": pendientes,
                "atrasados": atrasados,
                "sin_asignar": sin_asignar,
            })
        semanas.append(fila)

    total_mes = len(mantenimientos)
    total_realizados = len([m for m in mantenimientos if getattr(m, "estado", "") == "realizado"])
    total_pendientes = len([m for m in mantenimientos if getattr(m, "estado", "") == "pendiente"])

    return {
        "anio": anio,
        "mes": mes,
        "semanas": semanas,
        "total_mes": total_mes,
        "total_realizados": total_realizados,
        "total_pendientes": total_pendientes,
    }


# -------------------
# Helpers financiero
# -------------------
def _resumen_financiero_rango(fecha_inicio, fecha_fin):
    ingresos_total = Ingreso.objects.filter(
        fecha__range=(fecha_inicio, fecha_fin)
    ).aggregate(total=Sum("total"))["total"] or 0

    egresos_total = Egreso.objects.filter(
        fecha__range=(fecha_inicio, fecha_fin)
    ).aggregate(total=Sum("total"))["total"] or 0

    balance_total = ingresos_total - egresos_total

    return {
        "ingresos": float(ingresos_total),
        "egresos": float(egresos_total),
        "balance": float(balance_total),
    }


def _variacion_porcentual(actual, anterior):
    try:
        actual = float(actual or 0)
        anterior = float(anterior or 0)
        if anterior == 0:
            if actual == 0:
                return 0.0
            return 100.0
        return round(((actual - anterior) / anterior) * 100, 2)
    except Exception:
        return 0.0


# -------------------
# Automatización de movimientos recurrentes
# -------------------
def procesar_movimientos_recurrentes():
    hoy = date.today()

    movimientos = MovimientoRecurrente.objects.filter(
        activo=True,
        proxima_fecha__lte=hoy
    ).order_by("proxima_fecha", "id")

    total_ingresos = 0
    total_egresos = 0
    movimientos_procesados = 0

    for mov in movimientos:
        generado_este_movimiento = 0

        while mov.activo and mov.proxima_fecha <= hoy:
            fecha_mov = mov.proxima_fecha

            if mov.tipo == "ingreso":
                Ingreso.objects.create(
                    concepto=mov.concepto,
                    total=mov.monto,
                    fecha=fecha_mov
                )

                total_ingresos += 1
                generado_este_movimiento += 1

                _notificar_admins(
                    titulo="💰 Ingreso recurrente generado",
                    mensaje=f"Se generó el ingreso recurrente '{mov.concepto}' por ${mov.monto} (fecha {fecha_mov}).",
                    url="/dashboard/finanzas/flujo/",
                    enviar_push=True,
                )

            elif mov.tipo == "egreso":
                _crear_egreso_manual(
                    concepto=mov.concepto,
                    categoria="Recurrente",
                    total=mov.monto,
                    fecha=fecha_mov,
                )

                total_egresos += 1
                generado_este_movimiento += 1

                _notificar_admins(
                    titulo="💸 Pago recurrente generado",
                    mensaje=f"Se registró el egreso recurrente '{mov.concepto}' por ${mov.monto} (fecha {fecha_mov}).",
                    url="/dashboard/finanzas/flujo/",
                    enviar_push=True,
                )

            mov.proxima_fecha = _siguiente_fecha_recurrente(fecha_mov, mov.frecuencia)
            mov.save(update_fields=["proxima_fecha"])

        if generado_este_movimiento > 0:
            movimientos_procesados += 1

    return {
        "movimientos_procesados": movimientos_procesados,
        "ingresos_generados": total_ingresos,
        "egresos_generados": total_egresos,
        "total_generados": total_ingresos + total_egresos,
    }


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


def _registrar_actividad(user, titulo, descripcion, url=""):
    if ActividadSistema is None:
        return None

    try:
        return ActividadSistema.objects.create(
            user=user if getattr(user, "is_authenticated", False) else None,
            titulo=titulo,
            descripcion=descripcion,
            url=url or "",
        )
    except Exception:
        logger.exception(
            "No se pudo registrar ActividadSistema para user=%s",
            getattr(user, "username", "unknown"),
        )
        return None


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
        str(getattr(mantenimiento, "observaciones", "") or ""),
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


def _clasificar_estado_trabajador(carga_hoy, atrasados, proximos):
    carga_total = carga_hoy + atrasados + proximos

    if atrasados > 0 or carga_hoy >= 3 or carga_total >= 6:
        return "saturado"
    if carga_hoy >= 2 or carga_total >= 3:
        return "media"
    return "libre"


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
        notificar_movimientos_recurrentes_proximos()
        notificar_trabajadores_mantenimientos_hoy()
        return render(request, "dashboard/home_admin.html", ctx)

    if es_trabajador(request.user):
        ctx["es_admin"] = False
        notificar_trabajadores_mantenimientos_hoy()
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
        hoy = date.today()
        notificar_movimientos_recurrentes_proximos()
        notificar_trabajadores_mantenimientos_hoy()

        total_ingresos = Ingreso.objects.aggregate(total=Sum("total"))["total"] or 0
        total_egresos = Egreso.objects.aggregate(total=Sum("total"))["total"] or 0
        balance = total_ingresos - total_egresos

        ingresos_hoy = Ingreso.objects.filter(fecha=hoy).aggregate(total=Sum("total"))["total"] or 0
        egresos_hoy = Egreso.objects.filter(fecha=hoy).aggregate(total=Sum("total"))["total"] or 0
        balance_hoy = ingresos_hoy - egresos_hoy

        primer_dia_mes_actual, ultimo_dia_mes_actual = _inicio_fin_mes(hoy.year, hoy.month)
        anio_mes_anterior, mes_mes_anterior = _mes_anterior(hoy.year, hoy.month)
        primer_dia_mes_anterior, ultimo_dia_mes_anterior = _inicio_fin_mes(anio_mes_anterior, mes_mes_anterior)

        resumen_mes_actual = _resumen_financiero_rango(primer_dia_mes_actual, ultimo_dia_mes_actual)
        resumen_mes_anterior = _resumen_financiero_rango(primer_dia_mes_anterior, ultimo_dia_mes_anterior)

        variacion_ingresos_mes = _variacion_porcentual(
            resumen_mes_actual["ingresos"],
            resumen_mes_anterior["ingresos"],
        )
        variacion_egresos_mes = _variacion_porcentual(
            resumen_mes_actual["egresos"],
            resumen_mes_anterior["egresos"],
        )
        variacion_balance_mes = _variacion_porcentual(
            resumen_mes_actual["balance"],
            resumen_mes_anterior["balance"],
        )

        recurrentes_proximos_3_dias = list(
            MovimientoRecurrente.objects.filter(
                activo=True,
                proxima_fecha__gte=hoy,
                proxima_fecha__lte=hoy + timedelta(days=3)
            ).order_by("proxima_fecha", "id")[:10]
        )

        mantenimientos_hoy_qs = (
            Mantenimiento.objects.filter(fecha=hoy)
            .select_related("cliente", "contrato")
            .prefetch_related("trabajadores")
            .order_by("estado", "id")
        )

        total_mantenimientos_hoy = mantenimientos_hoy_qs.count()
        realizados_hoy = mantenimientos_hoy_qs.filter(estado="realizado").count()
        pendientes_hoy = mantenimientos_hoy_qs.filter(estado="pendiente").count()

        trabajadores_activos_hoy = (
            mantenimientos_hoy_qs
            .filter(trabajadores__isnull=False)
            .values("trabajadores")
            .distinct()
            .count()
        )

        if total_mantenimientos_hoy > 0:
            cumplimiento_hoy = round((realizados_hoy / total_mantenimientos_hoy) * 100, 2)
        else:
            cumplimiento_hoy = 0

        if cumplimiento_hoy >= 80:
            rendimiento_estado_clase = "success"
        elif cumplimiento_hoy >= 50:
            rendimiento_estado_clase = "warning"
        else:
            rendimiento_estado_clase = "danger"

        mantenimientos_atrasados_qs = (
            Mantenimiento.objects.filter(
                fecha__lt=hoy,
                estado="pendiente",
            )
            .select_related("cliente", "contrato")
            .prefetch_related("trabajadores")
            .order_by("fecha", "id")
        )

        pendientes_sin_asignar_qs = Mantenimiento.objects.filter(
            estado="pendiente",
            trabajadores__isnull=True,
        ).distinct()

        atrasados_sin_asignar_qs = Mantenimiento.objects.filter(
            fecha__lt=hoy,
            estado="pendiente",
            trabajadores__isnull=True,
        ).distinct()

        total_atrasados = mantenimientos_atrasados_qs.count()
        total_pendientes_sin_asignar = pendientes_sin_asignar_qs.count()
        total_atrasados_sin_asignar = atrasados_sin_asignar_qs.count()

        pendientes_hoy_items = list(
            mantenimientos_hoy_qs.filter(estado="pendiente")[:5]
        )

        sin_asignar_hoy_items = list(
            mantenimientos_hoy_qs.filter(estado="pendiente", trabajadores__isnull=True).distinct()[:5]
        )

        atrasados_urgentes_items = list(
            mantenimientos_atrasados_qs[:5]
        )

        requiere_atencion_items = []
        requiere_atencion_ids = set()

        for m in list(atrasados_sin_asignar_qs[:3]):
            if m.id not in requiere_atencion_ids:
                m.es_atrasado = True
                m.sin_asignar = True
                requiere_atencion_items.append(m)
                requiere_atencion_ids.add(m.id)

        for m in sin_asignar_hoy_items:
            if m.id not in requiere_atencion_ids:
                m.es_atrasado = m.fecha < hoy
                m.sin_asignar = True
                requiere_atencion_items.append(m)
                requiere_atencion_ids.add(m.id)

        for m in atrasados_urgentes_items:
            if m.id not in requiere_atencion_ids and len(requiere_atencion_items) < 5:
                m.es_atrasado = True
                try:
                    m.sin_asignar = not m.trabajadores.exists()
                except Exception:
                    m.sin_asignar = False
                requiere_atencion_items.append(m)
                requiere_atencion_ids.add(m.id)

        total_requieren_atencion = len(requiere_atencion_items)

        atrasados = list(mantenimientos_atrasados_qs)
        dia_list = list(mantenimientos_hoy_qs)
        proximos = list(
            Mantenimiento.objects.filter(fecha__gt=hoy, estado="pendiente")
            .select_related("cliente", "contrato")
            .prefetch_related("trabajadores")
            .order_by("fecha", "id")[:50]
        )

        resumen_trabajadores = _resumen_trabajadores_desde_listas(dia_list, atrasados, proximos)

        top_trabajadores = []
        trabajadores_libres = []
        trabajadores_media = []
        trabajadores_saturados = []

        for item in resumen_trabajadores:
            carga_hoy = item.get("dia", 0)
            atrasados_t = item.get("atrasados", 0)
            proximos_t = item.get("proximos", 0)
            carga_total = carga_hoy + atrasados_t + proximos_t
            estado = _clasificar_estado_trabajador(carga_hoy, atrasados_t, proximos_t)

            trabajador_data = {
                "id": item.get("trabajadores__id"),
                "username": item.get("trabajadores__user__username"),
                "carga_hoy": carga_hoy,
                "atrasados": atrasados_t,
                "proximos": proximos_t,
                "carga_total": carga_total,
                "estado": estado,
            }

            top_trabajadores.append(trabajador_data)

            if estado == "libre":
                trabajadores_libres.append(trabajador_data)
            elif estado == "media":
                trabajadores_media.append(trabajador_data)
            else:
                trabajadores_saturados.append(trabajador_data)

        top_trabajadores = top_trabajadores[:5]
        trabajadores_libres = trabajadores_libres[:5]
        trabajadores_media = trabajadores_media[:5]
        trabajadores_saturados = trabajadores_saturados[:5]

        total_trabajadores_libres = len([
            t for t in resumen_trabajadores
            if _clasificar_estado_trabajador(t.get("dia", 0), t.get("atrasados", 0), t.get("proximos", 0)) == "libre"
        ])
        total_trabajadores_media = len([
            t for t in resumen_trabajadores
            if _clasificar_estado_trabajador(t.get("dia", 0), t.get("atrasados", 0), t.get("proximos", 0)) == "media"
        ])
        total_trabajadores_saturados = len([
            t for t in resumen_trabajadores
            if _clasificar_estado_trabajador(t.get("dia", 0), t.get("atrasados", 0), t.get("proximos", 0)) == "saturado"
        ])

        trabajador_recomendado = None
        candidatos_recomendados = []

        for item in resumen_trabajadores:
            carga_hoy = item.get("dia", 0)
            atrasados_t = item.get("atrasados", 0)
            proximos_t = item.get("proximos", 0)
            estado = _clasificar_estado_trabajador(carga_hoy, atrasados_t, proximos_t)

            if estado != "saturado":
                candidatos_recomendados.append({
                    "id": item.get("trabajadores__id"),
                    "username": item.get("trabajadores__user__username"),
                    "carga_hoy": carga_hoy,
                    "atrasados": atrasados_t,
                    "proximos": proximos_t,
                    "carga_total": carga_hoy + atrasados_t + proximos_t,
                })

        if candidatos_recomendados:
            mejor = min(
                candidatos_recomendados,
                key=lambda x: (x["atrasados"], x["carga_hoy"], x["carga_total"], x["username"])
            )

            razones = []
            if mejor["carga_hoy"] == 0:
                razones.append("sin mantenimientos hoy")
            elif mejor["carga_hoy"] == 1:
                razones.append("solo tiene 1 mantenimiento hoy")
            else:
                razones.append(f"tiene {mejor['carga_hoy']} mantenimientos hoy")

            if mejor["atrasados"] == 0:
                razones.append("sin atrasados")
            else:
                razones.append(f"{mejor['atrasados']} atrasados")

            razones.append(f"carga total {mejor['carga_total']}")

            mejor["motivo"] = " · ".join(razones)
            trabajador_recomendado = mejor

        actividades_recientes = []
        if ActividadSistema is not None:
            actividades_recientes = list(ActividadSistema.objects.select_related("user").all()[:5])

        grafico_finanzas = {
            "labels": ["Ingresos", "Egresos", "Balance"],
            "data": [
                float(resumen_mes_actual.get("ingresos", 0) or 0),
                float(resumen_mes_actual.get("egresos", 0) or 0),
                float(resumen_mes_actual.get("balance", 0) or 0),
            ],
        }
        grafico_operativo = {
            "labels": ["Realizados hoy", "Pendientes hoy", "Atrasados", "Sin asignar"],
            "data": [
                int(realizados_hoy),
                int(pendientes_hoy),
                int(total_atrasados),
                int(total_pendientes_sin_asignar),
            ],
        }

        ctx = {
            **base_ctx,
            "modo": "admin",
            "hoy": hoy,
            "total_ingresos": float(total_ingresos),
            "total_egresos": float(total_egresos),
            "balance": float(balance),
            "ingresos_hoy": float(ingresos_hoy),
            "egresos_hoy": float(egresos_hoy),
            "balance_hoy": float(balance_hoy),
            "resumen_mes_actual": resumen_mes_actual,
            "resumen_mes_anterior": resumen_mes_anterior,
            "variacion_ingresos_mes": variacion_ingresos_mes,
            "variacion_egresos_mes": variacion_egresos_mes,
            "variacion_balance_mes": variacion_balance_mes,
            "recurrentes_proximos_3_dias": recurrentes_proximos_3_dias,
            "total_mantenimientos_hoy": total_mantenimientos_hoy,
            "realizados_hoy": realizados_hoy,
            "pendientes_hoy": pendientes_hoy,
            "trabajadores_activos_hoy": trabajadores_activos_hoy,
            "cumplimiento_hoy": cumplimiento_hoy,
            "rendimiento_estado_clase": rendimiento_estado_clase,
            "total_atrasados": total_atrasados,
            "total_pendientes_sin_asignar": total_pendientes_sin_asignar,
            "total_atrasados_sin_asignar": total_atrasados_sin_asignar,
            "pendientes_hoy_items": pendientes_hoy_items,
            "sin_asignar_hoy_items": sin_asignar_hoy_items,
            "atrasados_urgentes_items": atrasados_urgentes_items,
            "requiere_atencion_items": requiere_atencion_items,
            "total_requieren_atencion": total_requieren_atencion,
            "top_trabajadores": top_trabajadores,
            "trabajadores_libres": trabajadores_libres,
            "trabajadores_media": trabajadores_media,
            "trabajadores_saturados": trabajadores_saturados,
            "total_trabajadores_libres": total_trabajadores_libres,
            "total_trabajadores_media": total_trabajadores_media,
            "total_trabajadores_saturados": total_trabajadores_saturados,
            "trabajador_recomendado": trabajador_recomendado,
            "hay_alertas_operativas": (
                total_atrasados > 0
                or total_pendientes_sin_asignar > 0
                or total_atrasados_sin_asignar > 0
            ),
            "actividades_recientes": actividades_recientes,
            "grafico_finanzas": json.dumps(grafico_finanzas),
            "grafico_operativo": json.dumps(grafico_operativo),
            "es_admin": True,
        }
        return render(request, "dashboard/dashboard.html", ctx)

    if es_trabajador(request.user):
        hoy = date.today()
        notificar_trabajadores_mantenimientos_hoy()

        try:
            trabajador = request.user.trabajador
        except Exception:
            return render(request, "dashboard/no_autorizado.html", status=403)

        anio_cal = int(request.GET.get("anio_cal", hoy.year))
        mes_cal = int(request.GET.get("mes_cal", hoy.month))
        anio_cal_ant, mes_cal_ant = _mes_anterior(anio_cal, mes_cal)
        anio_cal_sig, mes_cal_sig = _mes_siguiente(anio_cal, mes_cal)

        calendario_trabajador = _build_calendario_mantenimientos(anio_cal, mes_cal, trabajador=trabajador)

        mantenimientos_hoy = (
            Mantenimiento.objects.filter(fecha=hoy, trabajadores=trabajador)
            .select_related("cliente", "contrato")
            .order_by("estado", "fecha")
        )

        ver_mas_proximos = request.GET.get("ver_mas_proximos") == "1"

        qs_mantenimientos_proximos = (
            Mantenimiento.objects.filter(fecha__gt=hoy, trabajadores=trabajador)
            .select_related("cliente", "contrato")
            .order_by("fecha")
        )
        total_proximos_reales = qs_mantenimientos_proximos.count()

        if ver_mas_proximos:
            mantenimientos_proximos = qs_mantenimientos_proximos
        else:
            mantenimientos_proximos = qs_mantenimientos_proximos[:10]

        mantenimientos_atrasados = (
            Mantenimiento.objects.filter(
                fecha__lt=hoy,
                estado="pendiente",
                trabajadores=trabajador
            )
            .select_related("cliente", "contrato")
            .order_by("fecha", "id")[:20]
        )

        ctx = {
            **base_ctx,
            "modo": "trabajador",
            "hoy": hoy,
            "mantenimientos_hoy": mantenimientos_hoy,
            "mantenimientos_proximos": mantenimientos_proximos,
            "total_proximos_reales": total_proximos_reales,
            "mostrar_boton_ver_mas_proximos": total_proximos_reales > 10,
            "ver_mas_proximos": ver_mas_proximos,
            "mantenimientos_atrasados": mantenimientos_atrasados,
            "anio_cal": anio_cal,
            "mes_cal": mes_cal,
            "anio_cal_ant": anio_cal_ant,
            "mes_cal_ant": mes_cal_ant,
            "anio_cal_sig": anio_cal_sig,
            "mes_cal_sig": mes_cal_sig,
            "calendario_trabajador": calendario_trabajador,
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


@login_required
def actividad_historial_view(request):
    if not es_admin(request.user):
        return render(request, "dashboard/no_autorizado.html", status=403)

    if ActividadSistema is None:
        page_obj = None
    else:
        qs = ActividadSistema.objects.select_related("user").all()
        paginator = Paginator(qs, 20)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

    return render(
        request,
        "dashboard/actividad_historial.html",
        {
            "page_obj": page_obj,
            "es_admin": True,
        },
    )


# -------------------
# Historial mantenimientos
# -------------------
@login_required
def mantenimiento_historial_view(request):
    if not es_admin(request.user):
        return render(request, "dashboard/no_autorizado.html", status=403)

    hoy = date.today()

    q = (request.GET.get("q", "") or "").strip()
    estado = (request.GET.get("estado", "") or "").strip().lower()
    filtro = (request.GET.get("filtro", "") or "").strip().lower()
    cliente_id = (request.GET.get("cliente", "") or "").strip()
    trabajador_id = (request.GET.get("trabajador", "") or "").strip()
    fecha_desde_str = (request.GET.get("fecha_desde", "") or "").strip()
    fecha_hasta_str = (request.GET.get("fecha_hasta", "") or "").strip()

    fecha_desde = parse_date(fecha_desde_str) if fecha_desde_str else None
    fecha_hasta = parse_date(fecha_hasta_str) if fecha_hasta_str else None

    qs = (
        Mantenimiento.objects
        .select_related("cliente", "contrato")
        .prefetch_related("trabajadores")
        .order_by("-fecha", "-id")
    )

    if filtro == "hoy":
        qs = qs.filter(fecha=hoy)
    elif filtro == "pendientes":
        qs = qs.filter(estado="pendiente")
        estado = "pendiente"
    elif filtro == "realizados":
        qs = qs.filter(estado="realizado")
        estado = "realizado"
    elif filtro == "atrasados":
        qs = qs.filter(fecha__lt=hoy, estado="pendiente")
    elif filtro == "sin_asignar":
        qs = qs.filter(trabajadores__isnull=True).distinct()

    if estado in ["pendiente", "realizado"]:
        qs = qs.filter(estado=estado)

    if cliente_id.isdigit():
        qs = qs.filter(cliente_id=int(cliente_id))

    if trabajador_id.isdigit():
        qs = qs.filter(trabajadores__id=int(trabajador_id))

    if fecha_desde:
        qs = qs.filter(fecha__gte=fecha_desde)

    if fecha_hasta:
        qs = qs.filter(fecha__lte=fecha_hasta)

    qs = qs.distinct()
    items = list(qs)

    if q:
        items = _filtrar_mantenimientos_por_busqueda(items, q)

    total_historial = len(items)
    total_realizados_historial = len([m for m in items if getattr(m, "estado", "") == "realizado"])
    total_pendientes_historial = len([m for m in items if getattr(m, "estado", "") == "pendiente"])
    total_atrasados_historial = len([
        m for m in items
        if getattr(m, "estado", "") == "pendiente" and getattr(m, "fecha", hoy) < hoy
    ])
    total_sin_asignar_historial = len([
        m for m in items
        if not m.trabajadores.exists()
    ])

    paginator = Paginator(items, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    clientes_filtro = []
    clientes_ids = set()
    for m in Mantenimiento.objects.select_related("cliente").all().order_by("cliente_id"):
        cid = getattr(m, "cliente_id", None)
        if cid and cid not in clientes_ids:
            clientes_ids.add(cid)
            clientes_filtro.append({
                "id": cid,
                "nombre": str(getattr(m, "cliente", "")),
            })

    trabajadores_filtro = list(
        Trabajador.objects.select_related("user").all().order_by("user__username")
    )

    query_params = request.GET.copy()
    if "page" in query_params:
        query_params.pop("page")
    querystring = query_params.urlencode()

    return render(
        request,
        "dashboard/mantenimientos_historial.html",
        {
            "page_obj": page_obj,
            "q": q,
            "estado": estado,
            "filtro": filtro,
            "cliente_id": cliente_id,
            "trabajador_id": trabajador_id,
            "fecha_desde": fecha_desde_str,
            "fecha_hasta": fecha_hasta_str,
            "clientes_filtro": clientes_filtro,
            "trabajadores_filtro": trabajadores_filtro,
            "total_historial": total_historial,
            "total_realizados_historial": total_realizados_historial,
            "total_pendientes_historial": total_pendientes_historial,
            "total_atrasados_historial": total_atrasados_historial,
            "total_sin_asignar_historial": total_sin_asignar_historial,
            "querystring": querystring,
            "es_admin": True,
        },
    )


# -------------------
# Operativo Admin
# -------------------
@login_required
def admin_operativo_view(request):
    if not es_admin(request.user):
        return render(request, "dashboard/no_autorizado.html", status=403)

    hoy = date.today()
    filtro = (request.GET.get("filtro", "") or "").strip().lower()
    q = (request.GET.get("q", "") or "").strip()
    ver_mas_proximos = (request.GET.get("ver_mas_proximos", "") or "").strip() == "1"

    anio_cal = int(request.GET.get("anio_cal", hoy.year))
    mes_cal = int(request.GET.get("mes_cal", hoy.month))
    anio_cal_ant, mes_cal_ant = _mes_anterior(anio_cal, mes_cal)
    anio_cal_sig, mes_cal_sig = _mes_siguiente(anio_cal, mes_cal)

    base_qs = (
        Mantenimiento.objects
        .select_related("cliente", "contrato")
        .prefetch_related("trabajadores")
        .order_by("fecha", "estado", "id")
    )

    if filtro == "atrasados":
        dia_list = []
        atrasados = list(
            base_qs.filter(
                fecha__lt=hoy,
                estado="pendiente"
            )
        )
        proximos = []
        etiqueta_periodo = "Mantenimientos atrasados"

    elif filtro == "sin_asignar":
        dia_list = list(
            base_qs.filter(
                fecha=hoy,
                estado="pendiente",
                trabajadores__isnull=True
            ).distinct()
        )
        atrasados = list(
            base_qs.filter(
                fecha__lt=hoy,
                estado="pendiente",
                trabajadores__isnull=True
            ).distinct()
        )
        proximos = []
        etiqueta_periodo = "Mantenimientos sin asignar"

    elif filtro == "pendientes_hoy":
        dia_list = list(
            base_qs.filter(
                fecha=hoy,
                estado="pendiente"
            )
        )
        atrasados = []
        proximos = []
        etiqueta_periodo = "Pendientes de hoy"

    elif filtro == "urgentes":
        dia_list = list(
            base_qs.filter(
                fecha=hoy,
                estado="pendiente",
                trabajadores__isnull=True
            ).distinct()
        )
        atrasados = list(
            base_qs.filter(
                fecha__lt=hoy,
                estado="pendiente"
            )
        )
        proximos = []
        etiqueta_periodo = "Requieren atención inmediata"

    else:
        dia_list = list(
            base_qs.filter(fecha=hoy)
        )
        atrasados = list(
            base_qs.filter(
                fecha__lt=hoy,
                estado="pendiente"
            )
        )

        limite_proximos = None if ver_mas_proximos else 10
        qs_proximos = base_qs.filter(
            fecha__gt=hoy,
            estado="pendiente"
        )

        if limite_proximos is not None:
            qs_proximos = qs_proximos[:limite_proximos]

        proximos = list(qs_proximos)
        etiqueta_periodo = "Operativo de hoy"

    if q:
        dia_list = _filtrar_mantenimientos_por_busqueda(dia_list, q)
        atrasados = _filtrar_mantenimientos_por_busqueda(atrasados, q)
        proximos = _filtrar_mantenimientos_por_busqueda(proximos, q)

    resumen_trabajadores = _resumen_trabajadores_desde_listas(dia_list, atrasados, proximos)

    sin_asignar_dia = _sin_asignar_count(dia_list)
    sin_asignar_atrasados = _sin_asignar_count(atrasados)
    sin_asignar_proximos = _sin_asignar_count(proximos)

    total_sin_asignar = (
        sin_asignar_dia +
        sin_asignar_atrasados +
        sin_asignar_proximos
    )

    calendario_operativo = _build_calendario_mantenimientos(anio_cal, mes_cal)

    total_proximos_reales = base_qs.filter(fecha__gt=hoy, estado="pendiente").count()
    mostrar_boton_ver_mas_proximos = (
        not filtro and not ver_mas_proximos and total_proximos_reales > 10
    )

    return render(
        request,
        "dashboard/admin_operativo.html",
        {
            "hoy": hoy,
            "q": q,
            "modo_actual": filtro,
            "etiqueta_periodo": etiqueta_periodo,
            "dia_list": dia_list,
            "atrasados": atrasados,
            "proximos": proximos,
            "resumen_trabajadores": resumen_trabajadores,
            "sin_asignar_dia": sin_asignar_dia,
            "sin_asignar_atrasados": sin_asignar_atrasados,
            "sin_asignar_proximos": sin_asignar_proximos,
            "total_sin_asignar": total_sin_asignar,
            "anio_cal": anio_cal,
            "mes_cal": mes_cal,
            "anio_cal_ant": anio_cal_ant,
            "mes_cal_ant": mes_cal_ant,
            "anio_cal_sig": anio_cal_sig,
            "mes_cal_sig": mes_cal_sig,
            "calendario_operativo": calendario_operativo,
            "ver_mas_proximos": ver_mas_proximos,
            "mostrar_boton_ver_mas_proximos": mostrar_boton_ver_mas_proximos,
            "total_proximos_reales": total_proximos_reales,
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

    es_usuario_admin = es_admin(request.user)
    insumos = Insumo.objects.all().order_by("nombre")
    esta_realizado = mantenimiento.estado == "realizado"

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
            fotos_qs_validacion = mantenimiento.fotos.all()
            fotos_por_nombre_validacion = {
                f.descripcion: f for f in fotos_qs_validacion if _nombre_foto_valido(f.descripcion)
            }
            cantidad_fotos_requeridas = len(fotos_por_nombre_validacion)

            if cantidad_fotos_requeridas < 3:
                messages.error(
                    request,
                    "Debes subir las 3 fotos requeridas antes de marcar como realizado."
                )
                return redirect(safe_return_url())

            mantenimiento.estado = "realizado"
            mantenimiento.save(update_fields=["estado"])

            actor = request.user.username
            _notificar_admins(
                titulo="✅ Mantenimiento realizado",
                mensaje=f"El mantenimiento de {mantenimiento.cliente} fue marcado como realizado por {actor}.",
                url=f"/dashboard/mantenimientos/{mantenimiento.pk}/",
                enviar_push=True,
                excluir_user_id=request.user.id if es_usuario_admin else None,
            )
            _registrar_actividad(
                user=request.user,
                titulo="Mantenimiento realizado",
                descripcion=f"{actor} marcó como realizado el mantenimiento de {mantenimiento.cliente}.",
                url=f"/dashboard/mantenimientos/{mantenimiento.pk}/",
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
                excluir_user_id=request.user.id if es_usuario_admin else None,
            )
            _registrar_actividad(
                user=request.user,
                titulo="Mantenimiento pendiente",
                descripcion=f"{actor} marcó como pendiente el mantenimiento de {mantenimiento.cliente}.",
                url=f"/dashboard/mantenimientos/{mantenimiento.pk}/",
            )

            messages.success(request, f"Mantenimiento de {mantenimiento.cliente} marcado como pendiente.")
            return redirect(safe_return_url())

        if esta_realizado:
            messages.error(request, "Este mantenimiento está realizado y bloqueado para cambios. Debes volverlo a pendiente para editarlo.")
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
                excluir_user_id=request.user.id if es_usuario_admin else None,
            )
            _registrar_actividad(
                user=request.user,
                titulo="Insumo registrado",
                descripcion=f"{actor} registró {insumo.nombre} x {cantidad} en el mantenimiento de {mantenimiento.cliente}.",
                url=f"/dashboard/mantenimientos/{mantenimiento.pk}/",
            )

            messages.success(request, f"Insumo registrado: {insumo.nombre} x {cantidad}")
            return redirect(f"/dashboard/mantenimientos/{mantenimiento.pk}/")

        if accion == "subir_fotos_requeridas":
            if esta_realizado:
                messages.error(request, "Este mantenimiento está realizado y bloqueado para cambios. Debes volverlo a pendiente para editarlo.")
                return redirect(safe_return_url())

            mapa_fotos = [
                ("Inicio de Mantenimiento", request.FILES.get("foto_inicio")),
                ("Fin de Mantenimiento", request.FILES.get("foto_fin")),
                ("Nivel PH y Cl", request.FILES.get("foto_nivel")),
            ]

            existentes = {
                f.descripcion: f
                for f in mantenimiento.fotos.all()
                if _nombre_foto_valido(f.descripcion)
            }

            subidas = []
            omitidas = []

            for tipo_foto, imagen in mapa_fotos:
                if not imagen:
                    continue

                if tipo_foto in existentes:
                    omitidas.append(tipo_foto)
                    continue

                FotoMantenimiento.objects.create(
                    mantenimiento=mantenimiento,
                    imagen=imagen,
                    descripcion=tipo_foto,
                )
                subidas.append(tipo_foto)

            if subidas:
                actor = request.user.username
                detalle = ", ".join(subidas)
                _notificar_admins(
                    titulo="📸 Fotos requeridas subidas",
                    mensaje=f"{actor} subió fotos en el mantenimiento de {mantenimiento.cliente}: {detalle}.",
                    url=f"/dashboard/mantenimientos/{mantenimiento.pk}/",
                    enviar_push=False,
                    excluir_user_id=request.user.id if es_usuario_admin else None,
                )
                _registrar_actividad(
                    user=request.user,
                    titulo="Fotos requeridas subidas",
                    descripcion=f"{actor} subió fotos en el mantenimiento de {mantenimiento.cliente}: {detalle}.",
                    url=f"/dashboard/mantenimientos/{mantenimiento.pk}/",
                )

            if subidas and omitidas:
                messages.success(
                    request,
                    f"Se subieron {len(subidas)} foto(s). Ya existían: {', '.join(omitidas)}."
                )
            elif subidas:
                messages.success(
                    request,
                    f"Se subieron correctamente {len(subidas)} foto(s)."
                )
            elif omitidas:
                messages.warning(
                    request,
                    f"No se subieron nuevas fotos porque ya existían: {', '.join(omitidas)}."
                )
            else:
                messages.error(
                    request,
                    "Debes seleccionar al menos una foto para subir."
                )

            return redirect(f"/dashboard/mantenimientos/{mantenimiento.pk}/")

        if accion == "subir_foto":
            imagen = request.FILES.get("imagen")
            tipo_foto = (request.POST.get("tipo_foto", "") or "").strip()

            if not imagen:
                messages.error(request, "Debes seleccionar una imagen.")
                return redirect(f"/dashboard/mantenimientos/{mantenimiento.pk}/")

            if not _nombre_foto_valido(tipo_foto):
                messages.error(request, "Tipo de foto inválido.")
                return redirect(f"/dashboard/mantenimientos/{mantenimiento.pk}/")

            cantidad_fotos_actual = mantenimiento.fotos.count()
            if cantidad_fotos_actual >= 3 and not mantenimiento.fotos.filter(descripcion=tipo_foto).exists():
                messages.error(request, "Solo se permiten máximo 3 fotos por mantenimiento.")
                return redirect(f"/dashboard/mantenimientos/{mantenimiento.pk}/")

            foto_existente = mantenimiento.fotos.filter(descripcion=tipo_foto).first()
            if foto_existente:
                messages.error(request, f"La foto '{tipo_foto}' ya fue subida. Si deseas cambiarla, elimínala primero.")
                return redirect(f"/dashboard/mantenimientos/{mantenimiento.pk}/")

            FotoMantenimiento.objects.create(
                mantenimiento=mantenimiento,
                imagen=imagen,
                descripcion=tipo_foto,
            )

            actor = request.user.username
            _notificar_admins(
                titulo="📸 Nueva foto subida",
                mensaje=f"{actor} subió la foto '{tipo_foto}' en el mantenimiento de {mantenimiento.cliente}.",
                url=f"/dashboard/mantenimientos/{mantenimiento.pk}/",
                enviar_push=False,
                excluir_user_id=request.user.id if es_usuario_admin else None,
            )
            _registrar_actividad(
                user=request.user,
                titulo="Foto subida",
                descripcion=f"{actor} subió la foto '{tipo_foto}' al mantenimiento de {mantenimiento.cliente}.",
                url=f"/dashboard/mantenimientos/{mantenimiento.pk}/",
            )

            messages.success(request, f"Foto subida correctamente: {tipo_foto}.")
            return redirect(f"/dashboard/mantenimientos/{mantenimiento.pk}/")

    lista_usos = mantenimiento.usos_insumos.all()
    lista_egresos = mantenimiento.egresos.all() if hasattr(mantenimiento, "egresos") else []
    total_egresos = sum(e.total for e in lista_egresos) if lista_egresos else 0

    fotos_qs = mantenimiento.fotos.all()
    fotos_por_nombre = {f.descripcion: f for f in fotos_qs if _nombre_foto_valido(f.descripcion)}
    fotos = [fotos_por_nombre[nombre] for nombre in FOTOS_REQUERIDAS if nombre in fotos_por_nombre]

    historial_cliente_reciente = []
    if es_usuario_admin:
        historial_cliente_reciente = (
            Mantenimiento.objects
            .filter(cliente=mantenimiento.cliente)
            .exclude(pk=mantenimiento.pk)
            .select_related("cliente", "contrato")
            .prefetch_related("trabajadores")
            .order_by("-fecha", "-id")[:5]
        )

    cantidad_fotos = len(fotos)
    cantidad_usos = lista_usos.count()
    puede_cerrar = cantidad_fotos == 3
    puede_subir_fotos = cantidad_fotos < 3 and not esta_realizado

    foto_inicio = fotos_por_nombre.get("Inicio de Mantenimiento")
    foto_fin = fotos_por_nombre.get("Fin de Mantenimiento")
    foto_nivel = fotos_por_nombre.get("Nivel PH y Cl")

    return render(
        request,
        "dashboard/mantenimiento_detalle.html",
        {
            "m": mantenimiento,
            "insumos": insumos,
            "lista_usos": lista_usos,
            "lista_egresos": lista_egresos,
            "total_egresos": total_egresos,
            "es_admin": es_usuario_admin,
            "fotos": fotos,
            "cantidad_fotos": cantidad_fotos,
            "cantidad_usos": cantidad_usos,
            "puede_cerrar": puede_cerrar,
            "puede_subir_fotos": puede_subir_fotos,
            "esta_realizado": esta_realizado,
            "foto_inicio": foto_inicio,
            "foto_fin": foto_fin,
            "foto_nivel": foto_nivel,
            "historial_cliente_reciente": historial_cliente_reciente,
        },
    )


@login_required
def foto_mantenimiento_eliminar_view(request, pk):
    foto = get_object_or_404(FotoMantenimiento, pk=pk)
    mantenimiento = foto.mantenimiento

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

    if mantenimiento.estado == "realizado":
        messages.error(request, "Este mantenimiento está realizado y bloqueado para cambios. Debes volverlo a pendiente para editarlo.")
        return redirect(f"/dashboard/mantenimientos/{mantenimiento.pk}/")

    if request.method == "POST":
        actor = request.user.username
        cliente_nombre = str(mantenimiento.cliente)
        foto_id = foto.pk
        foto_nombre = foto.descripcion or "foto"

        try:
            if foto.imagen:
                foto.imagen.delete(save=False)
        except Exception:
            logger.exception("No se pudo borrar el archivo físico de la foto id=%s", foto_id)

        foto.delete()

        _notificar_admins(
            titulo="🗑 Foto eliminada",
            mensaje=f"{actor} eliminó la foto '{foto_nombre}' del mantenimiento de {cliente_nombre}.",
            url=f"/dashboard/mantenimientos/{mantenimiento.pk}/",
            enviar_push=False,
            excluir_user_id=request.user.id if es_admin(request.user) else None,
        )
        _registrar_actividad(
            user=request.user,
            titulo="Foto eliminada",
            descripcion=f"{actor} eliminó la foto '{foto_nombre}' del mantenimiento de {cliente_nombre}.",
            url=f"/dashboard/mantenimientos/{mantenimiento.pk}/",
        )

        messages.success(request, "Foto eliminada correctamente.")
        return redirect(f"/dashboard/mantenimientos/{mantenimiento.pk}/")

    return redirect(f"/dashboard/mantenimientos/{mantenimiento.pk}/")


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

    if mantenimiento.estado == "realizado":
        messages.error(request, "Este mantenimiento está realizado y bloqueado para cambios. Debes volverlo a pendiente para editarlo.")
        return redirect(f"/dashboard/mantenimientos/{mantenimiento.pk}/")

    if request.method == "POST":
        insumo = uso.insumo
        insumo_nombre = getattr(insumo, "nombre", "Insumo")
        cantidad = uso.cantidad

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
        _registrar_actividad(
            user=request.user,
            titulo="Insumo eliminado",
            descripcion=f"{actor} eliminó {insumo_nombre} x {cantidad} del mantenimiento de {mantenimiento.cliente}.",
            url=f"/dashboard/mantenimientos/{mantenimiento.pk}/",
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

    if mantenimiento.estado == "realizado":
        messages.error(request, "Este mantenimiento está realizado y bloqueado para cambios. Debes volverlo a pendiente para editarlo.")
        return redirect(f"/dashboard/mantenimientos/{mantenimiento.pk}/")

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
        insumo_nombre = getattr(insumo, "nombre", "Insumo")

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
        _registrar_actividad(
            user=request.user,
            titulo="Insumo actualizado",
            descripcion=f"{actor} actualizó {insumo_nombre} de {anterior} a {nueva_cantidad} en el mantenimiento de {mantenimiento.cliente}.",
            url=f"/dashboard/mantenimientos/{mantenimiento.pk}/",
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
        nombres_asignados = []

        for trabajador in asignados:
            if getattr(trabajador, "user", None):
                nombres_asignados.append(trabajador.user.username)
                _crear_notificacion(
                    user=trabajador.user,
                    titulo="🛠 Nuevo mantenimiento asignado",
                    mensaje=f"Se te asignó el mantenimiento de {mantenimiento.cliente} para {mantenimiento.fecha}.",
                    url=f"/dashboard/mantenimientos/{mantenimiento.pk}/",
                    enviar_push=True,
                )

        actor = request.user.username
        detalle = ", ".join(nombres_asignados) if nombres_asignados else "sin trabajadores"
        _registrar_actividad(
            user=request.user,
            titulo="Trabajadores asignados",
            descripcion=f"{actor} actualizó la asignación del mantenimiento de {mantenimiento.cliente}: {detalle}.",
            url=f"/dashboard/mantenimientos/{mantenimiento.pk}/",
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
    hoy = timezone.localdate()

    try:
        anio = int(request.GET.get("anio", hoy.year))
        mes = int(request.GET.get("mes", hoy.month))
    except ValueError:
        anio, mes = hoy.year, hoy.month

    primer_dia = date(anio, mes, 1)
    ultimo_dia = date(anio, mes, monthrange(anio, mes)[1])

    ingresos_qs = Ingreso.objects.filter(fecha__range=(primer_dia, ultimo_dia)).order_by("-fecha", "-id")
    egresos_qs = Egreso.objects.filter(fecha__range=(primer_dia, ultimo_dia)).order_by("-fecha", "-id")

    ingresos_manuales_qs = ingresos_qs.filter(cliente__isnull=True, contrato__isnull=True)
    egresos_manuales_qs = egresos_qs.filter(mantenimiento__isnull=True, insumo__isnull=True)

    total_ingresos = ingresos_qs.aggregate(total=Sum("total"))["total"] or Decimal("0")
    total_egresos = egresos_qs.aggregate(total=Sum("total"))["total"] or Decimal("0")

    total_ingresos_manuales = ingresos_manuales_qs.aggregate(total=Sum("total"))["total"] or Decimal("0")
    total_egresos_manuales = egresos_manuales_qs.aggregate(total=Sum("total"))["total"] or Decimal("0")

    total_ingresos_automaticos = total_ingresos - total_ingresos_manuales
    total_egresos_automaticos = total_egresos - total_egresos_manuales

    balance = total_ingresos - total_egresos

    # 📊 MES ANTERIOR
    mes_anterior = mes - 1 or 12
    anio_anterior = anio - 1 if mes == 1 else anio

    primer_dia_ant = date(anio_anterior, mes_anterior, 1)
    ultimo_dia_ant = date(anio_anterior, mes_anterior, monthrange(anio_anterior, mes_anterior)[1])

    ingresos_ant = Ingreso.objects.filter(fecha__range=(primer_dia_ant, ultimo_dia_ant))
    egresos_ant = Egreso.objects.filter(fecha__range=(primer_dia_ant, ultimo_dia_ant))

    total_ingresos_ant = ingresos_ant.aggregate(total=Sum("total"))["total"] or Decimal("0")
    total_egresos_ant = egresos_ant.aggregate(total=Sum("total"))["total"] or Decimal("0")

    balance_ant = total_ingresos_ant - total_egresos_ant

    def variacion(actual, anterior):
        if anterior == 0:
            return 100 if actual > 0 else 0
        return ((actual - anterior) / anterior) * 100

    variacion_ingresos_mes = variacion(total_ingresos, total_ingresos_ant)
    variacion_egresos_mes = variacion(total_egresos, total_egresos_ant)
    variacion_balance_mes = variacion(balance, balance_ant)

    # 📅 RESUMEN DIARIO
    resumen_diario = []
    balance_acumulado = Decimal("0")

    dias = monthrange(anio, mes)[1]
    for dia in range(1, dias + 1):
        fecha = date(anio, mes, dia)

        ingresos_dia = ingresos_qs.filter(fecha=fecha).aggregate(total=Sum("total"))["total"] or Decimal("0")
        egresos_dia = egresos_qs.filter(fecha=fecha).aggregate(total=Sum("total"))["total"] or Decimal("0")

        balance_dia = ingresos_dia - egresos_dia
        balance_acumulado += balance_dia

        resumen_diario.append({
            "dia": dia,
            "ingresos": ingresos_dia,
            "egresos": egresos_dia,
            "balance_acumulado": balance_acumulado,
        })

    # 🏆 TOP
    top_ingresos = ingresos_qs.order_by("-total")[:5]
    top_egresos = egresos_qs.order_by("-total")[:5]

    # 🔥 FECHAS PARA REPORTE PRO
    fecha_inicio_reporte = primer_dia.strftime("%Y-%m-%d")
    fecha_fin_reporte = ultimo_dia.strftime("%Y-%m-%d")

    return render(request, "dashboard/flujo_mensual.html", {
        "anio": anio,
        "mes": mes,
        "primer_dia": primer_dia,

        "ingresos_qs": ingresos_qs,
        "egresos_qs": egresos_qs,

        "ingresos_manuales_qs": ingresos_manuales_qs,
        "egresos_manuales_qs": egresos_manuales_qs,

        "total_ingresos": total_ingresos,
        "total_egresos": total_egresos,

        "total_ingresos_manuales": total_ingresos_manuales,
        "total_egresos_manuales": total_egresos_manuales,

        "total_ingresos_automaticos": total_ingresos_automaticos,
        "total_egresos_automaticos": total_egresos_automaticos,

        "balance": balance,

        "resumen_mes_actual": {
            "ingresos": total_ingresos,
            "egresos": total_egresos,
            "balance": balance,
        },
        "resumen_mes_anterior": {
            "ingresos": total_ingresos_ant,
            "egresos": total_egresos_ant,
            "balance": balance_ant,
        },

        "variacion_ingresos_mes": variacion_ingresos_mes,
        "variacion_egresos_mes": variacion_egresos_mes,
        "variacion_balance_mes": variacion_balance_mes,

        "resumen_diario": resumen_diario,

        "top_ingresos": top_ingresos,
        "top_egresos": top_egresos,

        # 🔥 NUEVO
        "fecha_inicio_reporte": fecha_inicio_reporte,
        "fecha_fin_reporte": fecha_fin_reporte,
    })


@login_required
def egreso_manual_crear_view(request):
    if not es_admin(request.user):
        return render(request, "dashboard/no_autorizado.html", status=403)

    if request.method != "POST":
        return redirect("/dashboard/finanzas/flujo/")

    concepto = (request.POST.get("concepto", "") or "").strip()
    categoria = (request.POST.get("categoria", "") or "").strip()
    total_str = (request.POST.get("total", "") or "").strip()
    fecha_str = (request.POST.get("fecha", "") or "").strip()
    next_url = (request.POST.get("next", "") or "").strip()

    if not concepto:
        messages.error(request, "Debes escribir un concepto para el egreso.")
        return redirect(next_url or "/dashboard/finanzas/flujo/")

    try:
        total = float(total_str)
        if total <= 0:
            raise ValueError
    except Exception:
        messages.error(request, "Total inválido para el egreso.")
        return redirect(next_url or "/dashboard/finanzas/flujo/")

    fecha = parse_date(fecha_str)
    if not fecha:
        messages.error(request, "Fecha inválida para el egreso.")
        return redirect(next_url or "/dashboard/finanzas/flujo/")

    _crear_egreso_manual(
        concepto=concepto,
        categoria=categoria,
        total=total,
        fecha=fecha,
    )

    _registrar_actividad(
        user=request.user,
        titulo="Egreso manual creado",
        descripcion=f"{request.user.username} registró el egreso manual '{concepto}' por ${total}.",
        url=f"/dashboard/finanzas/flujo/?anio={fecha.year}&mes={fecha.month}",
    )

    messages.success(request, "Egreso manual registrado correctamente.")
    return redirect(next_url or f"/dashboard/finanzas/flujo/?anio={fecha.year}&mes={fecha.month}")


@login_required
def egreso_manual_eliminar_view(request, pk):
    if not es_admin(request.user):
        return render(request, "dashboard/no_autorizado.html", status=403)

    egreso = get_object_or_404(Egreso, pk=pk)

    if not _egreso_es_manual(egreso):
        messages.error(request, "Solo se pueden eliminar egresos manuales desde esta pantalla.")
        return redirect("/dashboard/finanzas/flujo/")

    if request.method != "POST":
        return redirect(f"/dashboard/finanzas/flujo/?anio={egreso.fecha.year}&mes={egreso.fecha.month}")

    concepto = getattr(egreso, "concepto", "") or "Egreso manual"
    total = egreso.total
    fecha = egreso.fecha

    _registrar_actividad(
        user=request.user,
        titulo="Egreso manual eliminado",
        descripcion=f"{request.user.username} eliminó el egreso manual '{concepto}' por ${total}.",
        url=f"/dashboard/finanzas/flujo/?anio={fecha.year}&mes={fecha.month}",
    )

    egreso.delete()
    messages.success(request, "Egreso manual eliminado.")
    return redirect(f"/dashboard/finanzas/flujo/?anio={fecha.year}&mes={fecha.month}")


@login_required
def ingreso_manual_crear_view(request):
    if not es_admin(request.user):
        return render(request, "dashboard/no_autorizado.html", status=403)

    if request.method != "POST":
        return redirect("/dashboard/finanzas/flujo/")

    concepto = (request.POST.get("concepto", "") or "").strip()
    total_str = (request.POST.get("total", "") or "").strip()
    fecha_str = (request.POST.get("fecha", "") or "").strip()
    next_url = (request.POST.get("next", "") or "").strip()

    if not concepto:
        messages.error(request, "Debes escribir un concepto para el ingreso.")
        return redirect(next_url or "/dashboard/finanzas/flujo/")

    try:
        total = float(total_str)
        if total <= 0:
            raise ValueError
    except Exception:
        messages.error(request, "Total inválido para el ingreso.")
        return redirect(next_url or "/dashboard/finanzas/flujo/")

    fecha = parse_date(fecha_str)
    if not fecha:
        messages.error(request, "Fecha inválida para el ingreso.")
        return redirect(next_url or "/dashboard/finanzas/flujo/")

    Ingreso.objects.create(
        concepto=concepto,
        total=total,
        fecha=fecha,
    )

    _registrar_actividad(
        user=request.user,
        titulo="Ingreso manual creado",
        descripcion=f"{request.user.username} registró el ingreso manual '{concepto}' por ${total}.",
        url=f"/dashboard/finanzas/flujo/?anio={fecha.year}&mes={fecha.month}",
    )

    messages.success(request, "Ingreso manual registrado correctamente.")
    return redirect(next_url or f"/dashboard/finanzas/flujo/?anio={fecha.year}&mes={fecha.month}")


@login_required
def ingreso_manual_eliminar_view(request, pk):
    if not es_admin(request.user):
        return render(request, "dashboard/no_autorizado.html", status=403)

    ingreso = get_object_or_404(Ingreso, pk=pk)

    if not _ingreso_es_manual(ingreso):
        messages.error(request, "Solo se pueden eliminar ingresos manuales desde esta pantalla.")
        return redirect("/dashboard/finanzas/flujo/")

    if request.method != "POST":
        return redirect(f"/dashboard/finanzas/flujo/?anio={ingreso.fecha.year}&mes={ingreso.fecha.month}")

    concepto = getattr(ingreso, "concepto", "") or "Ingreso manual"
    total = ingreso.total
    fecha = ingreso.fecha

    _registrar_actividad(
        user=request.user,
        titulo="Ingreso manual eliminado",
        descripcion=f"{request.user.username} eliminó el ingreso manual '{concepto}' por ${total}.",
        url=f"/dashboard/finanzas/flujo/?anio={fecha.year}&mes={fecha.month}",
    )

    ingreso.delete()
    messages.success(request, "Ingreso manual eliminado.")
    return redirect(f"/dashboard/finanzas/flujo/?anio={fecha.year}&mes={fecha.month}")


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

        ingreso = Ingreso.objects.create(concepto=concepto, total=total, fecha=fecha)
        _registrar_actividad(
            user=request.user,
            titulo="Ingreso creado",
            descripcion=f"{request.user.username} creó el ingreso '{concepto}' por ${total}.",
            url=f"/dashboard/finanzas/ingresos/{ingreso.pk}/editar/",
        )

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

        _registrar_actividad(
            user=request.user,
            titulo="Ingreso actualizado",
            descripcion=f"{request.user.username} actualizó el ingreso '{concepto}' a ${total}.",
            url=f"/dashboard/finanzas/ingresos/{pk}/editar/",
        )

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
        concepto = ingreso.concepto
        total = ingreso.total
        _registrar_actividad(
            user=request.user,
            titulo="Ingreso eliminado",
            descripcion=f"{request.user.username} eliminó el ingreso '{concepto}' por ${total}.",
            url="/dashboard/finanzas/ingresos/",
        )

        ingreso.delete()
        messages.success(request, "Ingreso eliminado.")
        return redirect("/dashboard/finanzas/ingresos/")

    return render(
        request,
        "dashboard/ingreso_eliminar.html",
        {"ingreso": ingreso, "es_admin": True},
    )


# -------------------
# Finanzas - Movimientos recurrentes
# -------------------
@login_required
def movimientos_recurrentes_view(request):
    if not es_admin(request.user):
        return render(request, "dashboard/no_autorizado.html", status=403)

    notificar_movimientos_recurrentes_proximos()

    if request.method == "POST":
        tipo = (request.POST.get("tipo", "") or "").strip()
        concepto = (request.POST.get("concepto", "") or "").strip()
        monto_str = (request.POST.get("monto", "") or "").strip()
        frecuencia = (request.POST.get("frecuencia", "") or "").strip()
        proxima_fecha_str = (request.POST.get("proxima_fecha", "") or "").strip()
        activo = request.POST.get("activo") == "on"

        if tipo not in ["ingreso", "egreso"]:
            messages.error(request, "Tipo de movimiento inválido.")
            return redirect("/dashboard/finanzas/recurrentes/")

        if frecuencia not in ["mensual", "semanal"]:
            messages.error(request, "Frecuencia inválida.")
            return redirect("/dashboard/finanzas/recurrentes/")

        if not concepto:
            messages.error(request, "Debes escribir un concepto.")
            return redirect("/dashboard/finanzas/recurrentes/")

        try:
            monto = float(monto_str)
            if monto <= 0:
                raise ValueError
        except Exception:
            messages.error(request, "Monto inválido.")
            return redirect("/dashboard/finanzas/recurrentes/")

        proxima_fecha = parse_date(proxima_fecha_str)
        if not proxima_fecha:
            messages.error(request, "Fecha inválida.")
            return redirect("/dashboard/finanzas/recurrentes/")

        MovimientoRecurrente.objects.create(
            tipo=tipo,
            concepto=concepto,
            monto=monto,
            frecuencia=frecuencia,
            proxima_fecha=proxima_fecha,
            activo=activo,
        )

        _registrar_actividad(
            user=request.user,
            titulo="Movimiento recurrente creado",
            descripcion=f"{request.user.username} creó el movimiento recurrente '{concepto}' por ${monto}.",
            url="/dashboard/finanzas/recurrentes/",
        )

        messages.success(request, "Movimiento recurrente creado correctamente.")
        return redirect("/dashboard/finanzas/recurrentes/")

    movimientos = MovimientoRecurrente.objects.all().order_by("activo", "proxima_fecha", "-id")
    total_activos = movimientos.filter(activo=True).count()
    total_inactivos = movimientos.filter(activo=False).count()
    total_ingresos = movimientos.filter(tipo="ingreso", activo=True).count()
    total_egresos = movimientos.filter(tipo="egreso", activo=True).count()
    pendientes = movimientos.filter(activo=True, proxima_fecha__lte=date.today()).count()

    return render(
        request,
        "dashboard/movimientos_recurrentes.html",
        {
            "movimientos": movimientos,
            "total_activos": total_activos,
            "total_inactivos": total_inactivos,
            "total_ingresos": total_ingresos,
            "total_egresos": total_egresos,
            "pendientes": pendientes,
            "hoy": date.today(),
            "es_admin": True,
        },
    )


@login_required
@require_http_methods(["POST"])
def movimientos_recurrentes_procesar_view(request):
    if not es_admin(request.user):
        return render(request, "dashboard/no_autorizado.html", status=403)

    resultado = procesar_movimientos_recurrentes()

    _registrar_actividad(
        user=request.user,
        titulo="Recurrentes procesados",
        descripcion=(
            f"{request.user.username} ejecutó los movimientos recurrentes: "
            f"{resultado['total_generados']} generados "
            f"({resultado['ingresos_generados']} ingresos, {resultado['egresos_generados']} egresos)."
        ),
        url="/dashboard/finanzas/recurrentes/",
    )

    if resultado["total_generados"] > 0:
        messages.success(
            request,
            f"Proceso completado: {resultado['total_generados']} movimientos generados "
            f"({resultado['ingresos_generados']} ingresos y {resultado['egresos_generados']} egresos)."
        )
    else:
        messages.info(request, "No había movimientos recurrentes pendientes por procesar.")

    return redirect("/dashboard/finanzas/recurrentes/")


@login_required
def movimiento_recurrente_editar_view(request, pk):
    if not es_admin(request.user):
        return render(request, "dashboard/no_autorizado.html", status=403)

    movimiento = get_object_or_404(MovimientoRecurrente, pk=pk)

    if request.method == "POST":
        tipo = (request.POST.get("tipo", "") or "").strip()
        concepto = (request.POST.get("concepto", "") or "").strip()
        monto_str = (request.POST.get("monto", "") or "").strip()
        frecuencia = (request.POST.get("frecuencia", "") or "").strip()
        proxima_fecha_str = (request.POST.get("proxima_fecha", "") or "").strip()
        activo = request.POST.get("activo") == "on"

        if tipo not in ["ingreso", "egreso"]:
            messages.error(request, "Tipo inválido.")
            return redirect(f"/dashboard/finanzas/recurrentes/{pk}/editar/")

        if frecuencia not in ["mensual", "semanal"]:
            messages.error(request, "Frecuencia inválida.")
            return redirect(f"/dashboard/finanzas/recurrentes/{pk}/editar/")

        if not concepto:
            messages.error(request, "Debes escribir un concepto.")
            return redirect(f"/dashboard/finanzas/recurrentes/{pk}/editar/")

        try:
            monto = float(monto_str)
            if monto <= 0:
                raise ValueError
        except Exception:
            messages.error(request, "Monto inválido.")
            return redirect(f"/dashboard/finanzas/recurrentes/{pk}/editar/")

        proxima_fecha = parse_date(proxima_fecha_str)
        if not proxima_fecha:
            messages.error(request, "Fecha inválida.")
            return redirect(f"/dashboard/finanzas/recurrentes/{pk}/editar/")

        movimiento.tipo = tipo
        movimiento.concepto = concepto
        movimiento.monto = monto
        movimiento.frecuencia = frecuencia
        movimiento.proxima_fecha = proxima_fecha
        movimiento.activo = activo
        movimiento.save()

        _registrar_actividad(
            user=request.user,
            titulo="Movimiento recurrente actualizado",
            descripcion=f"{request.user.username} actualizó el movimiento recurrente '{concepto}'.",
            url="/dashboard/finanzas/recurrentes/",
        )

        messages.success(request, "Movimiento recurrente actualizado correctamente.")
        return redirect("/dashboard/finanzas/recurrentes/")

    return render(
        request,
        "dashboard/movimiento_recurrente_form.html",
        {
            "movimiento": movimiento,
            "modo": "editar",
            "es_admin": True,
        },
    )


@login_required
@require_http_methods(["POST"])
def movimiento_recurrente_toggle_view(request, pk):
    if not es_admin(request.user):
        return render(request, "dashboard/no_autorizado.html", status=403)

    movimiento = get_object_or_404(MovimientoRecurrente, pk=pk)

    movimiento.activo = not movimiento.activo
    movimiento.save(update_fields=["activo"])

    estado = "activado" if movimiento.activo else "desactivado"

    _registrar_actividad(
        user=request.user,
        titulo="Movimiento recurrente actualizado",
        descripcion=f"{request.user.username} {estado} el movimiento recurrente '{movimiento.concepto}'.",
        url="/dashboard/finanzas/recurrentes/",
    )

    messages.success(request, f"Movimiento recurrente {estado} correctamente.")
    return redirect("/dashboard/finanzas/recurrentes/")


@login_required
def movimiento_recurrente_eliminar_view(request, pk):
    if not es_admin(request.user):
        return render(request, "dashboard/no_autorizado.html", status=403)

    movimiento = get_object_or_404(MovimientoRecurrente, pk=pk)

    if request.method == "POST":
        concepto = movimiento.concepto

        _registrar_actividad(
            user=request.user,
            titulo="Movimiento recurrente eliminado",
            descripcion=f"{request.user.username} eliminó el movimiento recurrente '{concepto}'.",
            url="/dashboard/finanzas/recurrentes/",
        )

        movimiento.delete()
        messages.success(request, "Movimiento recurrente eliminado correctamente.")
        return redirect("/dashboard/finanzas/recurrentes/")

    return render(
        request,
        "dashboard/movimiento_recurrente_form.html",
        {
            "movimiento": movimiento,
            "modo": "eliminar",
            "es_admin": True,
        },
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

#======================
# INVENTARIO PRO
#======================

from django.db.models import F
from decimal import Decimal
from inventario.models import Insumo, VentaInsumo, EntradaStock, MovimientoInventario
from finanzas.models import Ingreso


@login_required
def inventario_view(request):
    if not es_admin(request.user):
        return render(request, "dashboard/no_autorizado.html", status=403)

    insumos = Insumo.objects.all().order_by("nombre")

    total_insumos = insumos.count()
    bajo_stock = insumos.filter(stock__lte=F("stock_minimo")).count()
    stock_total = sum(i.stock for i in insumos)

    hoy = timezone.localdate()
    primer_dia_mes = hoy.replace(day=1)

    ventas_mes = VentaInsumo.objects.filter(fecha__gte=primer_dia_mes)
    total_ventas_mes = ventas_mes.aggregate(total=Sum("total")).get("total") or 0
    ganancia_mes = ventas_mes.aggregate(total=Sum("ganancia")).get("total") or 0
    unidades_vendidas_mes = ventas_mes.aggregate(total=Sum("cantidad")).get("total") or 0

    movimientos_recientes = list(
        MovimientoInventario.objects.select_related("insumo").all().order_by("-creado_en", "-id")[:8]
    )

    top_vendidos = list(
        VentaInsumo.objects
        .filter(fecha__gte=primer_dia_mes)
        .values("insumo__nombre")
        .annotate(
            cantidad_total=Sum("cantidad"),
            monto_total=Sum("total"),
            ganancia_total=Sum("ganancia"),
        )
        .order_by("-cantidad_total", "-monto_total")[:5]
    )

    return render(
        request,
        "dashboard/inventario.html",
        {
            "insumos": insumos,
            "total_insumos": total_insumos,
            "bajo_stock": bajo_stock,
            "stock_total": stock_total,
            "total_ventas_mes": float(total_ventas_mes),
            "ganancia_mes": float(ganancia_mes),
            "unidades_vendidas_mes": int(unidades_vendidas_mes or 0),
            "movimientos_recientes": movimientos_recientes,
            "top_vendidos": top_vendidos,
            "es_admin": True,
        },
    )


#======================
# VENDER INSUMO
#======================

@login_required
def vender_insumo_view(request):
    if not es_admin(request.user):
        return render(request, "dashboard/no_autorizado.html", status=403)

    if request.method != "POST":
        return redirect("/dashboard/inventario/")

    insumo_id = (request.POST.get("insumo_id") or "").strip()
    cantidad_str = (request.POST.get("cantidad") or "").strip()

    try:
        cantidad = int(cantidad_str)
        if cantidad <= 0:
            raise ValueError
    except Exception:
        messages.error(request, "Cantidad inválida")
        return redirect("/dashboard/inventario/")

    insumo = get_object_or_404(Insumo, pk=insumo_id)

    if insumo.stock < cantidad:
        messages.error(
            request,
            f"Stock insuficiente de {insumo.nombre}. Disponible: {insumo.stock}"
        )
        return redirect("/dashboard/inventario/")

    stock_anterior = insumo.stock
    precio_unitario = Decimal(insumo.precio)
    costo_unitario = Decimal(getattr(insumo, "costo", 0) or 0)
    total = Decimal(cantidad) * precio_unitario
    ganancia = Decimal(cantidad) * (precio_unitario - costo_unitario)

    insumo.stock -= cantidad
    insumo.save()

    VentaInsumo.objects.create(
        insumo=insumo,
        cantidad=cantidad,
        precio_unitario=precio_unitario,
        costo_unitario=costo_unitario,
        total=total,
        ganancia=ganancia,
    )

    MovimientoInventario.objects.create(
        insumo=insumo,
        tipo="venta",
        cantidad=cantidad,
        stock_anterior=stock_anterior,
        stock_resultante=insumo.stock,
        observacion=f"Venta de insumo · utilidad ${ganancia}",
    )

    Ingreso.objects.create(
        concepto=f"Venta de insumo: {insumo.nombre}",
        total=total,
        fecha=timezone.localdate(),
    )

    _registrar_actividad(
        user=request.user,
        titulo="Venta de insumo registrada",
        descripcion=f"{request.user.username} registró la venta de {insumo.nombre} x {cantidad} por ${total}. Ganancia: ${ganancia}.",
        url="/dashboard/inventario/",
    )

    messages.success(request, f"Venta registrada correctamente. Ganancia: ${ganancia}")
    return redirect("inventario")


#======================
# ENTRADA DE STOCK
#======================

@login_required
def agregar_stock_view(request):
    if not es_admin(request.user):
        return render(request, "dashboard/no_autorizado.html", status=403)

    if request.method != "POST":
        return redirect("/dashboard/inventario/")

    insumo_id = (request.POST.get("insumo_id") or "").strip()
    cantidad_str = (request.POST.get("cantidad") or "").strip()
    observacion = (request.POST.get("observacion") or "").strip()

    try:
        cantidad = int(cantidad_str)
        if cantidad <= 0:
            raise ValueError
    except Exception:
        messages.error(request, "Cantidad inválida.")
        return redirect("/dashboard/inventario/")

    insumo = get_object_or_404(Insumo, pk=insumo_id)
    stock_anterior = insumo.stock

    insumo.stock += cantidad
    insumo.save()

    EntradaStock.objects.create(
        insumo=insumo,
        cantidad=cantidad,
        observacion=observacion,
    )

    MovimientoInventario.objects.create(
        insumo=insumo,
        tipo="entrada",
        cantidad=cantidad,
        stock_anterior=stock_anterior,
        stock_resultante=insumo.stock,
        observacion=observacion or "Entrada manual",
    )

    _registrar_actividad(
        user=request.user,
        titulo="Entrada de stock registrada",
        descripcion=f"{request.user.username} agregó {cantidad} unidades de {insumo.nombre}.",
        url="/dashboard/inventario/",
    )

    messages.success(request, "Stock agregado correctamente.")
    return redirect("/dashboard/inventario/")


#======================
# HISTORIAL INVENTARIO PRO
#======================

@login_required
def inventario_historial_view(request):
    if not es_admin(request.user):
        return render(request, "dashboard/no_autorizado.html", status=403)

    q = (request.GET.get("q", "") or "").strip()
    tipo = (request.GET.get("tipo", "") or "").strip().lower()
    fecha_desde_str = (request.GET.get("fecha_desde", "") or "").strip()
    fecha_hasta_str = (request.GET.get("fecha_hasta", "") or "").strip()
    insumo_id = (request.GET.get("insumo", "") or "").strip()

    fecha_desde = parse_date(fecha_desde_str) if fecha_desde_str else None
    fecha_hasta = parse_date(fecha_hasta_str) if fecha_hasta_str else None

    qs = MovimientoInventario.objects.select_related("insumo").all().order_by("-creado_en", "-id")

    if tipo in ["entrada", "venta", "mantenimiento", "ajuste"]:
        qs = qs.filter(tipo=tipo)

    if fecha_desde:
        qs = qs.filter(fecha__gte=fecha_desde)

    if fecha_hasta:
        qs = qs.filter(fecha__lte=fecha_hasta)

    if insumo_id.isdigit():
        qs = qs.filter(insumo_id=int(insumo_id))

    if q:
        qs = qs.filter(insumo__nombre__icontains=q)

    total_movimientos = qs.count()
    total_entradas = qs.filter(tipo="entrada").count()
    total_ventas = qs.filter(tipo="venta").count()
    total_mantenimiento = qs.filter(tipo="mantenimiento").count()

    unidades_entrada = qs.filter(tipo="entrada").aggregate(total=Sum("cantidad")).get("total") or 0
    unidades_venta = qs.filter(tipo="venta").aggregate(total=Sum("cantidad")).get("total") or 0
    unidades_mantenimiento = qs.filter(tipo="mantenimiento").aggregate(total=Sum("cantidad")).get("total") or 0

    paginator = Paginator(qs, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    insumos_filtro = Insumo.objects.all().order_by("nombre")

    top_vendidos = list(
        VentaInsumo.objects
        .values("insumo__nombre")
        .annotate(
            cantidad_total=Sum("cantidad"),
            monto_total=Sum("total"),
            ganancia_total=Sum("ganancia"),
        )
        .order_by("-cantidad_total", "-monto_total")[:10]
    )

    top_movidos = list(
        MovimientoInventario.objects
        .values("insumo__nombre")
        .annotate(cantidad_total=Sum("cantidad"))
        .order_by("-cantidad_total")[:10]
    )

    query_params = request.GET.copy()
    if "page" in query_params:
        query_params.pop("page")
    querystring = query_params.urlencode()

    return render(
        request,
        "dashboard/inventario_historial.html",
        {
            "page_obj": page_obj,
            "q": q,
            "tipo": tipo,
            "fecha_desde": fecha_desde_str,
            "fecha_hasta": fecha_hasta_str,
            "insumo_id": insumo_id,
            "insumos_filtro": insumos_filtro,
            "total_movimientos": total_movimientos,
            "total_entradas": total_entradas,
            "total_ventas": total_ventas,
            "total_mantenimiento": total_mantenimiento,
            "unidades_entrada": int(unidades_entrada or 0),
            "unidades_venta": int(unidades_venta or 0),
            "unidades_mantenimiento": int(unidades_mantenimiento or 0),
            "top_vendidos": top_vendidos,
            "top_movidos": top_movidos,
            "querystring": querystring,
            "es_admin": True,
        },
    )


# ================================
# REPORTE DE GANANCIAS PRO
# ================================
import io
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import render

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


def _obtener_datos_reporte_ganancias(fecha_inicio=None, fecha_fin=None):
    ingresos = Ingreso.objects.all().order_by("-fecha", "-id")
    egresos = Egreso.objects.all().order_by("-fecha", "-id")

    if fecha_inicio:
        ingresos = ingresos.filter(fecha__gte=fecha_inicio)
        egresos = egresos.filter(fecha__gte=fecha_inicio)

    if fecha_fin:
        ingresos = ingresos.filter(fecha__lte=fecha_fin)
        egresos = egresos.filter(fecha__lte=fecha_fin)

    total_ingresos = ingresos.aggregate(total=Sum("total"))["total"] or Decimal("0")
    total_egresos = egresos.aggregate(total=Sum("total"))["total"] or Decimal("0")
    ganancia = total_ingresos - total_egresos

    movimientos = []

    for i in ingresos:
        movimientos.append({
            "tipo": "Ingreso",
            "concepto": i.concepto or "-",
            "monto": i.total or Decimal("0"),
            "fecha": i.fecha,
        })

    for e in egresos:
        movimientos.append({
            "tipo": "Egreso",
            "concepto": e.concepto or "-",
            "monto": e.total or Decimal("0"),
            "fecha": e.fecha,
        })

    movimientos.sort(key=lambda x: (x["fecha"], x["tipo"]), reverse=True)

    return {
        "ingresos": ingresos,
        "egresos": egresos,
        "movimientos": movimientos,
        "total_ingresos": total_ingresos,
        "total_egresos": total_egresos,
        "ganancia": ganancia,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
    }


@login_required
def reporte_ganancias_view(request):
    fecha_inicio = request.GET.get("fecha_inicio") or None
    fecha_fin = request.GET.get("fecha_fin") or None

    context = _obtener_datos_reporte_ganancias(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
    )

    return render(request, "dashboard/reporte_ganancias.html", context)


@login_required
def exportar_ganancias_excel(request):
    fecha_inicio = request.GET.get("fecha_inicio") or None
    fecha_fin = request.GET.get("fecha_fin") or None

    data = _obtener_datos_reporte_ganancias(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
    )

    wb = Workbook()
    ws = wb.active
    ws.title = "Ganancias"

    fill_titulo = PatternFill("solid", fgColor="1F4E78")
    fill_encabezado = PatternFill("solid", fgColor="D9EAF7")
    fill_ingreso = PatternFill("solid", fgColor="E2F0D9")
    fill_egreso = PatternFill("solid", fgColor="FDE9E7")

    font_blanco = Font(color="FFFFFF", bold=True, size=12)
    font_negrita = Font(bold=True)

    ws.merge_cells("A1:D1")
    ws["A1"] = "REPORTE DE GANANCIAS"
    ws["A1"].fill = fill_titulo
    ws["A1"].font = font_blanco
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")

    ws["A3"] = "Fecha inicio"
    ws["B3"] = data["fecha_inicio"] or "Todas"
    ws["C3"] = "Fecha fin"
    ws["D3"] = data["fecha_fin"] or "Todas"

    ws["A5"] = "Total ingresos"
    ws["B5"] = float(data["total_ingresos"])
    ws["C5"] = "Total egresos"
    ws["D5"] = float(data["total_egresos"])

    ws["A6"] = "Ganancia neta"
    ws["B6"] = float(data["ganancia"])

    for cell in ("A5", "C5", "A6"):
        ws[cell].font = font_negrita

    encabezados = ["Tipo", "Concepto", "Monto", "Fecha"]
    fila_inicio_tabla = 8

    for col, encabezado in enumerate(encabezados, start=1):
        cell = ws.cell(row=fila_inicio_tabla, column=col, value=encabezado)
        cell.fill = fill_encabezado
        cell.font = font_negrita
        cell.alignment = Alignment(horizontal="center")

    fila = fila_inicio_tabla + 1
    for mov in data["movimientos"]:
        ws.cell(row=fila, column=1, value=mov["tipo"])
        ws.cell(row=fila, column=2, value=mov["concepto"])
        ws.cell(row=fila, column=3, value=float(mov["monto"]))
        ws.cell(row=fila, column=4, value=mov["fecha"].strftime("%d/%m/%Y") if mov["fecha"] else "")

        if mov["tipo"] == "Ingreso":
            ws.cell(row=fila, column=1).fill = fill_ingreso
        else:
            ws.cell(row=fila, column=1).fill = fill_egreso

        fila += 1

    for row in ws.iter_rows(min_row=5, max_row=fila, min_col=2, max_col=3):
        for cell in row:
            if isinstance(cell.value, (int, float)):
                cell.number_format = '$ #,##0.00'

    ws.column_dimensions["A"].width = 15
    ws.column_dimensions["B"].width = 45
    ws.column_dimensions["C"].width = 18
    ws.column_dimensions["D"].width = 18

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="reporte_ganancias.xlsx"'

    wb.save(response)
    return response


@login_required
def exportar_ganancias_pdf(request):
    fecha_inicio = request.GET.get("fecha_inicio") or None
    fecha_fin = request.GET.get("fecha_fin") or None

    data = _obtener_datos_reporte_ganancias(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
    )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.2 * cm,
        leftMargin=1.2 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
    )

    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Reporte de Ganancias", styles["Title"]))
    story.append(Spacer(1, 10))

    rango_texto = f"Desde: {data['fecha_inicio'] or 'Todas'} &nbsp;&nbsp;&nbsp; Hasta: {data['fecha_fin'] or 'Todas'}"
    story.append(Paragraph(rango_texto, styles["Normal"]))
    story.append(Spacer(1, 10))

    resumen = [
        ["Total ingresos", f"${data['total_ingresos']:,.2f}"],
        ["Total egresos", f"${data['total_egresos']:,.2f}"],
        ["Ganancia neta", f"${data['ganancia']:,.2f}"],
    ]

    tabla_resumen = Table(resumen, colWidths=[7 * cm, 5 * cm])
    tabla_resumen.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(tabla_resumen)
    story.append(Spacer(1, 14))

    detalle = [["Tipo", "Concepto", "Monto", "Fecha"]]
    for mov in data["movimientos"]:
        detalle.append([
            mov["tipo"],
            mov["concepto"],
            f"${mov['monto']:,.2f}",
            mov["fecha"].strftime("%d/%m/%Y") if mov["fecha"] else "",
        ])

    tabla_detalle = Table(detalle, colWidths=[3 * cm, 8 * cm, 3.2 * cm, 3.2 * cm])
    tabla_detalle.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9EAF7")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ALIGN", (2, 1), (2, -1), "RIGHT"),
        ("ALIGN", (3, 1), (3, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))

    for idx, mov in enumerate(data["movimientos"], start=1):
        if mov["tipo"] == "Ingreso":
            tabla_detalle.setStyle(TableStyle([
                ("BACKGROUND", (0, idx), (0, idx), colors.HexColor("#E2F0D9"))
            ]))
        else:
            tabla_detalle.setStyle(TableStyle([
                ("BACKGROUND", (0, idx), (0, idx), colors.HexColor("#FDE9E7"))
            ]))

    story.append(tabla_detalle)

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="reporte_ganancias.pdf"'
    response.write(pdf)
    return response