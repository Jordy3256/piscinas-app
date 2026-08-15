from django.conf import settings
from django.db import models
from django.utils import timezone

from trabajadores.models import Trabajador


class MotorRecomendacion(models.Model):
    version = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=120, default="Motor JVAQUA")
    descripcion = models.TextField(blank=True, default="")
    reglas = models.JSONField(default=dict, blank=True)
    activo = models.BooleanField(default=False, db_index=True)
    publicado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="motores_tecnicos_publicados",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado_en", "-id"]

    def __str__(self):
        return f"{self.nombre} {self.version}"


class CasoAsistenteTecnico(models.Model):
    ESTADO_AGUA_CHOICES = [
        ("transparente", "Transparente"),
        ("ligeramente_turbia", "Ligeramente turbia"),
        ("muy_turbia", "Muy turbia"),
        ("verde", "Verde"),
    ]
    TIPO_PISCINA_CHOICES = [
        ("residencial", "Residencial"),
        ("condominio", "Condominio / urbanización"),
        ("hotel", "Hotel / hostería"),
        ("publica", "Piscina pública / alto uso"),
    ]
    RESULTADO_CHOICES = [
        ("pendiente", "Pendiente de seguimiento"),
        ("exitoso", "Funcionó completamente"),
        ("parcial", "Funcionó parcialmente"),
        ("fallido", "No funcionó"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="casos_asistente_tecnico",
    )
    trabajador = models.ForeignKey(
        Trabajador,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="casos_asistente_tecnico",
    )
    motor = models.ForeignKey(
        MotorRecomendacion,
        on_delete=models.PROTECT,
        related_name="casos",
    )

    volumen_m3 = models.DecimalField(max_digits=9, decimal_places=2)
    ph_inicial = models.DecimalField(max_digits=4, decimal_places=2)
    cloro_inicial = models.DecimalField(max_digits=5, decimal_places=2)
    estado_agua = models.CharField(max_length=30, choices=ESTADO_AGUA_CHOICES)
    tipo_piscina = models.CharField(max_length=30, choices=TIPO_PISCINA_CHOICES)

    diagnostico = models.CharField(max_length=120)
    tipo_tratamiento = models.CharField(max_length=40, db_index=True)
    prioridad = models.CharField(max_length=20, default="media")
    resumen = models.TextField(blank=True, default="")
    protocolo = models.JSONField(default=list, blank=True)
    productos_sugeridos = models.JSONField(default=list, blank=True)
    explicaciones = models.JSONField(default=dict, blank=True)
    advertencias = models.JSONField(default=list, blank=True)

    foto_inicial = models.ImageField(upload_to="asistente_tecnico/inicial/", null=True, blank=True)
    foto_final = models.ImageField(upload_to="asistente_tecnico/final/", null=True, blank=True)

    resultado = models.CharField(max_length=20, choices=RESULTADO_CHOICES, default="pendiente", db_index=True)
    fallas = models.JSONField(default=list, blank=True)
    observaciones_resultado = models.TextField(blank=True, default="")
    accion_final = models.TextField(blank=True, default="")
    ph_final = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    cloro_final = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    estado_agua_final = models.CharField(max_length=30, choices=ESTADO_AGUA_CHOICES, blank=True, default="")

    seguimiento_programado_para = models.DateTimeField(null=True, blank=True, db_index=True)
    seguimiento_respondido_en = models.DateTimeField(null=True, blank=True)
    ultimo_recordatorio_en = models.DateTimeField(null=True, blank=True)
    recordatorios_enviados = models.PositiveSmallIntegerField(default=0)

    destacado = models.BooleanField(default=False, db_index=True)
    nota_destacado = models.TextField(blank=True, default="")

    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creado_en", "-id"]
        indexes = [
            models.Index(fields=["user", "creado_en"], name="ati_user_created_idx"),
            models.Index(fields=["resultado", "seguimiento_programado_para"], name="ati_result_follow_idx"),
            models.Index(fields=["tipo_tratamiento", "resultado"], name="ati_type_result_idx"),
        ]

    @property
    def seguimiento_pendiente(self):
        return self.resultado == "pendiente"

    @property
    def seguimiento_vencido(self):
        return bool(
            self.seguimiento_pendiente
            and self.seguimiento_programado_para
            and self.seguimiento_programado_para <= timezone.now()
        )

    def __str__(self):
        return f"Caso #{self.pk} · {self.get_estado_agua_display()} · {self.volumen_m3} m³"


class CategoriaAcademia(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    descripcion = models.CharField(max_length=240, blank=True, default="")
    icono = models.CharField(max_length=20, blank=True, default="📘")
    orden = models.PositiveSmallIntegerField(default=0)
    activa = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "Categoría de academia"
        verbose_name_plural = "Categorías de academia"

    def __str__(self):
        return self.nombre


class LeccionAcademia(models.Model):
    categoria = models.ForeignKey(CategoriaAcademia, on_delete=models.PROTECT, related_name="lecciones")
    titulo = models.CharField(max_length=160)
    resumen = models.CharField(max_length=280, blank=True, default="")
    contenido = models.TextField()
    errores_evitar = models.TextField(blank=True, default="")
    consejo_jvaqua = models.TextField(blank=True, default="")
    duracion_minutos = models.PositiveSmallIntegerField(default=5)
    orden = models.PositiveSmallIntegerField(default=0)
    publicada = models.BooleanField(default=True, db_index=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="lecciones_academia_creadas")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["categoria__orden", "categoria__nombre", "orden", "titulo"]
        constraints = [models.UniqueConstraint(fields=["categoria", "titulo"], name="ati_unique_lesson_category_title")]
        verbose_name = "Lección de academia"
        verbose_name_plural = "Lecciones de academia"

    def __str__(self):
        return f"{self.categoria}: {self.titulo}"


class ProgresoLeccion(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="progreso_academia")
    leccion = models.ForeignKey(LeccionAcademia, on_delete=models.CASCADE, related_name="progresos")
    completada = models.BooleanField(default=True)
    completada_en = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "leccion"], name="ati_unique_user_lesson_progress")]
        ordering = ["-completada_en"]

    def __str__(self):
        return f"{self.user} · {self.leccion}"


class ArticuloBiblioteca(models.Model):
    CATEGORIAS = [
        ("quimica", "Química"),
        ("equipos", "Equipos"),
        ("filtracion", "Filtración"),
        ("mantenimiento", "Mantenimiento"),
        ("diagnostico", "Diagnóstico"),
        ("seguridad", "Seguridad"),
        ("procedimientos", "Procedimientos JVAQUA"),
    ]
    titulo = models.CharField(max_length=160, unique=True)
    categoria = models.CharField(max_length=30, choices=CATEGORIAS, default="equipos", db_index=True)
    resumen = models.CharField(max_length=280, blank=True, default="")
    funcionamiento = models.TextField(blank=True, default="")
    componentes = models.TextField(blank=True, default="")
    mantenimiento = models.TextField(blank=True, default="")
    fallas_comunes = models.TextField(blank=True, default="")
    recomendaciones = models.TextField(blank=True, default="")
    palabras_clave = models.CharField(max_length=300, blank=True, default="")
    publicada = models.BooleanField(default=True, db_index=True)
    orden = models.PositiveSmallIntegerField(default=0)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="articulos_biblioteca_creados")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["categoria", "orden", "titulo"]
        verbose_name = "Artículo de biblioteca"
        verbose_name_plural = "Artículos de biblioteca"

    def __str__(self):
        return self.titulo


class ConsejoJVAQUA(models.Model):
    CATEGORIAS = ArticuloBiblioteca.CATEGORIAS
    titulo = models.CharField(max_length=140, blank=True, default="Consejo JVAQUA")
    texto = models.TextField()
    categoria = models.CharField(max_length=30, choices=CATEGORIAS, default="mantenimiento", db_index=True)
    activo = models.BooleanField(default=True, db_index=True)
    orden = models.PositiveSmallIntegerField(default=0)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["orden", "id"]
        verbose_name = "Consejo JVAQUA"
        verbose_name_plural = "Consejos JVAQUA"

    def __str__(self):
        return self.titulo


class PropuestaConocimiento(models.Model):
    ESTADOS = [
        ("evaluacion", "En evaluación"),
        ("aprobada", "Aprobada"),
        ("descartada", "Descartada"),
    ]
    titulo = models.CharField(max_length=180)
    descripcion = models.TextField()
    fuente_clave = models.CharField(max_length=160, unique=True)
    evidencia = models.JSONField(default=dict, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="evaluacion", db_index=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    revisado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="propuestas_conocimiento_revisadas")
    revisado_en = models.DateTimeField(null=True, blank=True)
    nota_revision = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["estado", "-actualizado_en"]
        verbose_name = "Propuesta de conocimiento"
        verbose_name_plural = "Propuestas de conocimiento"

    def __str__(self):
        return self.titulo


# ============================================================
# Academia JVAQUA CMS (Sprint 3.1)
# ============================================================
class ContenidoAcademia(models.Model):
    TIPOS = [
        ("biblioteca", "Biblioteca Técnica"),
        ("procedimiento", "Procedimiento"),
        ("equipo", "Equipo"),
    ]
    ESTADOS = [
        ("borrador", "Borrador"),
        ("aprobado", "Aprobado"),
        ("archivado", "Archivado"),
    ]
    NIVELES = [
        ("basico", "Básico"),
        ("intermedio", "Intermedio"),
        ("avanzado", "Avanzado"),
    ]
    ACCESOS = [
        ("compartido", "Trabajadores y suscriptores"),
        ("interno", "Solo JVAQUA"),
        ("suscriptor", "Solo suscriptores"),
    ]
    MODULOS_CURSO = [
        ("fundamentos", "1. Fundamentos"), ("quimica", "2. Química del agua"),
        ("productos", "3. Productos químicos"), ("mantenimiento", "4. Mantenimiento"),
        ("problemas", "5. Problemas del agua"), ("equipos", "6. Equipos"),
        ("preventivo", "7. Mantenimiento preventivo"), ("seguridad", "8. Seguridad"),
        ("estandar", "9. Estándar JVAQUA"), ("avanzado", "10. Conocimiento avanzado"),
    ]
    tipo = models.CharField(max_length=20, choices=TIPOS, db_index=True)
    codigo = models.CharField(max_length=40, unique=True)
    titulo = models.CharField(max_length=180)
    slug = models.SlugField(max_length=210, unique=True)
    resumen = models.CharField(max_length=320, blank=True, default="")
    imagen_principal = models.ImageField(upload_to="academia/principales/", blank=True, null=True)
    nivel = models.CharField(max_length=20, choices=NIVELES, default="basico", db_index=True)
    tiempo_lectura_min = models.PositiveSmallIntegerField(default=5)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="borrador", db_index=True)
    version = models.CharField(max_length=20, default="1.0")
    introduccion = models.TextField(blank=True, default="")
    contenido = models.TextField(blank=True, default="")
    procedimiento = models.TextField(blank=True, default="")
    herramientas_materiales = models.TextField(blank=True, default="")
    funcionamiento = models.TextField(blank=True, default="")
    componentes = models.TextField(blank=True, default="")
    mantenimiento = models.TextField(blank=True, default="")
    fallas_frecuentes = models.TextField(blank=True, default="")
    buenas_practicas = models.TextField(blank=True, default="")
    errores_comunes = models.TextField(blank=True, default="")
    recomendaciones_jvaqua = models.TextField(blank=True, default="")
    referencias_tecnicas = models.TextField(blank=True, default="")
    etiquetas = models.CharField(max_length=500, blank=True, default="")
    acceso = models.CharField(max_length=20, choices=ACCESOS, default="compartido", db_index=True)
    modulo_curso = models.CharField(max_length=30, choices=MODULOS_CURSO, blank=True, default="", db_index=True)
    orden_curso = models.PositiveSmallIntegerField(default=0)
    relacionados = models.ManyToManyField("self", blank=True, symmetrical=True)
    orden = models.PositiveSmallIntegerField(default=0)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="contenidos_academia_creados")
    aprobado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="contenidos_academia_aprobados")
    aprobado_en = models.DateTimeField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["tipo", "orden", "titulo"]
        verbose_name = "Contenido de Academia"
        verbose_name_plural = "Contenidos de Academia"
        indexes = [models.Index(fields=["tipo", "estado"], name="ati_cms_tipo_estado_idx"), models.Index(fields=["estado", "actualizado_en"], name="ati_cms_estado_act_idx")]

    def __str__(self):
        return f"{self.get_tipo_display()} · {self.titulo}"

    @property
    def es_oficial(self):
        return self.estado == "aprobado"

    @property
    def visual_asset(self):
        """Ilustración editorial de respaldo cuando el CMS no tiene una foto cargada."""
        slug = (self.slug or "").lower()
        modulo = (self.modulo_curso or "").lower()
        tipo = (self.tipo or "").lower()

        reglas = [
            (("ph" in slug) or ("alcalinidad" in slug) or ("dureza" in slug) or ("cianur" in slug), "asistente_tecnico/academia/water-balance.svg"),
            (("cloro" in slug) or ("tricloro" in slug) or ("alguicida" in slug) or ("sulfato" in slug) or ("quim" in modulo), "asistente_tecnico/academia/chemistry.svg"),
            (("bomba" in slug) or ("cebado" in slug), "asistente_tecnico/academia/pump.svg"),
            (("filtro" in slug) or ("arena" in slug) or ("retrolavado" in slug), "asistente_tecnico/academia/filter.svg"),
            (("multivalvula" in slug) or ("valvula" in slug), "asistente_tecnico/academia/multiport.svg"),
            (("verde" in slug) or ("turbia" in slug) or ("flocul" in slug), "asistente_tecnico/academia/water-recovery.svg"),
            (("seguridad" in slug) or (modulo == "seguridad"), "asistente_tecnico/academia/safety.svg"),
            (("calor" in slug) or ("calef" in slug), "asistente_tecnico/academia/heat-pump.svg"),
            ((tipo == "equipo") or (modulo == "equipos"), "asistente_tecnico/academia/equipment.svg"),
            ((tipo == "procedimiento") or (modulo in {"mantenimiento", "preventivo", "estandar"}), "asistente_tecnico/academia/maintenance.svg"),
        ]
        for coincide, asset in reglas:
            if coincide:
                return asset
        return "asistente_tecnico/academia/pool-flow.svg"


class ImagenContenidoAcademia(models.Model):
    contenido = models.ForeignKey(ContenidoAcademia, on_delete=models.CASCADE, related_name="galeria")
    imagen = models.ImageField(upload_to="academia/galeria/")
    titulo = models.CharField(max_length=140, blank=True, default="")
    descripcion = models.CharField(max_length=280, blank=True, default="")
    orden = models.PositiveSmallIntegerField(default=0)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["orden", "id"]
        verbose_name = "Imagen de Academia"
        verbose_name_plural = "Imágenes de Academia"

    def __str__(self):
        return self.titulo or f"Imagen #{self.pk}"


class VersionContenidoAcademia(models.Model):
    contenido = models.ForeignKey(ContenidoAcademia, on_delete=models.CASCADE, related_name="versiones")
    version = models.CharField(max_length=20)
    snapshot = models.JSONField(default=dict)
    motivo = models.CharField(max_length=280, blank=True, default="")
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="versiones_academia_creadas")
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado_en", "-id"]
        verbose_name = "Versión de contenido"
        verbose_name_plural = "Versiones de contenido"

    def __str__(self):
        return f"{self.contenido.titulo} · v{self.version}"


class ExperienciaConocimiento(models.Model):
    ESTADOS = [
        ("borrador", "Borrador"),
        ("revision", "En revisión"),
        ("aprobada", "Aprobada"),
        ("descartada", "Descartada"),
    ]
    DESTINOS = [("", "Sin convertir"), ("biblioteca", "Biblioteca Técnica"), ("procedimiento", "Procedimiento"), ("equipo", "Equipo")]
    titulo = models.CharField(max_length=180)
    problema = models.TextField()
    analisis = models.TextField(blank=True, default="")
    solucion = models.TextField(blank=True, default="")
    resultado = models.TextField(blank=True, default="")
    aprendizaje = models.TextField(blank=True, default="")
    estado = models.CharField(max_length=20, choices=ESTADOS, default="borrador", db_index=True)
    destino_sugerido = models.CharField(max_length=20, choices=DESTINOS, blank=True, default="")
    convertido_en = models.ForeignKey(ContenidoAcademia, on_delete=models.SET_NULL, null=True, blank=True, related_name="experiencias_origen")
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="experiencias_conocimiento_creadas")
    revisado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="experiencias_conocimiento_revisadas")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["estado", "-actualizado_en"]
        verbose_name = "Experiencia de conocimiento"
        verbose_name_plural = "Experiencias de conocimiento"

    def __str__(self):
        return self.titulo


class ProgresoContenidoAcademia(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="progreso_contenido_academia")
    contenido = models.ForeignKey(ContenidoAcademia, on_delete=models.CASCADE, related_name="progresos_curso")
    completado = models.BooleanField(default=True)
    completado_en = models.DateTimeField(default=timezone.now)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "contenido"], name="ati_unique_user_content_progress")]
        ordering = ["-completado_en"]


class FavoritoContenidoAcademia(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favoritos_academia")
    contenido = models.ForeignKey(ContenidoAcademia, on_delete=models.CASCADE, related_name="favoritos")
    creado_en = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "contenido"], name="ati_unique_user_content_favorite")]
        ordering = ["-creado_en"]


class ConsultaContenidoAcademia(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="consultas_academia")
    contenido = models.ForeignKey(ContenidoAcademia, on_delete=models.CASCADE, related_name="consultas")
    consultado_en = models.DateTimeField(default=timezone.now, db_index=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "contenido"], name="ati_unique_user_content_recent")]
        ordering = ["-consultado_en"]


class PerfilSuscriptor(models.Model):
    ESTADOS = [("prueba", "Prueba"), ("activo", "Activo"), ("pausado", "Pausado"), ("vencido", "Vencido")]
    PLANES = [("digital", "JVAQUA Digital")]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil_suscriptor")
    estado = models.CharField(max_length=20, choices=ESTADOS, default="prueba", db_index=True)
    plan = models.CharField(max_length=30, choices=PLANES, default="digital")
    inicio = models.DateField(default=timezone.localdate)
    prueba_hasta = models.DateField(null=True, blank=True)
    acceso_hasta = models.DateField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Suscriptor JVAQUA Digital"
        verbose_name_plural = "Suscriptores JVAQUA Digital"

    @property
    def tiene_acceso(self):
        hoy = timezone.localdate()
        if self.estado == "activo":
            return not self.acceso_hasta or self.acceso_hasta >= hoy
        if self.estado == "prueba":
            return not self.prueba_hasta or self.prueba_hasta >= hoy
        return False

    def __str__(self):
        return f"{self.user} · {self.get_estado_display()}"


class PiscinaSuscriptor(models.Model):
    TIPOS = CasoAsistenteTecnico.TIPO_PISCINA_CHOICES
    DESINFECCION = [("cloro", "Cloro"), ("sal", "Cloración salina"), ("otro", "Otro / no lo sé")]
    FILTROS = [("arena", "Filtro de arena"), ("cartucho", "Filtro de cartucho"), ("otro", "Otro / no lo sé")]
    suscriptor = models.ForeignKey(PerfilSuscriptor, on_delete=models.CASCADE, related_name="piscinas")
    nombre = models.CharField(max_length=100, default="Mi piscina")
    tipo_piscina = models.CharField(max_length=30, choices=TIPOS, default="residencial")
    largo_m = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    ancho_m = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    profundidad_m = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    volumen_m3 = models.DecimalField(max_digits=9, decimal_places=2)
    tipo_filtro = models.CharField(max_length=20, choices=FILTROS, default="arena")
    desinfeccion = models.CharField(max_length=20, choices=DESINFECCION, default="cloro")
    notas = models.TextField(blank=True, default="")
    principal = models.BooleanField(default=False, db_index=True)
    activa = models.BooleanField(default=True, db_index=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-principal", "nombre"]
        verbose_name = "Piscina de suscriptor"
        verbose_name_plural = "Piscinas de suscriptores"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.principal:
            type(self).objects.filter(suscriptor=self.suscriptor).exclude(pk=self.pk).update(principal=False)

    def __str__(self):
        return f"{self.suscriptor.user} · {self.nombre}"
