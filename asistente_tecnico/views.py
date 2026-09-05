from datetime import timedelta, datetime, time
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
from .engine import DEFAULT_RULES, calcular_recomendacion, diagnosticar_problema_tecnico, PROBLEMAS_TECNICOS
from .models import CasoAsistenteTecnico, MotorRecomendacion, ContenidoAcademia, ProgresoContenidoAcademia, FavoritoContenidoAcademia, ConsultaContenidoAcademia, PerfilSuscriptor, PiscinaSuscriptor, PlanMantenimientoPiscina, RegistroMantenimientoPiscina, VisitaProgramadaPiscina, NotificacionDigital, SugerenciaDigital
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


def _suscriptor(user):
    if not user.is_authenticated:
        return None
    try:
        perfil = user.perfil_suscriptor
        return perfil if perfil.tiene_acceso else None
    except PerfilSuscriptor.DoesNotExist:
        return None


def _es_suscriptor(user):
    return _suscriptor(user) is not None


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
    if _es_admin(user):
        return "dashboard/base_admin.html"
    if _es_suscriptor(user):
        return "asistente_tecnico/base_suscriptor.html"
    return "dashboard/base_trabajador.html"


def _actualizar_recordatorios(user):
    try:
        from dashboard.views import _crear_notificacion
        generar_recordatorios_seguimiento(user=user, crear_notificacion=_crear_notificacion)
    except Exception:
        # El asistente nunca debe bloquear el ingreso a la herramienta por una falla de push.
        pass


def _academia_relacionada_con_diagnostico(resultado, limite=6):
    """Conecta Resolver con contenido oficial sin convertir la Academia en requisito."""
    if not resultado:
        return []
    tipo = (resultado.get("tipo_tratamiento") or "").lower()
    diagnostico = (resultado.get("diagnostico") or "").lower()
    resumen = (resultado.get("resumen") or "").lower()
    texto = f"{tipo} {diagnostico} {resumen}"

    modulos = {"fundamentos"}
    terminos = []
    if "floc" in texto or "verde" in texto or "turb" in texto:
        modulos.update({"problemas", "productos", "mantenimiento"})
        terminos += ["floc", "sulfato", "verde", "turb"]
    if "ph" in texto:
        modulos.add("quimica"); terminos += ["ph", "metasilicato", "reductor"]
    if "cloro" in texto or "desinf" in texto:
        modulos.update({"quimica", "productos"}); terminos += ["cloro", "tricloro"]
    if "filtr" in texto or "circul" in texto:
        modulos.update({"equipos", "preventivo"}); terminos += ["filtro", "bomba", "circul"]

    qs = ContenidoAcademia.objects.filter(estado="aprobado").exclude(acceso="suscriptor")
    filtro = Q(modulo_curso__in=modulos)
    for termino in terminos:
        filtro |= Q(titulo__icontains=termino) | Q(etiquetas__icontains=termino) | Q(resumen__icontains=termino)
    return list(qs.filter(filtro).order_by("orden_curso", "orden", "titulo").distinct()[:limite])


@login_required
@require_http_methods(["GET", "POST"])
def asistente_inicio_view(request):
    # Los suscriptores usan el mismo Motor Técnico JVAQUA, pero a través
    # de la experiencia guiada de JVAQUA Digital. Cualquier enlace antiguo
    # al Asistente técnico se redirige aquí en lugar de devolver 403.
    if _es_suscriptor(request.user):
        return redirect("asistente_tecnico:digital_resolver")
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
        "articulos_relacionados": _academia_relacionada_con_diagnostico(resultado),
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

# =========================
# Centro de Conocimiento JVAQUA
# =========================
from django.db.models import Case, When, IntegerField
from .forms import CategoriaAcademiaForm, LeccionAcademiaForm, ArticuloBibliotecaForm, ConsejoJVAQUAForm
from .models import (
    CategoriaAcademia, LeccionAcademia, ProgresoLeccion,
    ArticuloBiblioteca, ConsejoJVAQUA, PropuestaConocimiento,
)


def _consejo_del_dia():
    qs = ConsejoJVAQUA.objects.filter(activo=True).order_by("orden", "id")
    total = qs.count()
    if not total:
        return None
    idx = timezone.localdate().toordinal() % total
    return qs[idx]


def _progreso_usuario(user):
    total = LeccionAcademia.objects.filter(publicada=True, categoria__activa=True).count()
    completadas = ProgresoLeccion.objects.filter(user=user, completada=True, leccion__publicada=True, leccion__categoria__activa=True).count()
    porcentaje = round((completadas / total) * 100) if total else 0
    return total, completadas, porcentaje


@login_required
def centro_conocimiento_view(request):
    if not (_es_trabajador(request.user) or _es_admin(request.user)):
        return HttpResponseForbidden("No autorizado")
    oficiales = ContenidoAcademia.objects.filter(estado="aprobado")
    if not _es_admin(request.user):
        oficiales = oficiales.exclude(acceso="suscriptor")
    curso = oficiales.exclude(modulo_curso="")
    total = curso.count()
    completadas = ProgresoContenidoAcademia.objects.filter(user=request.user, completado=True, contenido__in=curso).count()
    porcentaje = round((completadas / total) * 100) if total else 0
    recientes = [x.contenido for x in ConsultaContenidoAcademia.objects.filter(user=request.user, contenido__estado="aprobado").select_related("contenido")[:4]]
    favoritos = [x.contenido for x in FavoritoContenidoAcademia.objects.filter(user=request.user, contenido__estado="aprobado").select_related("contenido")[:4]]
    return render(request, "asistente_tecnico/centro_conocimiento.html", {
        "base_template": _base_template(request.user), "consejo": _consejo_del_dia(),
        "total_contenidos": oficiales.count(), "total_curso": total, "completadas": completadas,
        "porcentaje": porcentaje, "recientes": recientes, "favoritos": favoritos,
        "es_admin": _es_admin(request.user),
    })


@login_required
def academia_view(request):
    if not (_es_trabajador(request.user) or _es_admin(request.user)):
        return HttpResponseForbidden("No autorizado")
    completadas_ids = set(ProgresoLeccion.objects.filter(user=request.user, completada=True).values_list("leccion_id", flat=True))
    categorias = list(CategoriaAcademia.objects.filter(activa=True).prefetch_related("lecciones"))
    for cat in categorias:
        publicadas = [x for x in cat.lecciones.all() if x.publicada]
        cat.lecciones_publicadas = publicadas
        cat.total_publicadas = len(publicadas)
        cat.total_completadas = sum(1 for x in publicadas if x.pk in completadas_ids)
        cat.porcentaje = round((cat.total_completadas / cat.total_publicadas) * 100) if cat.total_publicadas else 0
    total, completadas, porcentaje = _progreso_usuario(request.user)
    return render(request, "asistente_tecnico/academia.html", {
        "base_template": _base_template(request.user), "categorias": categorias,
        "completadas_ids": completadas_ids, "total_lecciones": total,
        "completadas": completadas, "porcentaje": porcentaje, "es_admin": _es_admin(request.user),
    })


@login_required
def leccion_detalle_view(request, pk):
    if not (_es_trabajador(request.user) or _es_admin(request.user)):
        return HttpResponseForbidden("No autorizado")
    qs = LeccionAcademia.objects.select_related("categoria")
    if not _es_admin(request.user):
        qs = qs.filter(publicada=True, categoria__activa=True)
    leccion = get_object_or_404(qs, pk=pk)
    completada = ProgresoLeccion.objects.filter(user=request.user, leccion=leccion, completada=True).exists()
    return render(request, "asistente_tecnico/leccion_detalle.html", {
        "base_template": _base_template(request.user), "leccion": leccion,
        "completada": completada, "es_admin": _es_admin(request.user),
    })


@login_required
@require_http_methods(["POST"])
def leccion_completar_view(request, pk):
    if not (_es_trabajador(request.user) or _es_admin(request.user)):
        return HttpResponseForbidden("No autorizado")
    leccion = get_object_or_404(LeccionAcademia, pk=pk, publicada=True, categoria__activa=True)
    ProgresoLeccion.objects.update_or_create(user=request.user, leccion=leccion, defaults={"completada": True, "completada_en": timezone.now()})
    messages.success(request, "Lección marcada como completada.")
    return redirect("asistente_tecnico:leccion_detalle", pk=pk)


@login_required
def biblioteca_tecnica_view(request):
    if not (_es_trabajador(request.user) or _es_admin(request.user)):
        return HttpResponseForbidden("No autorizado")
    q = (request.GET.get("q") or "").strip()
    categoria = (request.GET.get("categoria") or "").strip()
    qs = ArticuloBiblioteca.objects.filter(publicada=True)
    if q:
        qs = qs.filter(Q(titulo__icontains=q) | Q(resumen__icontains=q) | Q(palabras_clave__icontains=q) | Q(fallas_comunes__icontains=q))
    if categoria:
        qs = qs.filter(categoria=categoria)
    return render(request, "asistente_tecnico/biblioteca_tecnica.html", {
        "base_template": _base_template(request.user), "articulos": qs,
        "q": q, "categoria": categoria, "categorias": ArticuloBiblioteca.CATEGORIAS,
        "es_admin": _es_admin(request.user),
    })


@login_required
def articulo_biblioteca_detalle_view(request, pk):
    if not (_es_trabajador(request.user) or _es_admin(request.user)):
        return HttpResponseForbidden("No autorizado")
    qs = ArticuloBiblioteca.objects.all() if _es_admin(request.user) else ArticuloBiblioteca.objects.filter(publicada=True)
    articulo = get_object_or_404(qs, pk=pk)
    return render(request, "asistente_tecnico/biblioteca_detalle.html", {
        "base_template": _base_template(request.user), "articulo": articulo, "es_admin": _es_admin(request.user),
    })


@login_required
def casos_reales_view(request):
    if not (_es_trabajador(request.user) or _es_admin(request.user)):
        return HttpResponseForbidden("No autorizado")
    qs = CasoAsistenteTecnico.objects.filter(destacado=True).select_related("user", "trabajador", "motor")
    return render(request, "asistente_tecnico/casos_reales.html", {
        "base_template": _base_template(request.user), "casos": qs, "es_admin": _es_admin(request.user),
    })


@login_required
def certificacion_view(request):
    if not (_es_trabajador(request.user) or _es_admin(request.user)):
        return HttpResponseForbidden("No autorizado")
    completadas_ids = set(ProgresoLeccion.objects.filter(user=request.user, completada=True).values_list("leccion_id", flat=True))
    categorias = list(CategoriaAcademia.objects.filter(activa=True).prefetch_related("lecciones"))
    filas = []
    for cat in categorias:
        lecciones = [x for x in cat.lecciones.all() if x.publicada]
        total = len(lecciones)
        hechas = sum(1 for x in lecciones if x.pk in completadas_ids)
        porcentaje = round((hechas / total) * 100) if total else 0
        filas.append({"categoria": cat, "total": total, "completadas": hechas, "porcentaje": porcentaje, "insignia": bool(total and hechas == total)})
    total, completadas, porcentaje = _progreso_usuario(request.user)
    return render(request, "asistente_tecnico/certificacion.html", {
        "base_template": _base_template(request.user), "filas": filas,
        "total": total, "completadas": completadas, "porcentaje": porcentaje, "es_admin": _es_admin(request.user),
    })


def _analizar_motor_conocimiento():
    propuestas = []
    qs = CasoAsistenteTecnico.objects.exclude(resultado="pendiente")
    tipos = qs.values("tipo_tratamiento").annotate(total=Count("id"), exitosos=Count("id", filter=Q(resultado="exitoso")), parciales=Count("id", filter=Q(resultado="parcial")), fallidos=Count("id", filter=Q(resultado="fallido")))
    for fila in tipos:
        total = fila["total"]
        if total < 5:
            continue
        tasa = round((fila["exitosos"] / total) * 100, 1) if total else 0
        tipo = fila["tipo_tratamiento"] or "sin_tipo"
        if tasa >= 90:
            titulo = f"Protocolo {tipo}: patrón de alta efectividad"
            descripcion = f"En {total} seguimientos respondidos, el protocolo obtuvo {tasa}% de éxito. Conviene conservar esta referencia y revisar qué condiciones se repiten en los casos exitosos."
        elif tasa < 70:
            titulo = f"Revisar protocolo {tipo}"
            descripcion = f"En {total} seguimientos respondidos, el protocolo obtuvo {tasa}% de éxito. Conviene revisar los casos parciales y fallidos antes de modificar el protocolo oficial."
        else:
            titulo = f"Protocolo {tipo}: evidencia en evaluación"
            descripcion = f"Hay {total} casos respondidos con {tasa}% de éxito. Aún conviene acumular y revisar más evidencia antes de cambiar reglas oficiales."
        fuente = f"protocolo:{tipo}"
        evidencia = {"tipo_tratamiento": tipo, "total": total, "exitosos": fila["exitosos"], "parciales": fila["parciales"], "fallidos": fila["fallidos"], "tasa_exito": tasa}
        obj, _ = PropuestaConocimiento.objects.get_or_create(fuente_clave=fuente, defaults={"titulo": titulo, "descripcion": descripcion, "evidencia": evidencia})
        if obj.estado == "evaluacion":
            obj.titulo = titulo; obj.descripcion = descripcion; obj.evidencia = evidencia; obj.save(update_fields=["titulo", "descripcion", "evidencia", "actualizado_en"])
        propuestas.append(obj)
    return propuestas


@login_required
def motor_conocimiento_view(request):
    if not _es_admin(request.user):
        return HttpResponseForbidden("No autorizado")
    propuestas = PropuestaConocimiento.objects.all()
    return render(request, "asistente_tecnico/motor_conocimiento.html", {
        "base_template": "dashboard/base_admin.html", "propuestas": propuestas, "es_admin": True,
    })


@login_required
@require_http_methods(["POST"])
def motor_conocimiento_analizar_view(request):
    if not _es_admin(request.user):
        return HttpResponseForbidden("No autorizado")
    propuestas = _analizar_motor_conocimiento()
    messages.success(request, f"Análisis completado. Se actualizaron {len(propuestas)} patrones con evidencia suficiente.")
    return redirect("asistente_tecnico:motor_conocimiento")


@login_required
@require_http_methods(["POST"])
def propuesta_conocimiento_estado_view(request, pk):
    if not _es_admin(request.user):
        return HttpResponseForbidden("No autorizado")
    propuesta = get_object_or_404(PropuestaConocimiento, pk=pk)
    estado = request.POST.get("estado")
    if estado not in {x[0] for x in PropuestaConocimiento.ESTADOS}:
        messages.error(request, "Estado inválido.")
    else:
        propuesta.estado = estado
        propuesta.revisado_por = request.user
        propuesta.revisado_en = timezone.now()
        propuesta.nota_revision = (request.POST.get("nota_revision") or "").strip()
        propuesta.save(update_fields=["estado", "revisado_por", "revisado_en", "nota_revision", "actualizado_en"])
        messages.success(request, "Propuesta actualizada. Esta acción no modifica automáticamente el motor de recomendaciones.")
    return redirect("asistente_tecnico:motor_conocimiento")


@login_required
def conocimiento_admin_view(request):
    if not _es_admin(request.user):
        return HttpResponseForbidden("No autorizado")
    return render(request, "asistente_tecnico/conocimiento_admin.html", {
        "base_template": "dashboard/base_admin.html",
        "categorias": CategoriaAcademia.objects.all(),
        "lecciones": LeccionAcademia.objects.select_related("categoria")[:50],
        "articulos": ArticuloBiblioteca.objects.all()[:50],
        "consejos": ConsejoJVAQUA.objects.all()[:50],
        "propuestas_pendientes": PropuestaConocimiento.objects.filter(estado="evaluacion").count(),
        "es_admin": True,
    })


def _crud_conocimiento(request, modelo, form_class, template_title, pk=None):
    if not _es_admin(request.user):
        return HttpResponseForbidden("No autorizado")
    obj = get_object_or_404(modelo, pk=pk) if pk else None
    if request.method == "POST":
        form = form_class(request.POST, instance=obj)
        if form.is_valid():
            nuevo = form.save(commit=False)
            if hasattr(nuevo, "creado_por") and not getattr(nuevo, "creado_por_id", None):
                nuevo.creado_por = request.user
            nuevo.save()
            messages.success(request, "Contenido guardado correctamente.")
            return redirect("asistente_tecnico:conocimiento_admin")
    else:
        form = form_class(instance=obj)
    return render(request, "asistente_tecnico/contenido_form.html", {
        "base_template": "dashboard/base_admin.html", "form": form, "titulo": template_title, "obj": obj, "es_admin": True,
    })


@login_required
@require_http_methods(["GET", "POST"])
def categoria_form_view(request, pk=None):
    return _crud_conocimiento(request, CategoriaAcademia, CategoriaAcademiaForm, "Categoría de Academia", pk)


@login_required
@require_http_methods(["GET", "POST"])
def leccion_form_view(request, pk=None):
    return _crud_conocimiento(request, LeccionAcademia, LeccionAcademiaForm, "Lección de Academia", pk)


@login_required
@require_http_methods(["GET", "POST"])
def articulo_form_view(request, pk=None):
    return _crud_conocimiento(request, ArticuloBiblioteca, ArticuloBibliotecaForm, "Artículo de Biblioteca", pk)


@login_required
@require_http_methods(["GET", "POST"])
def consejo_form_view(request, pk=None):
    return _crud_conocimiento(request, ConsejoJVAQUA, ConsejoJVAQUAForm, "Consejo JVAQUA", pk)


# ============================================================
# Academia JVAQUA CMS - Sprint 3.1
# ============================================================
from django.http import HttpResponse
from django.utils.text import slugify
from .forms import ContenidoAcademiaForm, ImagenContenidoAcademiaForm, MaterialAudiovisualAcademiaForm, MaterialAudiovisualAcademiaForm, ExperienciaConocimientoForm
from .models import (
    ContenidoAcademia, ImagenContenidoAcademia, MaterialAudiovisualAcademia, VersionContenidoAcademia, ExperienciaConocimiento,
    ProgresoContenidoAcademia, FavoritoContenidoAcademia, ConsultaContenidoAcademia,
)


def _snapshot_contenido(obj):
    campos = [
        "tipo", "codigo", "titulo", "slug", "resumen", "nivel", "tiempo_lectura_min", "estado", "version",
        "introduccion", "contenido", "procedimiento", "herramientas_materiales", "funcionamiento", "componentes",
        "mantenimiento", "fallas_frecuentes", "buenas_practicas", "errores_comunes", "recomendaciones_jvaqua",
        "referencias_tecnicas", "etiquetas", "acceso", "modulo_curso", "orden_curso", "orden",
    ]
    return {c: getattr(obj, c, "") for c in campos}


def _guardar_version(obj, user, motivo=""):
    VersionContenidoAcademia.objects.create(
        contenido=obj, version=obj.version, snapshot=_snapshot_contenido(obj), motivo=motivo, creado_por=user,
    )


@login_required
def academia_cms_admin_view(request):
    if not _es_admin(request.user):
        return HttpResponseForbidden("No autorizado")
    qs = ContenidoAcademia.objects.all()
    q = (request.GET.get("q") or "").strip()
    tipo = (request.GET.get("tipo") or "").strip()
    estado = (request.GET.get("estado") or "").strip()
    if q:
        qs = qs.filter(Q(titulo__icontains=q) | Q(codigo__icontains=q) | Q(resumen__icontains=q) | Q(etiquetas__icontains=q) | Q(contenido__icontains=q))
    if tipo:
        qs = qs.filter(tipo=tipo)
    if estado:
        qs = qs.filter(estado=estado)
    ctx = {
        "base_template": "dashboard/base_admin.html", "contenidos": qs[:200], "q": q, "tipo": tipo, "estado": estado,
        "tipos": ContenidoAcademia.TIPOS, "estados": ContenidoAcademia.ESTADOS,
        "total": ContenidoAcademia.objects.count(),
        "aprobados": ContenidoAcademia.objects.filter(estado="aprobado").count(),
        "borradores": ContenidoAcademia.objects.filter(estado="borrador").count(),
        "archivados": ContenidoAcademia.objects.filter(estado="archivado").count(),
        "experiencias_revision": ExperienciaConocimiento.objects.filter(estado="revision").count(),
        "es_admin": True,
    }
    return render(request, "asistente_tecnico/cms_admin.html", ctx)


@login_required
@require_http_methods(["GET", "POST"])
def academia_cms_contenido_form_view(request, pk=None):
    if not _es_admin(request.user):
        return HttpResponseForbidden("No autorizado")
    obj = get_object_or_404(ContenidoAcademia, pk=pk) if pk else None
    estado_anterior = obj.estado if obj else None
    version_anterior = obj.version if obj else None
    if request.method == "POST":
        form = ContenidoAcademiaForm(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            nuevo = form.save(commit=False)
            if not nuevo.creado_por_id:
                nuevo.creado_por = request.user
            if nuevo.estado == "aprobado" and estado_anterior != "aprobado":
                nuevo.aprobado_por = request.user
                nuevo.aprobado_en = timezone.now()
            elif nuevo.estado != "aprobado":
                nuevo.aprobado_por = None
                nuevo.aprobado_en = None
            nuevo.save()
            form.save_m2m()
            motivo = (request.POST.get("motivo_version") or "").strip()
            if not obj or version_anterior != nuevo.version or motivo or estado_anterior != nuevo.estado:
                _guardar_version(nuevo, request.user, motivo or "Actualización de contenido")
            messages.success(request, "Contenido guardado correctamente.")
            return redirect("asistente_tecnico:cms_admin")
    else:
        form = ContenidoAcademiaForm(instance=obj)
    return render(request, "asistente_tecnico/cms_contenido_form.html", {
        "base_template": "dashboard/base_admin.html", "form": form, "obj": obj, "es_admin": True,
    })


@login_required
@require_http_methods(["GET", "POST"])
def academia_cms_imagen_form_view(request, contenido_pk):
    if not _es_admin(request.user):
        return HttpResponseForbidden("No autorizado")
    contenido = get_object_or_404(ContenidoAcademia, pk=contenido_pk)
    if request.method == "POST":
        form = ImagenContenidoAcademiaForm(request.POST, request.FILES)
        if form.is_valid():
            imagen = form.save(commit=False); imagen.contenido = contenido; imagen.save()
            messages.success(request, "Imagen añadida a la galería.")
            return redirect("asistente_tecnico:cms_contenido_editar", pk=contenido.pk)
    else:
        form = ImagenContenidoAcademiaForm()
    return render(request, "asistente_tecnico/cms_imagen_form.html", {"base_template":"dashboard/base_admin.html","form":form,"contenido":contenido,"es_admin":True})


@login_required
@require_http_methods(["GET", "POST"])
def academia_cms_material_form_view(request, contenido_pk):
    if not _es_admin(request.user):
        return HttpResponseForbidden("No autorizado")
    contenido = get_object_or_404(ContenidoAcademia, pk=contenido_pk)
    if request.method == "POST":
        form = MaterialAudiovisualAcademiaForm(request.POST, request.FILES)
        if form.is_valid():
            material = form.save(commit=False)
            material.contenido = contenido
            material.save()
            messages.success(request, "Material audiovisual añadido correctamente.")
            return redirect("asistente_tecnico:cms_contenido_editar", pk=contenido.pk)
    else:
        form = MaterialAudiovisualAcademiaForm()
    return render(
        request,
        "asistente_tecnico/cms_material_form.html",
        {"base_template": "dashboard/base_admin.html", "form": form, "contenido": contenido, "es_admin": True},
    )


@login_required
@require_http_methods(["POST"])
def academia_cms_material_eliminar_view(request, pk):
    if not _es_admin(request.user):
        return HttpResponseForbidden("No autorizado")
    material = get_object_or_404(MaterialAudiovisualAcademia, pk=pk)
    contenido_pk = material.contenido_id
    material.delete()
    messages.success(request, "Material audiovisual eliminado.")
    return redirect("asistente_tecnico:cms_contenido_editar", pk=contenido_pk)


@login_required
@require_http_methods(["POST"])
def academia_cms_imagen_eliminar_view(request, pk):
    if not _es_admin(request.user):
        return HttpResponseForbidden("No autorizado")
    imagen = get_object_or_404(ImagenContenidoAcademia, pk=pk); contenido_pk = imagen.contenido_id; imagen.delete()
    messages.success(request, "Imagen eliminada.")
    return redirect("asistente_tecnico:cms_contenido_editar", pk=contenido_pk)


@login_required
def academia_publica_view(request):
    if not (_es_trabajador(request.user) or _es_admin(request.user) or _es_suscriptor(request.user)):
        return HttpResponseForbidden("No autorizado")

    visibles = ContenidoAcademia.objects.filter(estado="aprobado")
    if _es_suscriptor(request.user):
        visibles = visibles.exclude(acceso="interno")
    elif not _es_admin(request.user):
        visibles = visibles.exclude(acceso="suscriptor")

    q = (request.GET.get("q") or "").strip()
    tipo = (request.GET.get("tipo") or "").strip()
    modo = (request.GET.get("modo") or "consultar").strip()
    modulo = (request.GET.get("modulo") or "").strip()

    completadas_ids = set(
        ProgresoContenidoAcademia.objects.filter(user=request.user, completado=True)
        .values_list("contenido_id", flat=True)
    )

    # El progreso siempre representa el curso completo visible para el usuario,
    # independientemente de los filtros de búsqueda que esté usando.
    curso_base = list(visibles.exclude(modulo_curso="").order_by("orden", "titulo"))
    rango_modulo = {codigo: i for i, (codigo, _nombre) in enumerate(ContenidoAcademia.MODULOS_CURSO)}
    curso_base.sort(key=lambda x: (rango_modulo.get(x.modulo_curso, 999), x.orden_curso, x.orden, x.titulo.lower()))
    curso_total = len(curso_base)
    curso_completadas = sum(1 for c in curso_base if c.pk in completadas_ids)
    curso_porcentaje = round((curso_completadas / curso_total) * 100) if curso_total else 0
    continuar = next((c for c in curso_base if c.pk not in completadas_ids), None)

    qs = visibles
    if q:
        qs = qs.filter(
            Q(titulo__icontains=q) | Q(resumen__icontains=q) | Q(etiquetas__icontains=q) |
            Q(contenido__icontains=q) | Q(procedimiento__icontains=q) |
            Q(fallas_frecuentes__icontains=q)
        )
    if tipo:
        qs = qs.filter(tipo=tipo)
    if modulo:
        qs = qs.filter(modulo_curso=modulo)

    grupos_curso = []
    recientes = [x.contenido for x in ConsultaContenidoAcademia.objects.filter(
        user=request.user, contenido__estado="aprobado"
    ).select_related("contenido")[:6]]
    favoritos = [x.contenido for x in FavoritoContenidoAcademia.objects.filter(
        user=request.user, contenido__estado="aprobado"
    ).select_related("contenido")[:6]]

    if modo == "aprender":
        lista = list(qs.exclude(modulo_curso=""))
        lista.sort(key=lambda x: (rango_modulo.get(x.modulo_curso, 999), x.orden_curso, x.orden, x.titulo.lower()))
        for codigo, nombre in ContenidoAcademia.MODULOS_CURSO:
            contenidos_modulo = [c for c in lista if c.modulo_curso == codigo]
            if contenidos_modulo:
                hechos = sum(1 for c in contenidos_modulo if c.pk in completadas_ids)
                grupos_curso.append({
                    "codigo": codigo,
                    "nombre": nombre,
                    "contenidos": contenidos_modulo,
                    "total": len(contenidos_modulo),
                    "completados": hechos,
                    "porcentaje": round((hechos / len(contenidos_modulo)) * 100) if contenidos_modulo else 0,
                })
        contenidos = lista
    else:
        contenidos = list(qs.order_by("tipo", "orden", "titulo")[:200])

    return render(request, "asistente_tecnico/academia_cms_publica.html", {
        "base_template": _base_template(request.user),
        "contenidos": contenidos,
        "grupos_curso": grupos_curso,
        "q": q, "tipo": tipo, "modo": modo, "modulo": modulo,
        "tipos": ContenidoAcademia.TIPOS, "modulos": ContenidoAcademia.MODULOS_CURSO,
        "completadas_ids": completadas_ids,
        "curso_total": curso_total, "curso_completadas": curso_completadas,
        "curso_porcentaje": curso_porcentaje, "continuar": continuar,
        "curso_xp": curso_completadas * 40,
        "recientes": recientes, "favoritos": favoritos,
        "es_admin": _es_admin(request.user), "consejo": _consejo_del_dia(),
    })

@login_required
def academia_contenido_detalle_view(request, slug):
    if not (_es_trabajador(request.user) or _es_admin(request.user) or _es_suscriptor(request.user)):
        return HttpResponseForbidden("No autorizado")
    filtros = {"slug": slug}
    if not _es_admin(request.user):
        filtros["estado"] = "aprobado"
    obj = get_object_or_404(
        ContenidoAcademia.objects.prefetch_related("relacionados", "galeria"), **filtros
    )
    if _es_suscriptor(request.user) and obj.acceso == "interno":
        return HttpResponseForbidden("Contenido exclusivo del equipo JVAQUA")
    if not (_es_admin(request.user) or _es_suscriptor(request.user)) and obj.acceso == "suscriptor":
        return HttpResponseForbidden("Contenido no disponible para este perfil")

    ConsultaContenidoAcademia.objects.update_or_create(
        user=request.user, contenido=obj, defaults={"consultado_en": timezone.now()}
    )
    completado = ProgresoContenidoAcademia.objects.filter(
        user=request.user, contenido=obj, completado=True
    ).exists()
    favorito = FavoritoContenidoAcademia.objects.filter(user=request.user, contenido=obj).exists()

    siguiente = None
    if obj.modulo_curso:
        visibles = ContenidoAcademia.objects.filter(estado="aprobado").exclude(modulo_curso="")
        if _es_suscriptor(request.user):
            visibles = visibles.exclude(acceso="interno")
        elif not _es_admin(request.user):
            visibles = visibles.exclude(acceso="suscriptor")
        lista = list(visibles)
        rango_modulo = {codigo: i for i, (codigo, _nombre) in enumerate(ContenidoAcademia.MODULOS_CURSO)}
        lista.sort(key=lambda x: (rango_modulo.get(x.modulo_curso, 999), x.orden_curso, x.orden, x.titulo.lower()))
        ids = [c.pk for c in lista]
        if obj.pk in ids:
            idx = ids.index(obj.pk)
            if idx + 1 < len(lista):
                siguiente = lista[idx + 1]

    return render(request, "asistente_tecnico/academia_contenido_detalle.html", {
        "base_template": _base_template(request.user), "obj": obj,
        "es_admin": _es_admin(request.user), "completado": completado,
        "favorito": favorito, "siguiente": siguiente, "es_curso": request.GET.get("curso") == "1",
    })

@login_required
@require_http_methods(["POST"])
def academia_contenido_completar_view(request, slug):
    obj = get_object_or_404(ContenidoAcademia, slug=slug, estado="aprobado")
    if _es_suscriptor(request.user) and obj.acceso == "interno":
        return HttpResponseForbidden("Contenido exclusivo del equipo JVAQUA")
    ProgresoContenidoAcademia.objects.update_or_create(user=request.user, contenido=obj, defaults={"completado": True, "completado_en": timezone.now()})
    messages.success(request, "Contenido marcado como aprendido.")
    return redirect("asistente_tecnico:academia_contenido_detalle", slug=slug)


@login_required
@require_http_methods(["POST"])
def academia_contenido_favorito_view(request, slug):
    obj = get_object_or_404(ContenidoAcademia, slug=slug, estado="aprobado")
    if _es_suscriptor(request.user) and obj.acceso == "interno":
        return HttpResponseForbidden("Contenido exclusivo del equipo JVAQUA")
    fav = FavoritoContenidoAcademia.objects.filter(user=request.user, contenido=obj)
    if fav.exists():
        fav.delete(); messages.info(request, "Eliminado de favoritos.")
    else:
        FavoritoContenidoAcademia.objects.create(user=request.user, contenido=obj); messages.success(request, "Guardado en favoritos.")
    return redirect("asistente_tecnico:academia_contenido_detalle", slug=slug)


@login_required
@require_http_methods(["GET", "POST"])
def experiencia_conocimiento_form_view(request, pk=None):
    if not _es_admin(request.user):
        return HttpResponseForbidden("No autorizado")
    obj = get_object_or_404(ExperienciaConocimiento, pk=pk) if pk else None
    if request.method == "POST":
        form = ExperienciaConocimientoForm(request.POST, instance=obj)
        if form.is_valid():
            nuevo=form.save(commit=False)
            if not nuevo.creado_por_id: nuevo.creado_por=request.user
            if nuevo.estado in {"aprobada","descartada"}: nuevo.revisado_por=request.user
            nuevo.save(); messages.success(request,"Experiencia guardada."); return redirect("asistente_tecnico:cms_experiencias")
    else: form=ExperienciaConocimientoForm(instance=obj)
    return render(request,"asistente_tecnico/cms_experiencia_form.html",{"base_template":"dashboard/base_admin.html","form":form,"obj":obj,"es_admin":True})


@login_required
def experiencias_conocimiento_view(request):
    if not _es_admin(request.user): return HttpResponseForbidden("No autorizado")
    return render(request,"asistente_tecnico/cms_experiencias.html",{"base_template":"dashboard/base_admin.html","experiencias":ExperienciaConocimiento.objects.all()[:200],"es_admin":True})


@login_required
@require_http_methods(["POST"])
def experiencia_convertir_view(request, pk):
    if not _es_admin(request.user): return HttpResponseForbidden("No autorizado")
    exp=get_object_or_404(ExperienciaConocimiento,pk=pk)
    if exp.convertido_en_id:
        messages.info(request,"Esta experiencia ya fue convertida en contenido oficial.")
        return redirect("asistente_tecnico:cms_experiencias")
    tipo=exp.destino_sugerido or "biblioteca"
    base=slugify(exp.titulo) or f"experiencia-{exp.pk}"; slug=base; n=2
    while ContenidoAcademia.objects.filter(slug=slug).exists(): slug=f"{base}-{n}"; n+=1
    codigo=f"EXP-{exp.pk:05d}"
    while ContenidoAcademia.objects.filter(codigo=codigo).exists(): codigo=f"EXP-{exp.pk:05d}-{n}"; n+=1
    contenido=ContenidoAcademia.objects.create(tipo=tipo,codigo=codigo,titulo=exp.titulo,slug=slug,resumen=exp.problema[:320],introduccion=exp.analisis,contenido=exp.solucion,buenas_practicas=exp.aprendizaje,recomendaciones_jvaqua=exp.resultado,estado="borrador",creado_por=request.user)
    _guardar_version(contenido,request.user,"Creado desde Base de Conocimiento")
    exp.convertido_en=contenido; exp.save(update_fields=["convertido_en","actualizado_en"])
    messages.success(request,"Experiencia convertida en borrador. Revísala y apruébala antes de publicarla.")
    return redirect("asistente_tecnico:cms_contenido_editar",pk=contenido.pk)


def _pdf_styles():
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name="JTitle", parent=styles["Title"], alignment=TA_CENTER, textColor="#0A5AA8", spaceAfter=12))
    styles.add(ParagraphStyle(name="JH", parent=styles["Heading2"], textColor="#0A5AA8", spaceBefore=10, spaceAfter=6))
    return styles


def _texto_pdf(texto):
    import html
    return html.escape(texto or "").replace("\n", "<br/>")


def _contenido_story(obj, styles):
    from reportlab.platypus import Paragraph, Spacer
    story=[Paragraph("JVAQUA · Manual Técnico Oficial",styles["JTitle"]),Paragraph(_texto_pdf(obj.titulo),styles["Heading1"])]
    story += [Paragraph(f"{obj.get_tipo_display()} · Nivel {obj.get_nivel_display()} · Versión {obj.version}", styles["Normal"]), Spacer(1,10)]
    if obj.resumen: story += [Paragraph(_texto_pdf(obj.resumen),styles["Italic"]),Spacer(1,8)]
    secciones=[("Introducción",obj.introduccion),("Contenido",obj.contenido),("Procedimiento",obj.procedimiento),("Herramientas / materiales",obj.herramientas_materiales),("Funcionamiento",obj.funcionamiento),("Componentes",obj.componentes),("Mantenimiento",obj.mantenimiento),("Fallas frecuentes",obj.fallas_frecuentes),("Buenas prácticas",obj.buenas_practicas),("Errores comunes",obj.errores_comunes),("Recomendaciones JVAQUA",obj.recomendaciones_jvaqua),("Referencias técnicas",obj.referencias_tecnicas)]
    for titulo,texto in secciones:
        if texto: story += [Paragraph(titulo,styles["JH"]),Paragraph(_texto_pdf(texto),styles["BodyText"]),Spacer(1,6)]
    return story


def _pdf_response(nombre, objetos):
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, PageBreak, Paragraph
    buf=BytesIO(); doc=SimpleDocTemplate(buf,pagesize=A4,rightMargin=16*mm,leftMargin=16*mm,topMargin=16*mm,bottomMargin=16*mm)
    styles=_pdf_styles(); story=[]
    objs=list(objetos)
    if len(objs)>1:
        story += [Paragraph("JVAQUA",styles["JTitle"]),Paragraph("Manual Técnico Oficial",styles["Title"]),Paragraph(f"Contenido aprobado · {timezone.localdate().strftime('%d/%m/%Y')}",styles["Normal"]),PageBreak()]
    for i,obj in enumerate(objs):
        if i: story.append(PageBreak())
        story.extend(_contenido_story(obj,styles))
    doc.build(story); data=buf.getvalue(); buf.close()
    resp=HttpResponse(data,content_type="application/pdf"); resp["Content-Disposition"]=f'attachment; filename="{nombre}"'; return resp


@login_required
def academia_pdf_articulo_view(request, slug):
    filtros={"slug":slug};
    if not _es_admin(request.user): filtros["estado"]="aprobado"
    obj=get_object_or_404(ContenidoAcademia,**filtros)
    return _pdf_response(f"JVAQUA_{slug}.pdf",[obj])


@login_required
def academia_pdf_categoria_view(request, tipo):
    if tipo not in {x[0] for x in ContenidoAcademia.TIPOS}: return HttpResponse("Tipo inválido",status=400)
    qs=ContenidoAcademia.objects.filter(estado="aprobado",tipo=tipo)
    return _pdf_response(f"JVAQUA_{tipo}.pdf",qs)


@login_required
def academia_pdf_manual_view(request):
    qs=ContenidoAcademia.objects.filter(estado="aprobado")
    return _pdf_response("Manual_Tecnico_Oficial_JVAQUA.pdf",qs)

@login_required
def digital_inicio_view(request):
    perfil = _suscriptor(request.user)
    if not perfil:
        return HttpResponseForbidden("Tu acceso a JVAQUA Digital no está activo.")
    piscinas = perfil.piscinas.filter(activa=True)
    principal = piscinas.filter(principal=True).first() or piscinas.first()
    recientes_qs = CasoAsistenteTecnico.objects.filter(user=request.user)
    if principal:
        recientes_qs = recientes_qs.filter(piscina=principal)
    recientes = recientes_qs[:4]
    progreso_total = ContenidoAcademia.objects.filter(estado="aprobado").exclude(acceso="interno").exclude(modulo_curso="").count()
    completados = ProgresoContenidoAcademia.objects.filter(user=request.user, completado=True, contenido__estado="aprobado").exclude(contenido__acceso="interno").count()
    porcentaje = round(completados * 100 / progreso_total) if progreso_total else 0
    plan = PlanMantenimientoPiscina.objects.filter(piscina=principal, activo=True).first() if principal else None
    return render(request, "asistente_tecnico/digital_inicio.html", {"perfil":perfil,"piscinas":piscinas,"principal":principal,"recientes":recientes,"curso_porcentaje":porcentaje,"plan_mantenimiento":plan,"base_template":"asistente_tecnico/base_suscriptor.html"})


@login_required
def digital_piscinas_view(request):
    perfil = _suscriptor(request.user)
    if not perfil:
        return HttpResponseForbidden("No autorizado")
    piscinas = perfil.piscinas.filter(activa=True)
    return render(
        request,
        "asistente_tecnico/digital_piscinas.html",
        {"perfil": perfil, "piscinas": piscinas},
    )


@login_required
def digital_piscina_detalle_view(request, pk):
    perfil = _suscriptor(request.user)
    if not perfil:
        return HttpResponseForbidden("No autorizado")
    piscina = get_object_or_404(PiscinaSuscriptor, pk=pk, suscriptor=perfil, activa=True)
    casos = piscina.casos_asistente.filter(user=request.user)[:12]
    mantenimientos = piscina.mantenimientos_digitales.all()[:12]
    visitas = piscina.visitas_programadas.all()[:12]
    plan = PlanMantenimientoPiscina.objects.filter(piscina=piscina, activo=True).first()
    return render(
        request,
        "asistente_tecnico/digital_piscina_detalle.html",
        {
            "perfil": perfil,
            "piscina": piscina,
            "casos": casos,
            "mantenimientos": mantenimientos,
            "visitas": visitas,
            "plan": plan,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def digital_sugerencias_view(request):
    perfil = _suscriptor(request.user)
    if not perfil:
        return HttpResponseForbidden("No autorizado")
    piscinas = perfil.piscinas.filter(activa=True)
    if request.method == "POST":
        categoria = (request.POST.get("categoria") or "general").strip()
        if categoria not in {x[0] for x in SugerenciaDigital.CATEGORIAS}:
            categoria = "general"
        mensaje = (request.POST.get("mensaje") or "").strip()
        piscina = None
        piscina_id = request.POST.get("piscina_id")
        if piscina_id:
            piscina = piscinas.filter(pk=piscina_id).first()
        calificacion = None
        try:
            valor = int(request.POST.get("calificacion") or 0)
            if 1 <= valor <= 5:
                calificacion = valor
        except (TypeError, ValueError):
            pass
        if len(mensaje) < 5:
            messages.error(request, "Cuéntanos un poco más para poder entender tu sugerencia.")
        else:
            SugerenciaDigital.objects.create(
                suscriptor=perfil,
                piscina=piscina,
                categoria=categoria,
                calificacion=calificacion,
                mensaje=mensaje,
            )
            messages.success(request, "Gracias. Tu opinión fue enviada directamente a JVAQUA.")
            return redirect("asistente_tecnico:digital_sugerencias")
    propias = perfil.sugerencias_digitales.all()[:6]
    return render(
        request,
        "asistente_tecnico/digital_sugerencias.html",
        {
            "perfil": perfil,
            "piscinas": piscinas,
            "categorias": SugerenciaDigital.CATEGORIAS,
            "propias": propias,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def digital_piscina_form_view(request, pk=None):
    perfil = _suscriptor(request.user)
    if not perfil: return HttpResponseForbidden("No autorizado")
    obj = get_object_or_404(PiscinaSuscriptor, pk=pk, suscriptor=perfil) if pk else None
    if request.method == "POST":
        try:
            largo = Decimal((request.POST.get("largo_m") or "0").replace(",",".")) if request.POST.get("largo_m") else None
            ancho = Decimal((request.POST.get("ancho_m") or "0").replace(",",".")) if request.POST.get("ancho_m") else None
            profundidad = Decimal((request.POST.get("profundidad_m") or "0").replace(",",".")) if request.POST.get("profundidad_m") else None
            vol_txt=(request.POST.get("volumen_m3") or "").replace(",",".")
            volumen=Decimal(vol_txt) if vol_txt else ((largo*ancho*profundidad).quantize(Decimal("0.01")) if largo and ancho and profundidad else Decimal("0"))
            if volumen <= 0: raise ValueError
        except (InvalidOperation, ValueError):
            messages.error(request,"Ingresa un volumen válido o las tres dimensiones de la piscina.")
        else:
            if obj is None:
                if perfil.piscinas.filter(activa=True).count() >= perfil.limite_piscinas:
                    messages.error(request, f"Tu plan {perfil.get_plan_display()} permite hasta {perfil.limite_piscinas} piscinas. Cambia a Plus para administrar hasta 30.")
                    return redirect("asistente_tecnico:digital_inicio")
                obj=PiscinaSuscriptor(suscriptor=perfil)
            obj.nombre=(request.POST.get("nombre") or "Mi piscina").strip()[:100]
            obj.tipo_piscina=request.POST.get("tipo_piscina") or "residencial"
            obj.largo_m=largo; obj.ancho_m=ancho; obj.profundidad_m=profundidad; obj.volumen_m3=volumen
            obj.tipo_filtro=request.POST.get("tipo_filtro") or "otro"; obj.desinfeccion=request.POST.get("desinfeccion") or "otro"
            obj.origen_agua=request.POST.get("origen_agua") or "potable"; obj.antecedente_hierro=request.POST.get("antecedente_hierro") or "no_se"
            obj.notas=(request.POST.get("notas") or "").strip(); obj.principal=request.POST.get("principal")=="on"; obj.save()
            messages.success(request,"Piscina guardada. El Asistente ya puede usar estos datos.")
            return redirect("asistente_tecnico:digital_inicio")
    return render(request,"asistente_tecnico/digital_piscina_form.html",{"obj":obj,"tipo_choices":PiscinaSuscriptor.TIPOS,"filtro_choices":PiscinaSuscriptor.FILTROS,"desinfeccion_choices":PiscinaSuscriptor.DESINFECCION,"origen_agua_choices":PiscinaSuscriptor.ORIGEN_AGUA,"hierro_choices":PiscinaSuscriptor.HIERRO})

@login_required
@require_http_methods(["GET", "POST"])
def digital_plan_mantenimiento_view(request, pk):
    perfil = _suscriptor(request.user)
    if not perfil:
        return HttpResponseForbidden("No autorizado")

    piscina = get_object_or_404(
        PiscinaSuscriptor, pk=pk, suscriptor=perfil, activa=True
    )
    plan, _ = PlanMantenimientoPiscina.objects.get_or_create(piscina=piscina)

    resultado = None
    plan_visitas = []
    valores = {
        "frecuencia": plan.frecuencia_semanal,
        "ph": "",
        "cloro": "",
        "estado_agua": "transparente",
    }

    def _fechas_semana(frecuencia):
        """Distribuye las visitas de forma uniforme desde hoy en los próximos 7 días."""
        hoy = timezone.localdate()
        if frecuencia <= 1:
            return [hoy]
        offsets = [int(i * 7 / frecuencia) for i in range(frecuencia)]
        return [hoy + timedelta(days=offset) for offset in offsets]

    def _guia_para(texto):
        texto = (texto or "").lower()
        if "ph" in texto or ("cloro" in texto and "medir" in texto):
            return "medir pH y cloro"
        if "pozo" in texto or "hierro" in texto or "precipitado" in texto:
            return "agua de pozo hierro"
        if "aspir" in texto:
            return "aspirado piscina"
        if "cepill" in texto:
            return "cepillado piscina"
        if "basura" in texto or "superficial" in texto:
            return "limpieza superficial cernidera"
        if "canastilla" in texto or "skimmer" in texto:
            return "limpieza skimmer canastilla bomba"
        if "retrolavado" in texto:
            return "retrolavado filtro"
        if "tratamiento" in texto or "químico" in texto or "quimico" in texto:
            return "tratamiento químico mantenimiento"
        return "mantenimiento piscina"

    def _armar_tareas(numero, recomendacion):
        base = plan.rutina_visita(numero)
        tareas = []
        productos_agregados = False

        for tarea in base:
            es_tratamiento = "tratamiento químico" in tarea.lower() or "tratamiento quimico" in tarea.lower()
            if es_tratamiento and numero == 1:
                productos = recomendacion.get("productos_sugeridos", []) if recomendacion else []
                if productos:
                    for producto in productos:
                        tareas.append({
                            "tipo": "quimico",
                            "titulo": f"Aplicar {producto.get('nombre', 'producto recomendado')}",
                            "detalle": f"{producto.get('cantidad', '')} {producto.get('unidad', '')}".strip(),
                            "motivo": producto.get("motivo", ""),
                            "guia": producto.get("nombre", "tratamiento químico"),
                        })
                    productos_agregados = True
                else:
                    tareas.append({
                        "tipo": "ok",
                        "titulo": "No aplicar correctivos químicos adicionales",
                        "detalle": "Las mediciones no requieren una corrección adicional según los estándares actuales de AQUO.",
                        "motivo": "",
                        "guia": "tratamiento químico mantenimiento",
                    })
                    productos_agregados = True
                continue

            if es_tratamiento and numero > 1:
                tareas.append({
                    "tipo": "control",
                    "titulo": "Volver a medir pH y cloro antes de agregar químicos",
                    "detalle": "No repitas automáticamente la dosis de la primera visita. Si las mediciones cambiaron, vuelve a calcular con AQUO.",
                    "motivo": "",
                    "guia": "medir pH y cloro",
                })
                continue

            tareas.append({
                "tipo": "tarea",
                "titulo": tarea,
                "detalle": "",
                "motivo": "",
                "guia": _guia_para(tarea),
            })

        if numero == 1 and recomendacion and recomendacion.get("protocolo"):
            for paso in recomendacion["protocolo"]:
                titulo = str(paso.get("titulo", "")).strip()
                detalle = str(paso.get("detalle", "")).strip()
                if not titulo:
                    continue
                # No duplicar el producto si ya está reflejado como tarea de dosificación.
                if productos_agregados and "aplicar" in titulo.lower():
                    continue
                tareas.append({
                    "tipo": "protocolo",
                    "titulo": titulo,
                    "detalle": detalle,
                    "motivo": "",
                    "guia": _guia_para(titulo + " " + detalle),
                })
        return tareas

    if request.method == "POST":
        try:
            frecuencia = int(request.POST.get("frecuencia_semanal") or 1)
        except (TypeError, ValueError):
            frecuencia = 1
        frecuencia = min(max(frecuencia, 1), 7)

        ph_txt = (request.POST.get("ph") or "").replace(",", ".").strip()
        cloro_txt = (request.POST.get("cloro") or "").replace(",", ".").strip()
        estado = (request.POST.get("estado_agua") or "transparente").strip()
        valores = {
            "frecuencia": frecuencia,
            "ph": ph_txt,
            "cloro": cloro_txt,
            "estado_agua": estado,
        }

        try:
            ph = Decimal(ph_txt)
            cloro = Decimal(cloro_txt)
            if ph <= 0 or cloro < 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            messages.error(
                request,
                "Ingresa valores válidos de pH y cloro para crear el plan semanal.",
            )
        else:
            plan.frecuencia_semanal = frecuencia
            plan.save(update_fields=["frecuencia_semanal", "actualizado_en"])

            resultado = calcular_recomendacion(
                volumen=float(piscina.volumen_m3),
                ph=float(ph),
                cloro=float(cloro),
                estado_agua=estado,
                tipo_piscina=piscina.tipo_piscina,
                tipo_agua=piscina.origen_agua,
                antecedente_hierro=piscina.antecedente_hierro,
            )

            fechas = _fechas_semana(frecuencia)
            # Reprogramar únicamente visitas futuras aún no ejecutadas de este ciclo.
            VisitaProgramadaPiscina.objects.filter(
                plan=plan,
                fecha__gte=timezone.localdate(),
                estado="programada",
            ).delete()

            for numero, fecha in enumerate(fechas, start=1):
                tareas = _armar_tareas(numero, resultado)
                visita = VisitaProgramadaPiscina.objects.create(
                    plan=plan,
                    piscina=piscina,
                    fecha=fecha,
                    visita_numero=numero,
                    plan_resultado={
                        "ph_inicial": str(ph),
                        "cloro_inicial": str(cloro),
                        "estado_agua": estado,
                        "diagnostico": resultado.get("diagnostico", ""),
                        "tareas": tareas,
                    },
                )
                plan_visitas.append({
                    "obj": visita,
                    "fecha": fecha,
                    "numero": numero,
                    "tareas": tareas,
                })

                # La notificación queda programada para las 07:00 del día de la visita.
                momento = timezone.make_aware(
                    datetime.combine(fecha, time(hour=7)),
                    timezone.get_current_timezone(),
                )
                NotificacionDigital.objects.get_or_create(
                    suscriptor=perfil,
                    visita=visita,
                    tipo="visita_hoy",
                    defaults={
                        "piscina": piscina,
                        "titulo": f"Mantenimiento de {piscina.nombre}",
                        "mensaje": f"Hoy corresponde la visita {numero} de {frecuencia}. Abre tu plan y sigue los pasos preparados por AQUO.",
                        "programada_para": momento,
                    },
                )

            NotificacionDigital.objects.create(
                suscriptor=perfil,
                piscina=piscina,
                tipo="plan_creado",
                titulo="Plan semanal preparado",
                mensaje=f"AQUO programó {frecuencia} visita{'s' if frecuencia != 1 else ''} para {piscina.nombre}.",
                programada_para=timezone.now(),
            )
            messages.success(
                request,
                f"AQUO preparó y programó {frecuencia} visita{'s' if frecuencia != 1 else ''} para los próximos 7 días.",
            )
    else:
        visitas_guardadas = VisitaProgramadaPiscina.objects.filter(
            plan=plan,
            fecha__gte=timezone.localdate(),
            estado="programada",
        ).order_by("fecha", "visita_numero")[:7]
        for visita in visitas_guardadas:
            data = visita.plan_resultado or {}
            plan_visitas.append({
                "obj": visita,
                "fecha": visita.fecha,
                "numero": visita.visita_numero,
                "tareas": data.get("tareas", []),
            })

    historial = piscina.mantenimientos_digitales.all()[:8]
    return render(
        request,
        "asistente_tecnico/digital_plan_mantenimiento.html",
        {
            "perfil": perfil,
            "piscina": piscina,
            "plan": plan,
            "resultado": resultado,
            "plan_visitas": plan_visitas,
            "valores": valores,
            "historial": historial,
            "frecuencias": PlanMantenimientoPiscina.FRECUENCIAS,
            "estados_agua": [
                ("transparente", "Transparente / normal"),
                ("ligeramente_turbia", "Ligeramente turbia"),
                ("muy_turbia", "Muy turbia"),
                ("verde", "Verde / con algas"),
            ],
        },
    )


@login_required
@require_http_methods(["POST"])
def digital_registrar_mantenimiento_view(request, pk):
    perfil = _suscriptor(request.user)
    if not perfil:
        return HttpResponseForbidden("No autorizado")

    piscina = get_object_or_404(
        PiscinaSuscriptor, pk=pk, suscriptor=perfil, activa=True
    )
    plan, _ = PlanMantenimientoPiscina.objects.get_or_create(piscina=piscina)

    try:
        visita_numero = int(request.POST.get("visita_numero") or 1)
    except ValueError:
        visita_numero = 1

    def dec(name):
        valor = (request.POST.get(name) or "").replace(",", ".").strip()
        if not valor:
            return None
        try:
            return Decimal(valor)
        except InvalidOperation:
            return None

    visita_programada = None
    visita_programada_id = request.POST.get("visita_programada_id")
    if visita_programada_id:
        visita_programada = VisitaProgramadaPiscina.objects.filter(
            pk=visita_programada_id,
            piscina=piscina,
            plan=plan,
        ).first()

    tareas = (
        (visita_programada.plan_resultado or {}).get("tareas", [])
        if visita_programada
        else plan.rutina_visita(visita_numero)
    )

    RegistroMantenimientoPiscina.objects.create(
        piscina=piscina,
        visita_numero=visita_numero,
        ph=dec("ph"),
        cloro=dec("cloro"),
        tareas=tareas,
        observaciones=(request.POST.get("observaciones") or "").strip(),
    )

    if visita_programada:
        visita_programada.estado = "completada"
        visita_programada.save(update_fields=["estado", "actualizado_en"])
        visita_programada.notificaciones.update(leida=True)

    messages.success(
        request,
        "Mantenimiento completado y guardado en el historial de la piscina.",
    )
    return redirect(
        "asistente_tecnico:digital_plan_mantenimiento", pk=piscina.pk
    )


@login_required
@require_http_methods(["GET"])
def digital_notificaciones_view(request):
    perfil = _suscriptor(request.user)
    if not perfil:
        return HttpResponseForbidden("No autorizado")

    ahora = timezone.now()
    notificaciones = NotificacionDigital.objects.filter(
        suscriptor=perfil,
        programada_para__lte=ahora,
    ).select_related("piscina", "visita")[:80]

    return render(
        request,
        "asistente_tecnico/digital_notificaciones.html",
        {
            "perfil": perfil,
            "notificaciones": notificaciones,
        },
    )


@login_required
@require_http_methods(["POST"])
def digital_notificacion_leer_view(request, pk):
    perfil = _suscriptor(request.user)
    if not perfil:
        return HttpResponseForbidden("No autorizado")

    notificacion = get_object_or_404(
        NotificacionDigital,
        pk=pk,
        suscriptor=perfil,
    )
    notificacion.leida = True
    notificacion.save(update_fields=["leida"])

    destino = request.POST.get("next") or ""
    if destino.startswith("/"):
        return redirect(destino)
    if notificacion.piscina_id:
        return redirect(
            "asistente_tecnico:digital_plan_mantenimiento",
            pk=notificacion.piscina_id,
        )
    return redirect("asistente_tecnico:digital_notificaciones")


@login_required
@require_http_methods(["POST"])
def digital_notificaciones_leer_todas_view(request):
    perfil = _suscriptor(request.user)
    if not perfil:
        return HttpResponseForbidden("No autorizado")

    NotificacionDigital.objects.filter(
        suscriptor=perfil,
        programada_para__lte=timezone.now(),
        leida=False,
    ).update(leida=True)
    return redirect("asistente_tecnico:digital_notificaciones")


@login_required
@require_http_methods(["GET", "POST"])
def digital_resolver_view(request):
    perfil=_suscriptor(request.user)
    if not perfil: return HttpResponseForbidden("No autorizado")
    piscinas=perfil.piscinas.filter(activa=True)
    piscina=None; resultado=None; caso=None; categoria_consulta="agua"; detalle_problema=""
    pid=request.POST.get("piscina_id") or request.GET.get("piscina")
    if pid:
        piscina=piscinas.filter(pk=pid).first()
    elif piscinas.count() == 1:
        piscina=piscinas.first()
    if request.method=="POST":
        categoria_consulta=(request.POST.get("categoria_consulta") or "agua").strip()
        detalle_problema=(request.POST.get("detalle_problema") or "").strip()
        if not piscina:
            messages.error(request,"Primero registra tu piscina para personalizar correctamente el diagnóstico.")
        elif categoria_consulta != "agua":
            resultado=diagnosticar_problema_tecnico(categoria_consulta, detalle_problema)
        else:
            try:
                ph=Decimal((request.POST.get("ph") or "").replace(",",".")); cloro=Decimal((request.POST.get("cloro") or "").replace(",","."))
            except InvalidOperation:
                messages.error(request,"Necesito los valores de pH y cloro para darte una recomendación química segura.")
            else:
                estado=request.POST.get("estado_agua") or ""
                if estado not in {x[0] for x in CasoAsistenteTecnico.ESTADO_AGUA_CHOICES}:
                    messages.error(request,"Selecciona cómo se ve el agua.")
                else:
                    motor=_motor_activo(); resultado=calcular_recomendacion(piscina.volumen_m3,ph,cloro,estado,piscina.tipo_piscina,motor.reglas,tipo_agua=piscina.origen_agua,antecedente_hierro=piscina.antecedente_hierro)
                    caso=CasoAsistenteTecnico.objects.create(user=request.user,piscina=piscina,motor=motor,volumen_m3=piscina.volumen_m3,ph_inicial=ph,cloro_inicial=cloro,estado_agua=estado,tipo_piscina=piscina.tipo_piscina,diagnostico=resultado["diagnostico"],tipo_tratamiento=resultado["tipo_tratamiento"],prioridad=resultado["prioridad"],resumen=resultado["resumen"],protocolo=resultado["protocolo"],productos_sugeridos=resultado["productos_sugeridos"],explicaciones=resultado["explicaciones"],advertencias=resultado["advertencias"],seguimiento_programado_para=timezone.now()+timedelta(hours=resultado["seguimiento_horas"]))
    return render(request,"asistente_tecnico/digital_resolver.html",{
        "piscinas":piscinas,"piscina":piscina,"resultado":resultado,"caso":caso,
        "estado_choices":CasoAsistenteTecnico.ESTADO_AGUA_CHOICES,
        "problemas_tecnicos":PROBLEMAS_TECNICOS,
        "categoria_consulta":categoria_consulta,"detalle_problema":detalle_problema,
        "articulos_relacionados":_academia_relacionada_con_diagnostico(resultado),
    })
