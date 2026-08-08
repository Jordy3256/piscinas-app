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
