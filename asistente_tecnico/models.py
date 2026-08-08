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
