from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from trabajadores.models import Trabajador
from .engine import DEFAULT_RULES, calcular_recomendacion
from .models import CasoAsistenteTecnico, MotorRecomendacion
from .services import generar_recordatorios_seguimiento


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


def _trabajador(user):
    try:
        return Trabajador.objects.get(user=user)
    except Trabajador.DoesNotExist:
        return None


def _motor_activo():
    motor = MotorRecomendacion.objects.filter(activo=True).order_by("-creado_en").first()
    if motor:
        return motor
    return MotorRecomendacion.objects.create(
        version="1.0",
        nombre="Motor JVAQUA",
        descripcion="Primera versión del motor de recomendaciones basado en protocolos operativos JVAQUA.",
        reglas=DEFAULT_RULES,
        activo=True,
    )


def _base_template(user):
    return "dashboard/base_admin.html" if _es_admin(user) else "dashboard/base_trabajador.html"


def _actualizar_recordatorios(user):
    try:
        from dashboard.views import _crear_notificacion
        generar_recordatorios_seguimiento(user=user, crear_notificacion=_crear_notificacion)
    except Exception:
        # El asistente nunca debe bloquear el ingreso a la herramienta por una falla de push.
        pass


@login_required
@require_http_methods(["GET", "POST"])
def asistente_inicio_view(request):
    if not (_es_trabajador(request.user) or _es_admin(request.user)):
        return HttpResponseForbidden("No autorizado")
    _actualizar_recordatorios(request.user)
    motor = _motor_activo()
    resultado = None
    caso = None

    if request.method == "POST":
        metodo_volumen = (request.POST.get("metodo_volumen") or "volumen").strip()
        try:
            ph = Decimal((request.POST.get("ph") or "").replace(",", "."))
            cloro = Decimal((request.POST.get("cloro") or "").replace(",", "."))

            if metodo_volumen == "dimensiones":
                largo = Decimal((request.POST.get("largo_m") or "").replace(",", "."))
                ancho = Decimal((request.POST.get("ancho_m") or "").replace(",", "."))
                profundidad = Decimal((request.POST.get("profundidad_m") or "").replace(",", "."))
                if largo <= 0 or ancho <= 0 or profundidad <= 0:
                    raise ValueError
                volumen = (largo * ancho * profundidad).quantize(Decimal("0.01"))
            else:
                volumen = Decimal((request.POST.get("volumen_m3") or "").replace(",", "."))
        except (InvalidOperation, ValueError):
            messages.error(
                request,
                "Revisa las medidas o el volumen, pH y cloro. Deben ser valores numéricos válidos.",
            )
        else:
            estado = request.POST.get("estado_agua") or ""
            tipo_piscina = request.POST.get("tipo_piscina") or ""
            estados_validos = {x[0] for x in CasoAsistenteTecnico.ESTADO_AGUA_CHOICES}
            tipos_validos = {x[0] for x in CasoAsistenteTecnico.TIPO_PISCINA_CHOICES}
            errores = []
            if volumen <= 0 or volumen > 5000:
                errores.append("El volumen debe ser mayor que 0.")
            if ph < 0 or ph > 14:
                errores.append("El pH debe estar entre 0 y 14.")
            if cloro < 0 or cloro > 20:
                errores.append("El cloro debe estar entre 0 y 20 ppm.")
            if estado not in estados_validos:
                errores.append("Selecciona el estado del agua.")
            if tipo_piscina not in tipos_validos:
                errores.append("Selecciona el tipo de piscina.")

            if errores:
                for error in errores:
                    messages.error(request, error)
            else:
                resultado = calcular_recomendacion(volumen, ph, cloro, estado, tipo_piscina, motor.reglas)
                caso = CasoAsistenteTecnico.objects.create(
                    user=request.user,
                    trabajador=_trabajador(request.user),
                    motor=motor,
                    volumen_m3=volumen,
                    ph_inicial=ph,
                    cloro_inicial=cloro,
                    estado_agua=estado,
                    tipo_piscina=tipo_piscina,
                    diagnostico=resultado["diagnostico"],
                    tipo_tratamiento=resultado["tipo_tratamiento"],
                    prioridad=resultado["prioridad"],
                    resumen=resultado["resumen"],
                    protocolo=resultado["protocolo"],
                    productos_sugeridos=resultado["productos_sugeridos"],
                    explicaciones=resultado["explicaciones"],
                    advertencias=resultado["advertencias"],
                    foto_inicial=request.FILES.get("foto_inicial"),
                    seguimiento_programado_para=timezone.now() + timedelta(hours=resultado["seguimiento_horas"]),
                )
                messages.success(request, f"Diagnóstico guardado como caso #{caso.pk}. El seguimiento se solicitará después de aproximadamente 24 horas.")

    recientes = CasoAsistenteTecnico.objects.filter(user=request.user).select_related("motor")[:5]
    return render(request, "asistente_tecnico/inicio.html", {
        "base_template": _base_template(request.user),
        "resultado": resultado,
        "caso": caso,
        "motor": motor,
        "recientes": recientes,
        "estado_choices": CasoAsistenteTecnico.ESTADO_AGUA_CHOICES,
        "tipo_choices": CasoAsistenteTecnico.TIPO_PISCINA_CHOICES,
        "es_admin": _es_admin(request.user),
    })


@login_required
def asistente_historial_view(request):
    if not (_es_trabajador(request.user) or _es_admin(request.user)):
        return HttpResponseForbidden("No autorizado")
    _actualizar_recordatorios(request.user)
    qs = CasoAsistenteTecnico.objects.select_related("user", "trabajador", "motor")
    if not _es_admin(request.user):
        qs = qs.filter(user=request.user)
    resultado = request.GET.get("resultado") or ""
    tratamiento = request.GET.get("tratamiento") or ""
    if resultado:
        qs = qs.filter(resultado=resultado)
    if tratamiento:
        qs = qs.filter(tipo_tratamiento=tratamiento)
    return render(request, "asistente_tecnico/historial.html", {
        "base_template": _base_template(request.user),
        "casos": qs[:200],
        "filtro_resultado": resultado,
        "filtro_tratamiento": tratamiento,
        "es_admin": _es_admin(request.user),
    })


@login_required
def asistente_caso_detalle_view(request, pk):
    caso = get_object_or_404(CasoAsistenteTecnico.objects.select_related("user", "trabajador", "motor"), pk=pk)
    if not _es_admin(request.user) and caso.user_id != request.user.id:
        return HttpResponseForbidden("No autorizado")
    return render(request, "asistente_tecnico/caso_detalle.html", {
        "base_template": _base_template(request.user),
        "caso": caso,
        "es_admin": _es_admin(request.user),
    })


@login_required
@require_http_methods(["GET", "POST"])
def asistente_seguimiento_view(request, pk):
    caso = get_object_or_404(CasoAsistenteTecnico, pk=pk)
    if not _es_admin(request.user) and caso.user_id != request.user.id:
        return HttpResponseForbidden("No autorizado")

    if request.method == "POST":
        resultado = request.POST.get("resultado") or ""
        if resultado not in {"exitoso", "parcial", "fallido"}:
            messages.error(request, "Selecciona cómo funcionó el tratamiento.")
        else:
            caso.resultado = resultado
            caso.fallas = request.POST.getlist("fallas") if resultado != "exitoso" else []
            caso.observaciones_resultado = (request.POST.get("observaciones") or "").strip()
            caso.accion_final = (request.POST.get("accion_final") or "").strip()
            caso.estado_agua_final = request.POST.get("estado_agua_final") or ""
            caso.foto_final = request.FILES.get("foto_final") or caso.foto_final
            for attr, key in (("ph_final", "ph_final"), ("cloro_final", "cloro_final")):
                value = (request.POST.get(key) or "").strip().replace(",", ".")
                if value:
                    try:
                        setattr(caso, attr, Decimal(value))
                    except InvalidOperation:
                        pass
            caso.seguimiento_respondido_en = timezone.now()
            caso.save()
            try:
                from dashboard.models import Notificacion
                Notificacion.objects.filter(
                    user=caso.user,
                    url=f"/dashboard/asistente/casos/{caso.pk}/seguimiento/",
                    leida=False,
                ).update(leida=True, leida_en=timezone.now())
            except Exception:
                pass
            messages.success(request, "Gracias. El resultado quedó registrado y ayudará a evaluar el protocolo.")
            return redirect("asistente_tecnico:caso_detalle", pk=caso.pk)

    return render(request, "asistente_tecnico/seguimiento.html", {
        "base_template": _base_template(request.user),
        "caso": caso,
        "fallas_opciones": [
            ("sigue_verde", "El agua sigue verde"),
            ("sigue_turbia", "El agua sigue turbia"),
            ("ph_bajo", "El pH quedó bajo"),
            ("ph_alto", "El pH quedó alto"),
            ("cloro_insuficiente", "El cloro fue insuficiente"),
            ("cloro_alto", "El cloro quedó demasiado alto"),
            ("otro", "Otro"),
        ],
        "estado_choices": CasoAsistenteTecnico.ESTADO_AGUA_CHOICES,
        "es_admin": _es_admin(request.user),
    })


@login_required
def asistente_biblioteca_view(request):
    if not (_es_trabajador(request.user) or _es_admin(request.user)):
        return HttpResponseForbidden("No autorizado")
    temas = [
        {"titulo": "Floculación con sulfato de aluminio", "texto": "Se utiliza en agua muy turbia o verde. El sulfato agrupa partículas para sedimentarlas y además tiende a reducir el pH. El protocolo JVAQUA recomienda 24 horas de floculación antes de aspirar los sedimentos."},
        {"titulo": "Cloración de choque", "texto": "Busca elevar rápidamente el desinfectante cuando existe recuperación de agua o turbidez. En floculación se trabaja como referencia alrededor de 3–4 ppm y siempre se vuelve a medir antes de repetir."},
        {"titulo": "Metasilicato", "texto": "Se utiliza para elevar el pH en mantenimiento normal. Se aplica gradualmente, preferiblemente disuelto, se deja recircular aproximadamente 10 minutos y se vuelve a medir."},
        {"titulo": "Cal P24 / soda en polvo", "texto": "En floculación con pH bajo se usa para elevar previamente el pH, buscando compensar la caída posterior provocada por el sulfato de aluminio."},
        {"titulo": "Tricloro en pastilla", "texto": "Se prioriza en agua transparente y estable porque mantiene el cloro gradualmente y suele contribuir a que el pH tienda ligeramente hacia abajo."},
        {"titulo": "Reductor de pH", "texto": "Se reserva para mantenimiento normal cuando el pH está claramente elevado. No se utiliza como corrección previa al sulfato en un protocolo de floculación."},
    ]
    destacados = CasoAsistenteTecnico.objects.filter(destacado=True).select_related("user", "motor")[:12]
    return render(request, "asistente_tecnico/biblioteca.html", {
        "base_template": _base_template(request.user),
        "temas": temas,
        "destacados": destacados,
        "es_admin": _es_admin(request.user),
    })


@login_required
def asistente_admin_view(request):
    if not _es_admin(request.user):
        return HttpResponseForbidden("No autorizado")
    qs = CasoAsistenteTecnico.objects.select_related("user", "trabajador", "motor")
    total = qs.count()
    exitosos = qs.filter(resultado="exitoso").count()
    parciales = qs.filter(resultado="parcial").count()
    fallidos = qs.filter(resultado="fallido").count()
    respondidos = exitosos + parciales + fallidos
    tasa_exito = round((exitosos / respondidos) * 100, 1) if respondidos else 0
    por_tratamiento = list(qs.values("tipo_tratamiento").annotate(total=Count("id"), exitosos=Count("id", filter=Q(resultado="exitoso"))).order_by("tipo_tratamiento"))
    por_estado = list(qs.values("estado_agua").annotate(total=Count("id"), exitosos=Count("id", filter=Q(resultado="exitoso"))).order_by("estado_agua"))
    por_tipo_piscina = list(qs.values("tipo_piscina").annotate(total=Count("id"), exitosos=Count("id", filter=Q(resultado="exitoso"))).order_by("tipo_piscina"))
    fallas_conteo = {}
    rangos_volumen = {"0–25 m³": [0, 0], "25–50 m³": [0, 0], "50–100 m³": [0, 0], ">100 m³": [0, 0]}
    # Usar un queryset independiente sin select_related.
    # En Django, combinar select_related() con only() omitiendo las FK relacionadas
    # puede provocar FieldError al evaluar la consulta en el panel administrativo.
    for caso in CasoAsistenteTecnico.objects.only("volumen_m3", "resultado", "fallas"):
        v = float(caso.volumen_m3)
        clave = "0–25 m³" if v <= 25 else "25–50 m³" if v <= 50 else "50–100 m³" if v <= 100 else ">100 m³"
        rangos_volumen[clave][0] += 1
        if caso.resultado == "exitoso":
            rangos_volumen[clave][1] += 1
        for falla in (caso.fallas or []):
            fallas_conteo[falla] = fallas_conteo.get(falla, 0) + 1
    por_volumen = [{"rango": k, "total": v[0], "exitosos": v[1]} for k, v in rangos_volumen.items() if v[0]]
    fallas_frecuentes = sorted(fallas_conteo.items(), key=lambda x: (-x[1], x[0]))[:8]
    sugerencias = []
    for fila in por_tratamiento:
        respondidos_tipo = qs.filter(tipo_tratamiento=fila["tipo_tratamiento"]).exclude(resultado="pendiente").count()
        exitosos_tipo = qs.filter(tipo_tratamiento=fila["tipo_tratamiento"], resultado="exitoso").count()
        if respondidos_tipo >= 5:
            tasa = round(exitosos_tipo / respondidos_tipo * 100, 1)
            if tasa < 70:
                sugerencias.append(f"El protocolo {fila['tipo_tratamiento']} tiene {tasa}% de éxito en {respondidos_tipo} casos respondidos. Conviene revisar los casos parciales y fallidos antes de modificar sus reglas.")
    motores = MotorRecomendacion.objects.all()
    return render(request, "asistente_tecnico/admin.html", {
        "base_template": "dashboard/base_admin.html",
        "total": total,
        "exitosos": exitosos,
        "parciales": parciales,
        "fallidos": fallidos,
        "pendientes": qs.filter(resultado="pendiente").count(),
        "tasa_exito": tasa_exito,
        "por_tratamiento": por_tratamiento,
        "por_estado": por_estado,
        "por_tipo_piscina": por_tipo_piscina,
        "por_volumen": por_volumen,
        "fallas_frecuentes": fallas_frecuentes,
        "sugerencias": sugerencias,
        "casos_recientes": qs[:20],
        "motores": motores,
        "es_admin": True,
    })


@login_required
@require_http_methods(["GET", "POST"])
def asistente_version_nueva_view(request):
    if not _es_admin(request.user):
        return HttpResponseForbidden("No autorizado")
    actual = _motor_activo()
    reglas_actuales = {**DEFAULT_RULES, **(actual.reglas or {})}
    if request.method == "POST":
        version = (request.POST.get("version") or "").strip()
        descripcion = (request.POST.get("descripcion") or "").strip()
        if not version or MotorRecomendacion.objects.filter(version=version).exists():
            messages.error(request, "Escribe una versión nueva y única, por ejemplo 1.1.")
        else:
            reglas = dict(reglas_actuales)
            campos = [
                "ph_min", "ph_max", "ph_objetivo_normal", "ph_objetivo_pre_floculacion",
                "cloro_min", "cloro_max", "cloro_objetivo_normal", "cloro_objetivo_alto_uso",
                "cloro_objetivo_turbidez", "cloro_objetivo_floculacion", "cloro_granulado_g_por_m3",
                "sulfato_tramo_m3", "sulfato_tolerancia_m3", "alguicida_g_por_25m3",
                "p24_g_min_por_25m3", "p24_g_max_por_25m3", "seguimiento_horas",
            ]
            try:
                for campo in campos:
                    valor = (request.POST.get(campo) or "").strip().replace(",", ".")
                    if valor:
                        reglas[campo] = int(float(valor)) if campo == "seguimiento_horas" else float(valor)
            except ValueError:
                messages.error(request, "Hay un valor numérico inválido en las reglas.")
            else:
                with transaction.atomic():
                    MotorRecomendacion.objects.filter(activo=True).update(activo=False)
                    nuevo = MotorRecomendacion.objects.create(version=version, nombre="Motor JVAQUA", descripcion=descripcion, reglas=reglas, activo=True, publicado_por=request.user)
                messages.success(request, f"Motor JVAQUA {nuevo.version} publicado. Los casos históricos conservan la versión con la que fueron calculados.")
                return redirect("asistente_tecnico:admin")
    return render(request, "asistente_tecnico/version_form.html", {"base_template": "dashboard/base_admin.html", "actual": actual, "reglas": reglas_actuales, "es_admin": True})


@login_required
@require_http_methods(["POST"])
def asistente_version_activar_view(request, pk):
    if not _es_admin(request.user):
        return HttpResponseForbidden("No autorizado")
    motor = get_object_or_404(MotorRecomendacion, pk=pk)
    with transaction.atomic():
        MotorRecomendacion.objects.filter(activo=True).update(activo=False)
        motor.activo = True
        motor.publicado_por = request.user
        motor.save(update_fields=["activo", "publicado_por"])
    messages.success(request, f"Motor {motor.version} activado. Los casos nuevos usarán esta versión.")
    return redirect("asistente_tecnico:admin")


@login_required
@require_http_methods(["POST"])
def asistente_destacar_view(request, pk):
    if not _es_admin(request.user):
        return HttpResponseForbidden("No autorizado")
    caso = get_object_or_404(CasoAsistenteTecnico, pk=pk)
    caso.destacado = not caso.destacado
    caso.nota_destacado = (request.POST.get("nota_destacado") or caso.nota_destacado or "").strip()
    caso.save(update_fields=["destacado", "nota_destacado", "actualizado_en"])
    messages.success(request, "Caso destacado actualizado.")
    return redirect("asistente_tecnico:caso_detalle", pk=caso.pk)
